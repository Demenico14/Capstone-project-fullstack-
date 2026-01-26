import { type NextRequest, NextResponse } from "next/server"
import clientPromise from "@/lib/mongodb"

export async function GET() {
  try {
    const client = await clientPromise
    const db = client.db("cropiot")
    const config = await db.collection("config").findOne({ _id: "system" })

    if (!config) {
      // Return default config if none exists
      return NextResponse.json({
        success: true,
        config: {
          sensorApiUrl: process.env.NEXT_PUBLIC_API_URL || "http://192.168.4.2:5000",
          diseaseApiUrl: process.env.NEXT_PUBLIC_DISEASE_API_URL || "http://192.168.4.2:8000",
          yieldApiUrl: process.env.NEXT_PUBLIC_YIELD_API_URL || "http://192.168.4.2:9000",
          nodes: JSON.parse(process.env.NEXT_PUBLIC_NODE_COORDINATES || "{}"),
          farmCenter: {
            lat: Number.parseFloat(process.env.NEXT_PUBLIC_FARM_CENTER_LAT || "-18.30252535"),
            lng: Number.parseFloat(process.env.NEXT_PUBLIC_FARM_CENTER_LNG || "31.56415345"),
          },
        },
      })
    }

    return NextResponse.json({ success: true, config: config.data })
  } catch (error) {
    console.error("Error fetching config:", error)
    return NextResponse.json({ success: false, error: "Failed to fetch configuration" }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const client = await clientPromise
    const db = client.db("cropiot")

    await db
      .collection("config")
      .updateOne({ _id: "system" }, { $set: { data: body, updatedAt: new Date() } }, { upsert: true })

    return NextResponse.json({ success: true, message: "Configuration updated successfully" })
  } catch (error) {
    console.error("Error updating config:", error)
    return NextResponse.json({ success: false, error: "Failed to update configuration" }, { status: 500 })
  }
}
