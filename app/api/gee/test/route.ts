import { NextResponse } from "next/server"
import ee from "@google/earthengine"

export async function GET() {
  try {
    // Check if credentials are configured
    const serviceAccountEmail = process.env.GEE_SERVICE_ACCOUNT_EMAIL
    const privateKeyPath = process.env.GEE_PRIVATE_KEY_PATH
    const serviceAccountJson = process.env.GEE_SERVICE_ACCOUNT_JSON

    const checks = {
      serviceAccountEmail: !!serviceAccountEmail,
      hasPrivateKey: !!(privateKeyPath || serviceAccountJson),
      privateKeyPath: privateKeyPath || "Using base64 JSON",
    }

    if (!serviceAccountEmail) {
      return NextResponse.json(
        {
          success: false,
          error: "GEE_SERVICE_ACCOUNT_EMAIL not configured",
          checks,
        },
        { status: 500 },
      )
    }

    if (!privateKeyPath && !serviceAccountJson) {
      return NextResponse.json(
        {
          success: false,
          error: "Neither GEE_PRIVATE_KEY_PATH nor GEE_SERVICE_ACCOUNT_JSON configured",
          checks,
        },
        { status: 500 },
      )
    }

    // Try to authenticate
    let privateKey: string

    if (serviceAccountJson) {
      const decoded = Buffer.from(serviceAccountJson, "base64").toString("utf-8")
      const keyData = JSON.parse(decoded)
      privateKey = keyData.private_key
    } else if (privateKeyPath) {
      const fs = require("fs")
      const keyData = JSON.parse(fs.readFileSync(privateKeyPath, "utf-8"))
      privateKey = keyData.private_key
    } else {
      throw new Error("No private key available")
    }

    // Test authentication
    await new Promise<void>((resolve, reject) => {
      ee.data.authenticateViaPrivateKey(
        { client_email: serviceAccountEmail, private_key: privateKey },
        () => {
          ee.initialize(null, null, resolve, reject)
        },
        reject,
      )
    })

    return NextResponse.json({
      success: true,
      message: "Google Earth Engine authentication successful",
      serviceAccount: serviceAccountEmail,
      checks,
    })
  } catch (error: any) {
    console.error("[GEE Test] Authentication failed:", error)
    return NextResponse.json(
      {
        success: false,
        error: "Failed to authenticate with Google Earth Engine",
        details: error.message,
      },
      { status: 500 },
    )
  }
}
