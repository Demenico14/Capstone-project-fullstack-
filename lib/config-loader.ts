let cachedConfig: any = null

export async function loadConfig() {
  if (cachedConfig) {
    return cachedConfig
  }

  try {
    const response = await fetch("/api/config", { cache: "no-store" })
    if (response.ok) {
      const data = await response.json()
      cachedConfig = data.config
      return cachedConfig
    }
  } catch (error) {
    console.error("Failed to load config from MongoDB:", error)
  }

  // Fallback to environment variables
  return {
    sensorApiUrl: process.env.NEXT_PUBLIC_API_URL || "http://192.168.4.2:5000",
    diseaseApiUrl: process.env.NEXT_PUBLIC_DISEASE_API_URL || "http://192.168.4.2:8000",
    yieldApiUrl: process.env.NEXT_PUBLIC_YIELD_API_URL || "http://192.168.4.2:9000",
    nodes: JSON.parse(process.env.NEXT_PUBLIC_NODE_COORDINATES || "{}"),
    farmCenter: {
      lat: Number.parseFloat(process.env.NEXT_PUBLIC_FARM_CENTER_LAT || "-18.30252535"),
      lng: Number.parseFloat(process.env.NEXT_PUBLIC_FARM_CENTER_LNG || "31.56415345"),
    },
  }
}

export function clearConfigCache() {
  cachedConfig = null
}
