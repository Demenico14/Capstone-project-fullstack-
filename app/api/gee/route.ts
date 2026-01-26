import { type NextRequest, NextResponse } from "next/server"
import ee from "@google/earthengine"

// Initialize Earth Engine (done once)
let eeInitialized = false

async function initializeEarthEngine() {
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

    // Authenticate with service account
    await new Promise<void>((resolve, reject) => {
      ee.data.authenticateViaPrivateKey(
        { client_email: serviceAccountEmail, private_key: privateKey },
        () => {
          ee.initialize(
            null,
            null,
            () => {
              console.log("[GEE] Earth Engine initialized successfully")
              eeInitialized = true
              resolve()
            },
            reject,
          )
        },
        reject,
      )
    })
  } catch (error) {
    console.error("[GEE] Failed to initialize Earth Engine:", error)
    throw error
  }
}

export async function GET(request: NextRequest) {
  try {
    // Initialize Earth Engine
    await initializeEarthEngine()

    const searchParams = request.nextUrl.searchParams
    const layer = searchParams.get("layer") || "ndvi"

    // Get farm coordinates from environment
    const centerLat = Number.parseFloat(process.env.NEXT_PUBLIC_FARM_CENTER_LAT || "-18.30252535")
    const centerLng = Number.parseFloat(process.env.NEXT_PUBLIC_FARM_CENTER_LNG || "31.56415345")

    // Define area of interest (1km x 1km around farm center)
    const geometry = ee.Geometry.Rectangle([
      centerLng - 0.005, // ~500m west
      centerLat - 0.005, // ~500m south
      centerLng + 0.005, // ~500m east
      centerLat + 0.005, // ~500m north
    ])

    // Get the most recent Sentinel-2 image (last 30 days)
    const endDate = new Date()
    const startDate = new Date(endDate.getTime() - 30 * 24 * 60 * 60 * 1000)

    const collection = ee
      .ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
      .filterBounds(geometry)
      .filterDate(startDate.toISOString(), endDate.toISOString())
      .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
      .sort("CLOUD_COVERAGE_ASSESSMENT")

    const image = collection.first()

    let visualizationParams: any
    let imageToVisualize: any

    switch (layer) {
      case "ndvi": {
        // Calculate NDVI: (NIR - Red) / (NIR + Red)
        const nir = image.select("B8")
        const red = image.select("B4")
        const ndvi = nir.subtract(red).divide(nir.add(red)).rename("NDVI")

        imageToVisualize = ndvi
        visualizationParams = {
          min: -0.2,
          max: 0.8,
          palette: ["red", "yellow", "green"],
        }
        break
      }

      case "moisture": {
        // Calculate NDWI (Normalized Difference Water Index)
        const nir = image.select("B8")
        const swir = image.select("B11")
        const ndwi = nir.subtract(swir).divide(nir.add(swir)).rename("NDWI")

        imageToVisualize = ndwi
        visualizationParams = {
          min: -0.3,
          max: 0.3,
          palette: ["brown", "white", "blue"],
        }
        break
      }

      case "evi": {
        // Calculate EVI: 2.5 * ((NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1))
        const nir = image.select("B8")
        const red = image.select("B4")
        const blue = image.select("B2")
        const evi = nir
          .subtract(red)
          .divide(nir.add(red.multiply(6)).subtract(blue.multiply(7.5)).add(10000))
          .multiply(2.5)
          .rename("EVI")

        imageToVisualize = evi
        visualizationParams = {
          min: -0.2,
          max: 0.8,
          palette: ["red", "yellow", "green"],
        }
        break
      }

      case "true-color":
      default: {
        imageToVisualize = image.select(["B4", "B3", "B2"])
        visualizationParams = {
          min: 0,
          max: 3000,
          gamma: 1.4,
        }
        break
      }
    }

    // Get the tile URL
    const mapId = await new Promise<any>((resolve, reject) => {
      imageToVisualize.getMap(visualizationParams, (obj: any, error: any) => {
        if (error) reject(error)
        else resolve(obj)
      })
    })

    // Get image metadata
    const imageInfo = await new Promise<any>((resolve, reject) => {
      image.getInfo((info: any, error: any) => {
        if (error) reject(error)
        else resolve(info)
      })
    })

    return NextResponse.json({
      success: true,
      layer,
      tileUrl: mapId.urlFormat,
      metadata: {
        date: imageInfo.properties["system:time_start"],
        cloudCoverage: imageInfo.properties["CLOUDY_PIXEL_PERCENTAGE"],
        satellite: "Sentinel-2",
        bounds: {
          north: centerLat + 0.005,
          south: centerLat - 0.005,
          east: centerLng + 0.005,
          west: centerLng - 0.005,
        },
      },
    })
  } catch (error: any) {
    console.error("[GEE] Error fetching satellite data:", error)
    return NextResponse.json(
      {
        success: false,
        error: "Failed to fetch satellite imagery",
        details: error.message,
      },
      { status: 500 },
    )
  }
}
