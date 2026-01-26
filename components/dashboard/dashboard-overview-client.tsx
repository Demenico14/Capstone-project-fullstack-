"use client"

import { useEffect, useState } from "react"
import { api, type SensorReading, type Statistics, type DiseaseStats, type DailyAverage } from "@/lib/api"
import { SensorCard } from "./sensor-card"
import { StatsGrid } from "./stats-grid"
import { RecentReadings } from "./recent-readings"
import { DiseaseAlerts } from "./disease-alerts"
import { TrendCharts } from "./trend-charts"
import { FarmMapPage } from "./farm-map-page"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle } from "lucide-react"

export default function DashboardOverview() {
  const [latestReadings, setLatestReadings] = useState<SensorReading[]>([])
  const [stats, setStats] = useState<Statistics | null>(null)
  const [diseaseStats, setDiseaseStats] = useState<DiseaseStats | null>(null)
  const [dailyAverages, setDailyAverages] = useState<{ [sensorId: string]: DailyAverage[] }>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      console.log("[v0] Loading dashboard data...")
      const [readings, statistics, disease, averages] = await Promise.all([
        api.getLatestReadings(),
        api.getStatistics(),
        api.getDiseaseStats(),
        api.getDailyAverages(14),
      ])

      console.log("[v0] Daily averages from API:", averages)

      setLatestReadings(readings)
      setStats(statistics)
      setDiseaseStats(disease)
      setDailyAverages(averages)
    } catch (err) {
      console.error("[v0] Dashboard load error:", err)
      setError(err instanceof Error ? err.message : "Failed to load dashboard data")
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-4 sm:space-y-6">
        <div className="grid gap-3 sm:gap-4 grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-24 sm:h-32" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Key Statistics */}
      {stats && <StatsGrid stats={stats} />}

      {/* Farm Map */}
      <div>
        <h2 className="mb-3 sm:mb-4 text-xl sm:text-2xl font-semibold">Farm Overview Map</h2>
        <FarmMapPage />
      </div>

      {/* Health Alerts and Recent Readings */}
      <div className="grid gap-4 sm:gap-6 lg:grid-cols-2">
        {diseaseStats && <DiseaseAlerts stats={diseaseStats} />}
        <RecentReadings readings={latestReadings.slice(0, 5)} />
      </div>

      {/* Trend Analysis */}
      <div>
        <h2 className="mb-3 sm:mb-4 text-xl sm:text-2xl font-semibold">Trend Analysis</h2>
        <TrendCharts dailyAverages={dailyAverages} />
      </div>

      {/* Active Sensors */}
      <div>
        <h2 className="mb-3 sm:mb-4 text-xl sm:text-2xl font-semibold">Active Sensors</h2>
        <div className="grid gap-4 sm:gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {latestReadings.map((reading) => (
            <SensorCard key={reading.sensor_id} reading={reading} />
          ))}
        </div>
      </div>
    </div>
  )
}
