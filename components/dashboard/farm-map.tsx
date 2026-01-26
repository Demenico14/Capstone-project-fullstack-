"use client"

import { useEffect, useState } from "react"
import dynamic from "next/dynamic"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { MapPin, Loader2 } from "lucide-react"
import type { SensorReading } from "@/lib/api"

const LeafletMapClient = dynamic(() => import("./leaflet-map-client"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  ),
})

interface FarmMapProps {
  readings: SensorReading[]
  diseaseAlerts?: { [sensorId: string]: string }
}

interface NodeCoordinate {
  lat: number
  lng: number
}

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

export function FarmMap({ readings, diseaseAlerts = {} }: FarmMapProps) {
  const [nodes, setNodes] = useState<SensorNode[]>([])
  const [mapReady, setMapReady] = useState(false)
  const [center, setCenter] = useState<[number, number]>([-17.8252, 31.0335])
  const [zoom] = useState(15)

  useEffect(() => {
    console.log("[v0] FarmMap mounted, readings:", readings.length)
    console.log("[v0] Disease alerts:", diseaseAlerts)

    // Parse node coordinates from environment variable
    const coordsStr = process.env.NEXT_PUBLIC_NODE_COORDINATES
    console.log("[v0] Node coordinates string:", coordsStr)

    if (coordsStr) {
      try {
        const parsed = JSON.parse(coordsStr)
        const sensorNodes: SensorNode[] = []

        Object.entries(parsed).forEach(([sensorId, coordStr]) => {
          const [lat, lng] = (coordStr as string).split(",").map(Number)

          // Find latest reading for this sensor
          const latestReading = readings.find((r) => r.sensor_id === sensorId)

          // Determine status based on disease alerts
          let status: "healthy" | "warning" | "danger" = "healthy"
          if (diseaseAlerts[sensorId]) {
            const alert = diseaseAlerts[sensorId].toLowerCase()
            if (alert.includes("infected") || alert.includes("danger")) {
              status = "danger"
            } else if (alert.includes("risk") || alert.includes("warning")) {
              status = "warning"
            }
          }

          sensorNodes.push({
            id: sensorId,
            name: sensorId.replace("_", " "),
            lat,
            lng,
            status,
            lastReading: latestReading
              ? {
                  temperature: latestReading.temperature,
                  humidity: latestReading.humidity,
                  soil_moisture: latestReading.soil_moisture,
                }
              : undefined,
          })

          console.log("[v0] Created node for", sensorId, ":", { lat, lng, status })
        })

        setNodes(sensorNodes)
      } catch (error) {
        console.error("[v0] Failed to parse node coordinates:", error)
      }
    }

    // Get center coordinates
    const centerLatStr = process.env.NEXT_PUBLIC_FARM_CENTER_LAT
    const centerLngStr = process.env.NEXT_PUBLIC_FARM_CENTER_LNG
    if (centerLatStr && centerLngStr) {
      const lat = Number.parseFloat(centerLatStr)
      const lng = Number.parseFloat(centerLngStr)
      setCenter([lat, lng])
      console.log("[v0] Map center:", { lat, lng })
    }

    setMapReady(true)
  }, [readings, diseaseAlerts])

  if (!mapReady || nodes.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MapPin className="h-5 w-5" />
            Farm Overview Map
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-[400px] items-center justify-center">
            {!mapReady ? (
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            ) : (
              <div className="text-center text-muted-foreground">
                <MapPin className="mx-auto mb-2 h-12 w-12" />
                <p>No sensor coordinates configured</p>
                <p className="mt-1 text-sm">Add NEXT_PUBLIC_NODE_COORDINATES to your .env.local file</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MapPin className="h-5 w-5" />
          Farm Overview Map
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[500px] w-full overflow-hidden rounded-lg border">
          <LeafletMapClient nodes={nodes} center={center} zoom={zoom} />
        </div>

        <div className="mt-4 flex items-center justify-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-green-500" />
            <span>Healthy</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-yellow-500" />
            <span>At Risk</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-red-500" />
            <span>Infected</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
