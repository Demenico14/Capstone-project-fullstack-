import { type NextRequest, NextResponse } from "next/server"
import { spawn } from "child_process"
import path from "path"

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { windowDays = 7, epochs = 50 } = body

    // Get MongoDB URI from environment
    const mongodbUri = process.env.MONGODB_URI
    if (!mongodbUri) {
      return NextResponse.json({ error: "MongoDB URI not configured" }, { status: 500 })
    }

    // Path to training script
    const scriptPath = path.join(process.cwd(), "backend", "ml_pipeline", "train_from_mongodb.py")

    // Start training process in background
    const pythonProcess = spawn(
      "python3",
      [
        scriptPath,
        "--mongodb-uri",
        mongodbUri,
        "--database",
        process.env.MONGODB_DB_NAME || "cropiot",
        "--window-days",
        windowDays.toString(),
        "--epochs",
        epochs.toString(),
      ],
      {
        detached: true,
        stdio: "ignore",
      },
    )

    // Detach the process so it continues running
    pythonProcess.unref()

    return NextResponse.json({
      success: true,
      message: "Training started in background",
      pid: pythonProcess.pid,
    })
  } catch (error) {
    console.error("Error starting training:", error)
    return NextResponse.json({ error: "Failed to start training" }, { status: 500 })
  }
}
