import { NextResponse } from "next/server"
import fs from "fs"
import path from "path"

export async function GET() {
  try {
    const statusPath = path.join(process.cwd(), "backend", "ml_pipeline", "training_status.json")

    // Check if status file exists
    if (!fs.existsSync(statusPath)) {
      return NextResponse.json({
        status: "idle",
        progress: 0,
        message: "No training in progress",
        timestamp: new Date().toISOString(),
      })
    }

    // Read status file
    const statusData = JSON.parse(fs.readFileSync(statusPath, "utf-8"))

    return NextResponse.json(statusData)
  } catch (error) {
    console.error("Error reading training status:", error)
    return NextResponse.json({ error: "Failed to read training status" }, { status: 500 })
  }
}
