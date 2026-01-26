import { type NextRequest, NextResponse } from "next/server"
import { getDb } from "@/lib/mongodb"

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const sensorId = searchParams.get("sensor_id")
    const limit = Number.parseInt(searchParams.get("limit") || "50")

    const db = await getDb()
    const collection = db.collection("yield_records")

    const query = sensorId ? { sensor_id: sensorId } : {}
    const records = await collection.find(query).sort({ harvest_date: -1 }).limit(limit).toArray()

    return NextResponse.json({
      success: true,
      records: records.map((r) => ({
        ...r,
        _id: r._id.toString(),
      })),
    })
  } catch (error) {
    console.error("[v0] Error fetching yield records:", error)
    return NextResponse.json({ success: false, error: "Failed to fetch yield records" }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { sensor_id, harvest_date, yield_value, crop_type, unit, notes } = body

    if (!sensor_id || !harvest_date || !yield_value) {
      return NextResponse.json({ success: false, error: "Missing required fields" }, { status: 400 })
    }

    const db = await getDb()
    const collection = db.collection("yield_records")

    const record = {
      sensor_id,
      harvest_date: new Date(harvest_date),
      yield_value: Number.parseFloat(yield_value),
      crop_type: crop_type || "tobacco",
      unit: unit || "kg/hectare",
      notes: notes || "",
      created_at: new Date(),
    }

    const result = await collection.insertOne(record)

    return NextResponse.json({
      success: true,
      record: {
        ...record,
        _id: result.insertedId.toString(),
      },
    })
  } catch (error) {
    console.error("[v0] Error saving yield record:", error)
    return NextResponse.json({ success: false, error: "Failed to save yield record" }, { status: 500 })
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const id = searchParams.get("id")

    if (!id) {
      return NextResponse.json({ success: false, error: "Missing record ID" }, { status: 400 })
    }

    const db = await getDb()
    const collection = db.collection("yield_records")

    const { ObjectId } = require("mongodb")
    await collection.deleteOne({ _id: new ObjectId(id) })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error("[v0] Error deleting yield record:", error)
    return NextResponse.json({ success: false, error: "Failed to delete yield record" }, { status: 500 })
  }
}
