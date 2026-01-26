"use client"

import { useEffect, useRef, useState } from "react"

interface SensorNode {
  id: string
  name: string
  lat: number
  lng: number
  status: "healthy" | "warning" | "danger"
  lastReading?: {
    temperature?: number
    humidity?: number
    soil_moisture?: number
  }
}

interface GeeMapClientProps {
  nodes: SensorNode[]
  center: [number, number]
  zoom: number
}

export default function GeeMapClient({ nodes, center, zoom }: GeeMapClientProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const [activeLayer, setActiveLayer] = useState<string>("true-color")
  const [loading, setLoading] = useState(false)
  const [mapImageUrl, setMapImageUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    console.log("[v0] GEE Map initialized with", nodes.length, "nodes")
    loadSatelliteLayer(activeLayer)
  }, [])

  const loadSatelliteLayer = async (type: string) => {
    setLoading(true)
    setError(null)
    console.log("[v0] Loading GEE satellite layer:", type)

    try {
      const size = 0.02
      const response = await fetch(`/api/gee?type=${type}&lat=${center[0]}&lng=${center[1]}&size=${size}`)

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.message || "Failed to load satellite imagery")
      }

      const blob = await response.blob()
      const imageUrl = URL.createObjectURL(blob)
      setMapImageUrl(imageUrl)
      setActiveLayer(type)
      console.log("[v0] GEE satellite layer loaded successfully:", type)
    } catch (err) {
      console.error("[v0] Error loading GEE satellite layer:", err)
      setError(err instanceof Error ? err.message : "Unknown error")
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy":
        return "#22c55e"
      case "warning":
        return "#f59e0b"
      case "danger":
        return "#ef4444"
      default:
        return "#6b7280"
    }
  }

  return (
    <div className="relative h-full w-full">
      {/* Layer Controls */}
      <div className="absolute right-4 top-4 z-10 flex flex-col gap-2 rounded-lg bg-white p-2 shadow-lg">
        <div className="text-xs font-semibold text-gray-700">Satellite Layers</div>
        <button
          onClick={() => loadSatelliteLayer("true-color")}
          disabled={loading}
          className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
            activeLayer === "true-color" ? "bg-purple-500 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          } ${loading ? "cursor-not-allowed opacity-50" : ""}`}
        >
          True Color
        </button>
        <button
          onClick={() => loadSatelliteLayer("ndvi")}
          disabled={loading}
          className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
            activeLayer === "ndvi" ? "bg-green-500 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          } ${loading ? "cursor-not-allowed opacity-50" : ""}`}
        >
          NDVI
        </button>
        <button
          onClick={() => loadSatelliteLayer("moisture")}
          disabled={loading}
          className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
            activeLayer === "moisture" ? "bg-blue-500 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          } ${loading ? "cursor-not-allowed opacity-50" : ""}`}
        >
          Moisture
        </button>
        {loading && <div className="text-center text-xs text-gray-500">Loading...</div>}
      </div>

      {/* Legend */}
      {activeLayer !== "true-color" && !loading && !error && (
        <div className="absolute bottom-4 left-4 z-10 rounded-lg bg-white p-3 shadow-lg">
          <div className="mb-2 text-xs font-semibold text-gray-700">
            {activeLayer === "ndvi" && "NDVI Legend"}
            {activeLayer === "moisture" && "Moisture Legend"}
          </div>
          {activeLayer === "ndvi" && (
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded" style={{ backgroundColor: "#cc3333" }} />
                <span>Stressed (&lt;0.2)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded" style={{ backgroundColor: "#e6b34d" }} />
                <span>Sparse (0.2-0.4)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded" style={{ backgroundColor: "#99e666" }} />
                <span>Moderate (0.4-0.6)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded" style={{ backgroundColor: "#33cc4d" }} />
                <span>Healthy (0.6-0.8)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded" style={{ backgroundColor: "#1a8033" }} />
                <span>Very Healthy (&gt;0.8)</span>
              </div>
            </div>
          )}
          {activeLayer === "moisture" && (
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded" style={{ backgroundColor: "#1a4dcc" }} />
                <span>High (&gt;0.3)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded" style={{ backgroundColor: "#4d99e6" }} />
                <span>Moderate (0.1-0.3)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded" style={{ backgroundColor: "#e6b34d" }} />
                <span>Low (-0.1-0.1)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded" style={{ backgroundColor: "#e64d33" }} />
                <span>Very Dry (&lt;-0.1)</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Map Container */}
      <div ref={mapContainerRef} className="relative h-full w-full overflow-hidden rounded-lg bg-gray-100">
        {error && (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <p className="text-red-500 font-medium">Failed to load satellite imagery</p>
              <p className="text-sm text-gray-600 mt-2">{error}</p>
            </div>
          </div>
        )}

        {!error && mapImageUrl && (
          <div className="relative h-full w-full">
            <img
              src={mapImageUrl || "/placeholder.svg"}
              alt="Satellite imagery"
              className="h-full w-full object-cover"
            />

            {/* Sensor Markers Overlay */}
            <svg className="absolute inset-0 h-full w-full pointer-events-none">
              {nodes.map((node, index) => {
                const latRange = 0.02
                const lngRange = 0.02
                const x = ((node.lng - (center[1] - lngRange / 2)) / lngRange) * 100
                const y = (1 - (node.lat - (center[0] - latRange / 2)) / latRange) * 100

                return (
                  <g key={node.id}>
                    <circle
                      cx={`${x}%`}
                      cy={`${y}%`}
                      r="15"
                      fill={getStatusColor(node.status)}
                      stroke="white"
                      strokeWidth="3"
                      className="pointer-events-auto cursor-pointer"
                    />
                    <text
                      x={`${x}%`}
                      y={`${y}%`}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fill="white"
                      fontSize="12"
                      fontWeight="bold"
                      className="pointer-events-none"
                    >
                      {node.id.replace("Sensor_", "")}
                    </text>
                  </g>
                )
              })}
            </svg>
          </div>
        )}

        {loading && (
          <div className="flex h-full items-center justify-center">
            <div className="text-sm text-gray-500">Loading satellite imagery...</div>
          </div>
        )}
      </div>
    </div>
  )
}
