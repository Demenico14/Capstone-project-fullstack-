import { type NextRequest, NextResponse } from "next/server"
import ee from "@google/earthengine"

// Initialize Earth Engine
let eeInitialized = false

async function initializeEE() {
  if (eeInitialized) return

  try {
    // Get credentials from environment
    const serviceAccountEmail = process.env.GEE_SERVICE_ACCOUNT_EMAIL
    const privateKeyPath = process.env.GEE_PRIVATE_KEY_PATH
    const serviceAccountJson = process.env.GEE_SERVICE_ACCOUNT_JSON

    if (!serviceAccountEmail) {
      throw new Error("GEE_SERVICE_ACCOUNT_EMAIL not configured")
    }

    let privateKey: string

    // Check if we have the JSON as a base64 string (for deployment)
    if (serviceAccountJson) {
      const decoded = Buffer.from(serviceAccountJson, "base64").toString("utf-8")
      const keyData = JSON.parse(decoded)
      privateKey = keyData.private_key
    }
    // Otherwise, read from file (for local development)
    else if (privateKeyPath) {
      const fs = require("fs")
      const keyData = JSON.parse(fs.readFileSync(privateKeyPath, "utf-8"))
      privateKey = keyData.private_key
    } else {
      throw new Error("Neither GEE_SERVICE_ACCOUNT_JSON nor GEE_PRIVATE_KEY_PATH configured")
    }

    return new Promise((resolve, reject) => {
      ee.data.authenticateViaPrivateKey(
        { client_email: serviceAccountEmail, private_key: privateKey },
        () => {
          ee.initialize(
            null,
            null,
            () => {
              eeInitialized = true
              console.log("[Water Balance] Earth Engine initialized successfully")
              resolve(true)
            },
            reject,
          )
        },
        reject,
      )
    })
  } catch (error) {
    console.error("[Water Balance] Failed to initialize Earth Engine:", error)
    throw error
  }
}

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const lat = Number.parseFloat(searchParams.get("lat") || "0")
    const lng = Number.parseFloat(searchParams.get("lng") || "0")
    const startDate =
      searchParams.get("startDate") || new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0]
    const endDate = searchParams.get("endDate") || new Date().toISOString().split("T")[0]

    console.log("[Water Balance] Fetching data for:", { lat, lng, startDate, endDate })

    // Initialize Earth Engine
    await initializeEE()

    // Define area of interest (500m radius around point)
    const point = ee.Geometry.Point([lng, lat])
    const aoi = point.buffer(500)

    // 1. Fetch NDVI from Sentinel-2
    const s2 = ee
      .ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
      .filterBounds(aoi)
      .filterDate(startDate, endDate)
      .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))

    const ndviCollection = s2.map((image: any) => {
      const ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
      return ndvi.set("system:time_start", image.get("system:time_start"))
    })

    // 2. Fetch Rainfall from CHIRPS
    const chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterBounds(aoi).filterDate(startDate, endDate)

    // 3. Fetch ET from MOD16A2GF
    const mod16 = ee.ImageCollection("MODIS/061/MOD16A2GF").filterBounds(aoi).filterDate(startDate, endDate)

    // Get time series data
    const ndviTimeSeries = await getTimeSeries(ndviCollection, aoi, "NDVI")
    const rainfallTimeSeries = await getTimeSeries(chirps, aoi, "precipitation")
    const etTimeSeries = await getTimeSeries(mod16, aoi, "ET")

    // Calculate Kc (crop coefficient) from NDVI
    const ndviMin = 0.2
    const ndviMax = 0.8
    const kcValues = ndviTimeSeries.map((item: any) => {
      const ndvi = item.value
      const kc = Math.max(0, Math.min(1.2, (ndvi - ndviMin) / (ndviMax - ndviMin)))
      return { date: item.date, value: kc }
    })

    // Fetch IoT sensor data (soil moisture and irrigation)
    const sensorData = await fetchSensorData(startDate, endDate)

    // Calculate ΔS (change in soil moisture)
    const deltaSValues = calculateDeltaS(sensorData.soilMoisture)

    // Calculate water balance: ET = P + I - R - ΔS
    const waterBalance = calculateWaterBalance({
      rainfall: rainfallTimeSeries,
      irrigation: sensorData.irrigation,
      deltaS: deltaSValues,
      et: etTimeSeries,
    })

    return NextResponse.json({
      success: true,
      data: {
        ndvi: ndviTimeSeries,
        rainfall: rainfallTimeSeries,
        et: etTimeSeries,
        kc: kcValues,
        deltaS: deltaSValues,
        irrigation: sensorData.irrigation,
        waterBalance: waterBalance,
      },
      metadata: {
        location: { lat, lng },
        dateRange: { start: startDate, end: endDate },
        areaSize: "500m radius",
      },
    })
  } catch (error) {
    console.error("[Water Balance] Error:", error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Failed to fetch water balance data",
      },
      { status: 500 },
    )
  }
}

