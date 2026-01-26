"use client"

import { useEffect, useRef, useState } from "react"
import "leaflet/dist/leaflet.css"

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

interface LeafletMapClientProps {
  nodes: SensorNode[]
  center: [number, number]
  zoom: number
}

export default function LeafletMapClient({ nodes, center, zoom }: LeafletMapClientProps) {
  const mapRef = useRef<any>(null)
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const satelliteLayerRef = useRef<any>(null)
  const [activeLayer, setActiveLayer] = useState<string>("none")
  const [provider] = useState<"sentinel">("sentinel")
  const [loading, setLoading] = useState(false)
  const [leafletLoaded, setLeafletLoaded] = useState(false)

  useEffect(() => {
    if (typeof window === "undefined") return

    // Dynamically import Leaflet
    import("leaflet").then((L) => {
      // Fix for default marker icons
      delete (L.Icon.Default.prototype as any)._getIconUrl
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
        iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
        shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
      })

      setLeafletLoaded(true)
    })
  }, [])

  useEffect(() => {
    if (!leafletLoaded || !mapContainerRef.current || mapRef.current) return

    console.log("[v0] Initializing Leaflet map with", nodes.length, "nodes")

    // Import Leaflet again to use it
    import("leaflet").then((L) => {
      if (!mapContainerRef.current) return

      // Initialize map
      const map = L.map(mapContainerRef.current).setView(center, zoom)
      mapRef.current = map

      // Add OpenStreetMap tiles
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap contributors",
        maxZoom: 19,
      }).addTo(map)

      // Add markers for each sensor node
      nodes.forEach((node) => {
        const color = node.status === "healthy" ? "#22c55e" : node.status === "warning" ? "#f59e0b" : "#ef4444"

        // Create custom icon
        const customIcon = L.divIcon({
          className: "custom-marker",
          html: `
            <div style="
              background-color: ${color};
              width: 30px;
              height: 30px;
              border-radius: 50%;
              border: 3px solid white;
              box-shadow: 0 2px 4px rgba(0,0,0,0.3);
              display: flex;
              align-items: center;
              justify-content: center;
              color: white;
              font-weight: bold;
              font-size: 12px;
            ">
              ${node.id.replace("Sensor_", "")}
            </div>
          `,
          iconSize: [30, 30],
          iconAnchor: [15, 15],
        })

        // Create popup content
        const popupContent = `
          <div style="min-width: 200px;">
            <h3 style="font-weight: bold; margin-bottom: 8px;">${node.name}</h3>
            <p style="margin: 4px 0;"><strong>Status:</strong> ${node.status}</p>
            ${
              node.lastReading
                ? `
              ${
                node.lastReading.temperature !== undefined
                  ? `<p style="margin: 4px 0;"><strong>Temperature:</strong> ${node.lastReading.temperature.toFixed(1)}°C</p>`
                  : ""
              }
              ${
                node.lastReading.humidity !== undefined
                  ? `<p style="margin: 4px 0;"><strong>Humidity:</strong> ${node.lastReading.humidity.toFixed(1)}%</p>`
                  : ""
              }
              ${
                node.lastReading.soil_moisture !== undefined
                  ? `<p style="margin: 4px 0;"><strong>Soil Moisture:</strong> ${node.lastReading.soil_moisture.toFixed(1)}%</p>`
                  : ""
              }
            `
                : '<p style="margin: 4px 0;">No recent readings</p>'
            }
          </div>
        `

        // Add marker with popup
        L.marker([node.lat, node.lng], { icon: customIcon }).addTo(map).bindPopup(popupContent)
      })

      console.log("[v0] Map initialized successfully")
    })

    // Cleanup
    return () => {
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
      }
    }
  }, [leafletLoaded, nodes, center, zoom])

  const loadSatelliteLayer = async (type: string) => {
    if (!mapRef.current || !leafletLoaded) return

    setLoading(true)
    console.log("[v0] Loading satellite layer:", type, "from Sentinel Hub")

    try {
      const L = await import("leaflet")

      if (satelliteLayerRef.current) {
        mapRef.current.removeLayer(satelliteLayerRef.current)
        satelliteLayerRef.current = null
      }

      if (type === "none") {
        setActiveLayer("none")
        setLoading(false)
        return
      }

      // Calculate bounding box around farm
      const size = 0.02
      const bounds: any = [
        [center[0] - size / 2, center[1] - size / 2],
        [center[0] + size / 2, center[1] + size / 2],
      ]

      const response = await fetch(`/api/satellite?type=${type}&lat=${center[0]}&lng=${center[1]}&size=${size}`)

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.message || "Failed to load satellite imagery from Sentinel Hub")
      }

      const blob = await response.blob()
      const imageUrl = URL.createObjectURL(blob)

      const imageOverlay = L.imageOverlay(imageUrl, bounds, {
        opacity: 0.7,
        interactive: false,
        zIndex: 1,
      })

      imageOverlay.addTo(mapRef.current)
      satelliteLayerRef.current = imageOverlay

      mapRef.current.eachLayer((layer: any) => {
        if (layer instanceof L.Marker) {
          layer.setZIndexOffset(1000)
        }
      })

      setActiveLayer(type)
      console.log("[v0] Satellite layer loaded successfully:", type)
    } catch (error) {
      console.error("[v0] Error loading satellite layer:", error)
      alert(
        `Failed to load satellite imagery: ${error instanceof Error ? error.message : "Unknown error"}\n\nMake sure your Sentinel Hub credentials are configured in .env.local`,
      )
    } finally {
      setLoading(false)
    }
  }

  if (!leafletLoaded) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <div className="text-sm text-gray-500">Loading map...</div>
      </div>
    )
  }

  return (
    <div className="relative h-full w-full">
      <div className="absolute right-4 top-4 z-[1000] flex flex-col gap-2 rounded-lg bg-white p-2 shadow-lg">
        <div className="text-xs font-semibold text-gray-700">Satellite Layers</div>
        <button
          onClick={() => loadSatelliteLayer("none")}
          disabled={loading}
          className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
            activeLayer === "none" ? "bg-blue-500 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          } ${loading ? "cursor-not-allowed opacity-50" : ""}`}
        >
          None
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
        <button
          onClick={() => loadSatelliteLayer("true-color")}
          disabled={loading}
          className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
            activeLayer === "true-color" ? "bg-purple-500 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          } ${loading ? "cursor-not-allowed opacity-50" : ""}`}
        >
          True Color
        </button>
        {loading && <div className="text-center text-xs text-gray-500">Loading...</div>}
      </div>

      {activeLayer !== "none" && (
        <div className="absolute bottom-4 left-4 z-[1000] rounded-lg bg-white p-3 shadow-lg">
          <div className="mb-2 text-xs font-semibold text-gray-700">
            {activeLayer === "ndvi" && "NDVI Legend"}
            {activeLayer === "moisture" && "Moisture Legend"}
            {activeLayer === "true-color" && "True Color"}
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

      <div ref={mapContainerRef} className="h-full w-full rounded-lg" style={{ minHeight: "400px" }} />
    </div>
  )
}
