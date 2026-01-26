import { NextResponse } from "next/server"

// Sentinel Hub API endpoint
const SENTINEL_HUB_PROCESS_URL = "https://services.sentinel-hub.com/api/v1/process"
const SENTINEL_HUB_TOKEN_URL = "https://services.sentinel-hub.com/oauth/token"

// Cache for access token
let cachedToken: { token: string; expiresAt: number } | null = null

async function getAccessToken(): Promise<string> {
  // Return cached token if still valid
  if (cachedToken && cachedToken.expiresAt > Date.now()) {
    return cachedToken.token
  }

  const clientId = process.env.SENTINELHUB_CLIENT_ID || process.env.NEXT_PUBLIC_SENTINELHUB_CLIENT_ID

  // Client secret must NEVER be exposed to the client - only use server-side variable
  const clientSecret = process.env.SENTINELHUB_CLIENT_SECRET

  console.log("[v0] Checking Sentinel Hub credentials:", {
    hasClientId: !!clientId,
    hasClientSecret: !!clientSecret,
    clientIdLength: clientId?.length || 0,
    clientSecretLength: clientSecret?.length || 0,
  })

  if (!clientId || !clientSecret) {
    console.error("[v0] Missing Sentinel Hub credentials")
    throw new Error(
      "Sentinel Hub credentials not configured. Make sure SENTINELHUB_CLIENT_SECRET (without NEXT_PUBLIC_) is set in .env.local",
    )
  }

  console.log("[v0] Requesting Sentinel Hub access token with client ID:", clientId.substring(0, 8) + "...")

  try {
    const response = await fetch(SENTINEL_HUB_TOKEN_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        grant_type: "client_credentials",
        client_id: clientId,
        client_secret: clientSecret,
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error("[v0] Sentinel Hub token error response:", {
        status: response.status,
        statusText: response.statusText,
        error: errorText,
      })
      throw new Error(`Failed to authenticate with Sentinel Hub (${response.status}): ${errorText}`)
    }

    const data = await response.json()
    console.log("[v0] Successfully obtained Sentinel Hub access token")

    // Cache token (expires in 1 hour, cache for 55 minutes)
    cachedToken = {
      token: data.access_token,
      expiresAt: Date.now() + 55 * 60 * 1000,
    }

    return data.access_token
  } catch (error) {
    console.error("[v0] Error getting Sentinel Hub token:", error)
    throw error
  }
}

// NDVI evalscript
const NDVI_SCRIPT = `
//VERSION=3
function setup() {
  return {
    input: ["B04", "B08", "dataMask"],
    output: { bands: 4 }
  };
}

function evaluatePixel(sample) {
  let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
  
  // Color coding for NDVI
  if (ndvi < 0.2) return [0.8, 0.2, 0.2, sample.dataMask]; // Red - stressed
  if (ndvi < 0.4) return [0.9, 0.7, 0.3, sample.dataMask]; // Yellow - sparse
  if (ndvi < 0.6) return [0.6, 0.9, 0.4, sample.dataMask]; // Light green - moderate
  if (ndvi < 0.8) return [0.2, 0.8, 0.3, sample.dataMask]; // Green - healthy
  return [0.1, 0.5, 0.2, sample.dataMask]; // Dark green - very healthy
}
`

// Moisture Index evalscript
const MOISTURE_SCRIPT = `
//VERSION=3
function setup() {
  return {
    input: ["B08", "B11", "dataMask"],
    output: { bands: 4 }
  };
}

function evaluatePixel(sample) {
  let moisture = (sample.B08 - sample.B11) / (sample.B08 + sample.B11);
  
  // Color coding for moisture
  if (moisture > 0.3) return [0.1, 0.3, 0.8, sample.dataMask]; // Blue - high moisture
  if (moisture > 0.1) return [0.3, 0.6, 0.9, sample.dataMask]; // Light blue - moderate
  if (moisture > -0.1) return [0.9, 0.7, 0.3, sample.dataMask]; // Yellow - low
  return [0.9, 0.3, 0.2, sample.dataMask]; // Red - very dry
}
`

// True color evalscript
const TRUE_COLOR_SCRIPT = `
//VERSION=3
function setup() {
  return {
    input: ["B04", "B03", "B02", "dataMask"],
    output: { bands: 4 }
  };
}

function evaluatePixel(sample) {
  return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02, sample.dataMask];
}
`

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const type = searchParams.get("type") || "ndvi"
  const lat = Number.parseFloat(searchParams.get("lat") || process.env.NEXT_PUBLIC_FARM_CENTER_LAT || "-17.8252")
  const lng = Number.parseFloat(searchParams.get("lng") || process.env.NEXT_PUBLIC_FARM_CENTER_LNG || "31.0335")
  const size = Number.parseFloat(searchParams.get("size") || "0.01") // Size in degrees (~1km)

  console.log("[v0] Satellite imagery request:", { type, lat, lng, size })

  try {
    const accessToken = await getAccessToken()

    // Calculate bounding box
    const bbox = [
      lng - size / 2, // min longitude
      lat - size / 2, // min latitude
      lng + size / 2, // max longitude
      lat + size / 2, // max latitude
    ]

    // Select evalscript based on type
    let evalscript = NDVI_SCRIPT
    if (type === "moisture") evalscript = MOISTURE_SCRIPT
    if (type === "true-color") evalscript = TRUE_COLOR_SCRIPT

    // Get current date and 10 days ago
    const toDate = new Date()
    const fromDate = new Date()
    fromDate.setDate(fromDate.getDate() - 10)

    const requestBody = {
      input: {
        bounds: {
          bbox,
          properties: {
            crs: "http://www.opengis.net/def/crs/EPSG/0/4326",
          },
        },
        data: [
          {
            type: "sentinel-2-l2a",
            dataFilter: {
              timeRange: {
                from: fromDate.toISOString(),
                to: toDate.toISOString(),
              },
              maxCloudCoverage: 30,
            },
          },
        ],
      },
      output: {
        width: 512,
        height: 512,
        responses: [
          {
            identifier: "default",
            format: {
              type: "image/png",
            },
          },
        ],
      },
      evalscript,
    }

    const imageResponse = await fetch(SENTINEL_HUB_PROCESS_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    })

    if (!imageResponse.ok) {
      const errorText = await imageResponse.text()
      console.error("[v0] Sentinel Hub API error:", errorText)
      throw new Error(`Sentinel Hub API error: ${imageResponse.status}`)
    }

    console.log("[v0] Successfully fetched satellite imagery")
    const imageBlob = await imageResponse.blob()

    return new NextResponse(imageBlob, {
      headers: {
        "Content-Type": "image/png",
        "Cache-Control": "public, max-age=43200", // Cache for 12 hours
      },
    })
  } catch (error) {
    console.error("[v0] Satellite data fetch error:", error)
    return NextResponse.json(
      {
        error: "Failed to fetch satellite data",
        message: error instanceof Error ? error.message : "Unknown error",
        hint: "Make sure SENTINELHUB_CLIENT_ID and SENTINELHUB_CLIENT_SECRET are set in .env.local",
      },
      { status: 500 },
    )
  }
}
