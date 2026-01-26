"use client"

import { createContext, useContext, useEffect, useState, type ReactNode } from "react"

interface ConfigContextType {
  config: AppConfig | null
  loading: boolean
  refreshConfig: () => Promise<void>
}

interface AppConfig {
  sensorApiUrl: string
  diseaseApiUrl: string
  yieldApiUrl: string
  nodes: Record<string, string>
  farmCenter: { lat: number; lng: number }
  sentinelClientId?: string
  sentinelInstanceId?: string
  geeServiceAccount?: string
}

const ConfigContext = createContext<ConfigContextType>({
  config: null,
  loading: true,
  refreshConfig: async () => {},
})

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [loading, setLoading] = useState(true)

  const loadConfig = async () => {
    try {
      const response = await fetch("/api/config", { cache: "no-store" })
      if (response.ok) {
        const data = await response.json()
        setConfig(data.config)
      }
    } catch (error) {
      console.error("[v0] Failed to load config:", error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadConfig()
  }, [])

  const refreshConfig = async () => {
    setLoading(true)
    await loadConfig()
  }

  return <ConfigContext.Provider value={{ config, loading, refreshConfig }}>{children}</ConfigContext.Provider>
}

export function useConfig() {
  const context = useContext(ConfigContext)
  if (!context) {
    throw new Error("useConfig must be used within ConfigProvider")
  }
  return context
}
