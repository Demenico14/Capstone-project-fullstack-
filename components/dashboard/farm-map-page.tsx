"use client"

import { useEffect, useState } from "react"
import { api, type SensorReading, type DiseaseStats } from "@/lib/api"
import { FarmMap } from "./farm-map"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle } from "lucide-react"

export function FarmMapPage() {
  const [latestReadings, setLatestReadings] = useState<SensorReading[]>([])
  const [diseaseStats, setDiseaseStats] = useState<DiseaseStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [readings, disease] = await Promise.all([api.getLatestReadings(), api.getDiseaseStats()])

      setLatestReadings(readings)
      setDiseaseStats(disease)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load map data")
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <Skeleton className="h-[500px]" />
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    )
  }

  const diseaseAlerts: { [sensorId: string]: string } = {}
  latestReadings.forEach((reading) => {
    const diseaseRate =
      diseaseStats && diseaseStats.total_detections > 0
        ? diseaseStats.diseased_count / diseaseStats.total_detections
        : 0
    if (diseaseRate === 0) {
      diseaseAlerts[reading.sensor_id] = "Healthy"
    } else if (diseaseRate < 0.3) {
      diseaseAlerts[reading.sensor_id] = "At Risk"
    } else {
      diseaseAlerts[reading.sensor_id] = "Infected"
    }
  })

  return <FarmMap readings={latestReadings} diseaseAlerts={diseaseAlerts} />
}
