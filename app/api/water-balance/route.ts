import { type NextRequest, NextResponse } from "next/server"

/**
 * Water Balance API Route
 *
 * This route proxies requests to the Python backend which handles:
 * - Google Earth Engine data fetching (NDVI, rainfall, ET, LST)
 * - Physics calculations (water balance, VPD, crop growth)
 * - Integration with IoT sensor data
 *
 * The actual physics computations are done in the backend using:
 * - FAO-56 Penman-Monteith equations
 * - VPD stress calculations
 * - Growing degree day models
 */

const BACKEND_URL = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000"

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const lat = searchParams.get("lat")
    const lng = searchParams.get("lng")
    const startDate = searchParams.get("startDate")
    const endDate = searchParams.get("endDate")
    const sensorId = searchParams.get("sensorId")

    if (!lat || !lng) {
      return NextResponse.json(
        {
          success: false,
          error: "lat and lng parameters are required",
        },
        { status: 400 },
      )
    }

    // Build query string for backend
    const params = new URLSearchParams({
      lat,
      lng,
      ...(startDate && { startDate }),
      ...(endDate && { endDate }),
      ...(sensorId && { sensorId }),
    })

    // Proxy to Python backend
    const backendResponse = await fetch(`${BACKEND_URL}/api/water-balance?${params}`, {
      headers: {
        Accept: "application/json",
      },
      signal: AbortSignal.timeout(60000), // 60 second timeout for GEE operations
    })

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text()
      console.error("[Water Balance] Backend error:", errorText)
      return NextResponse.json(
        {
          success: false,
          error: `Backend error: ${backendResponse.status}`,
        },
        { status: backendResponse.status },
      )
    }

    const data = await backendResponse.json()

    return NextResponse.json(data)
  } catch (error) {
    console.error("[Water Balance] Error:", error)

    // Check if it's a timeout error
    if (error instanceof Error && error.name === "AbortError") {
      return NextResponse.json(
        {
          success: false,
          error: "Request timed out. The backend may be processing GEE data.",
        },
        { status: 504 },
      )
    }

    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Failed to fetch water balance data",
      },
      { status: 500 },
    )
  }
}

/**
 * Get VPD Analysis
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { lat, lng, startDate, endDate, dataType } = body

    if (!lat || !lng) {
      return NextResponse.json(
        {
          success: false,
          error: "lat and lng are required",
        },
        { status: 400 },
      )
    }

    // Route to appropriate backend endpoint based on dataType
    let endpoint = "/api/water-balance"
    if (dataType === "vpd") {
      endpoint = "/api/physics/vpd"
    } else if (dataType === "growth") {
      endpoint = "/api/physics/crop-growth"
    } else if (dataType === "stress") {
      endpoint = "/api/physics/yield-stress"
    }

    const params = new URLSearchParams({
      lat: String(lat),
      lng: String(lng),
      ...(startDate && { startDate }),
      ...(endDate && { endDate }),
    })

    const backendResponse = await fetch(`${BACKEND_URL}${endpoint}?${params}`, {
      headers: {
        Accept: "application/json",
      },
      signal: AbortSignal.timeout(30000),
    })

    if (!backendResponse.ok) {
      throw new Error(`Backend returned ${backendResponse.status}`)
    }

    const data = await backendResponse.json()

    return NextResponse.json(data)
  } catch (error) {
    console.error("[Water Balance POST] Error:", error)

    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Failed to process request",
      },
      { status: 500 },
    )
  }
}
