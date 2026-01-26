import { api } from "@/lib/api"
import { SensorCard } from "./sensor-card"
import { StatsGrid } from "./stats-grid"
import { RecentReadings } from "./recent-readings"
import { FarmMap } from "./farm-map"
import { DiseaseAlerts } from "./disease-alerts"
import { TrendCharts } from "./trend-charts"

export default async function DashboardOverview() {
  try {
    const [latestReadings, stats, diseaseStats, dailyAverages] = await Promise.all([
      api.getLatestReadings(),
      api.getStatistics(),
      api.getDiseaseStats(),
      api.getDailyAverages(14),
    ])

    const diseaseAlerts: { [sensorId: string]: string } = {}
    latestReadings.forEach((reading) => {
      // This would be populated from sensor-specific disease stats
      // For now, using global stats as fallback
      const diseaseRate =
        diseaseStats.total_detections > 0 ? diseaseStats.diseased_count / diseaseStats.total_detections : 0
      if (diseaseRate === 0) {
        diseaseAlerts[reading.sensor_id] = "Healthy"
      } else if (diseaseRate < 0.3) {
        diseaseAlerts[reading.sensor_id] = "At Risk"
      } else {
        diseaseAlerts[reading.sensor_id] = "Infected"
      }
    })

    return (
      <div>
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-balance">CropIoT Dashboard</h1>
          <p className="mt-2 text-muted-foreground">Real-time monitoring of your agricultural sensors</p>
        </div>

        <StatsGrid stats={stats} />

        <div className="mt-8">
          <DiseaseAlerts stats={diseaseStats} />
        </div>

        <div className="mt-8">
          <FarmMap readings={latestReadings} diseaseAlerts={diseaseAlerts} />
        </div>

        <div className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold">Active Sensors</h2>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {latestReadings.map((reading) => (
              <SensorCard key={reading.sensor_id} reading={reading} />
            ))}
          </div>
        </div>

        <div className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold">Trend Analysis</h2>
          <TrendCharts dailyAverages={dailyAverages} />
        </div>

        <div className="mt-8">
          <RecentReadings readings={latestReadings} />
        </div>
      </div>
    )
  } catch (error) {
    return (
      <div>
        <div className="rounded-lg border border-destructive bg-destructive/10 p-6">
          <h2 className="text-lg font-semibold text-destructive">Error Loading Dashboard</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Unable to connect to the backend API. Please ensure the Python API server is running on port 5000.
          </p>
        </div>
      </div>
    )
  }
}
