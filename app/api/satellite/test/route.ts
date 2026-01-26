import { NextResponse } from "next/server"

export async function GET() {
  const credentials = {
    SENTINELHUB_CLIENT_ID: process.env.SENTINELHUB_CLIENT_ID,
    NEXT_PUBLIC_SENTINELHUB_CLIENT_ID: process.env.NEXT_PUBLIC_SENTINELHUB_CLIENT_ID,
    SENTINELHUB_CLIENT_SECRET: process.env.SENTINELHUB_CLIENT_SECRET ? "***SET***" : undefined,
  }

  const clientId = process.env.SENTINELHUB_CLIENT_ID || process.env.NEXT_PUBLIC_SENTINELHUB_CLIENT_ID
  const clientSecret = process.env.SENTINELHUB_CLIENT_SECRET

  return NextResponse.json({
    message: "Sentinel Hub Credentials Test",
    credentials,
    ready: !!(clientId && clientSecret),
    clientIdPreview: clientId ? clientId.substring(0, 8) + "..." : "NOT SET",
    clientSecretSet: !!clientSecret,
    hint: clientSecret
      ? "Credentials are configured correctly!"
      : "Set SENTINELHUB_CLIENT_SECRET (without NEXT_PUBLIC_) in .env.local and restart your dev server",
  })
}