async function getTimeSeries(collection: any, aoi: any, bandName: string): Promise<any[]> {
  return new Promise((resolve, reject) => {
    const reducer = ee.Reducer.mean()

    collection
      .map((image: any) => {
        const value = image.reduceRegion({
          reducer: reducer,
          geometry: aoi,
          scale: 30,
          maxPixels: 1e9,
        })
        return ee.Feature(null, {
          date: ee.Date(image.get("system:time_start")).format("YYYY-MM-dd"),
          value: value.get(bandName),
        })
      })
      .evaluate((result: any, error: any) => {
        if (error) {
          reject(error)
        } else {
          const features = result.features || []
          const timeSeries = features.map((f: any) => ({
            date: f.properties.date,
            value: f.properties.value || 0,
          }))
          resolve(timeSeries)
        }
      })
  })
}

async function fetchSensorData(startDate: string, endDate: string) {
  // Fetch from your backend API
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://192.168.4.2:5000"

  try {
    const response = await fetch(`${baseUrl}/api/readings?start=${startDate}&end=${endDate}`, {
      signal: AbortSignal.timeout(5000),
    })

    if (!response.ok) {
      throw new Error("Failed to fetch sensor data")
    }

    const data = await response.json()

    // Process sensor data
    const soilMoisture = data.map((reading: any) => ({
      date: reading.timestamp.split("T")[0],
      value: reading.soil_moisture || 0,
    }))

    // Mock irrigation data (replace with actual irrigation sensor data)
    const irrigation = data.map((reading: any) => ({
      date: reading.timestamp.split("T")[0],
      value: 0, // Replace with actual irrigation data
    }))

    return { soilMoisture, irrigation }
  } catch (error) {
    console.error("[Water Balance] Error fetching sensor data:", error)
    // Return mock data if sensor API fails
    return {
      soilMoisture: [],
      irrigation: [],
    }
  }
}

function calculateDeltaS(soilMoistureData: any[]): any[] {
  const deltaS = []
  for (let i = 1; i < soilMoistureData.length; i++) {
    const current = soilMoistureData[i].value
    const previous = soilMoistureData[i - 1].value
    deltaS.push({
      date: soilMoistureData[i].date,
      value: current - previous,
    })
  }
  return deltaS
}

function calculateWaterBalance(data: any): any[] {
  const { rainfall, irrigation, deltaS, et } = data

  // Align all data by date
  const dates = new Set([
    ...rainfall.map((d: any) => d.date),
    ...irrigation.map((d: any) => d.date),
    ...deltaS.map((d: any) => d.date),
    ...et.map((d: any) => d.date),
  ])

  const balance = Array.from(dates).map((date) => {
    const p = rainfall.find((d: any) => d.date === date)?.value || 0
    const i = irrigation.find((d: any) => d.date === date)?.value || 0
    const ds = deltaS.find((d: any) => d.date === date)?.value || 0
    const etValue = et.find((d: any) => d.date === date)?.value || 0

    // Water balance: ET = P + I - R - ΔS
    // Rearranged: Balance = P + I - ET - ΔS (assuming R ≈ 0 for simplicity)
    const waterBalance = p + i - etValue - ds

    return {
      date,
      value: waterBalance,
      components: { p, i, ds, et: etValue },
    }
  })

  return balance.sort((a, b) => a.date.localeCompare(b.date))
}
