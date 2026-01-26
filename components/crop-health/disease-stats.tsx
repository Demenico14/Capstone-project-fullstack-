"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Activity, AlertTriangle, CheckCircle2 } from "lucide-react"
import { api, type DiseaseStats as DiseaseStatsType } from "@/lib/api"

interface DiseaseStatsProps {
  sensorId?: string
  refreshTrigger?: number
}

export function DiseaseStats({ sensorId, refreshTrigger }: DiseaseStatsProps) {
  const [stats, setStats] = useState<DiseaseStatsType | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.getDiseaseStats(sensorId)
        setStats(data)
      } catch (error) {
        console.error("Failed to fetch disease stats:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [sensorId, refreshTrigger])

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Disease Statistics</CardTitle>
          {sensorId && <CardDescription>For {sensorId}</CardDescription>}
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Loading...</div>
        </CardContent>
      </Card>
    )
  }

  if (!stats) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Disease Statistics</CardTitle>
          {sensorId && <CardDescription>For {sensorId}</CardDescription>}
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">No data available</div>
        </CardContent>
      </Card>
    )
  }

  const healthPercentage =
    stats.total_detections > 0 ? ((stats.healthy_count / stats.total_detections) * 100).toFixed(1) : "0"

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Scans</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_detections}</div>
            <p className="text-xs text-muted-foreground mt-1">{stats.recent_detections_7days} in last 7 days</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Health Rate</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{healthPercentage}%</div>
            <p className="text-xs text-muted-foreground mt-1">
              {stats.healthy_count} healthy / {stats.diseased_count} diseased
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Disease Distribution */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Disease Distribution</CardTitle>
          <CardDescription>Breakdown of detected conditions</CardDescription>
        </CardHeader>
        <CardContent>
          {stats.disease_distribution.length === 0 ? (
            <div className="text-sm text-muted-foreground">No detections yet</div>
          ) : (
            <div className="space-y-3">
              {stats.disease_distribution.map((disease) => {
                const percentage =
                  stats.total_detections > 0 ? ((disease.count / stats.total_detections) * 100).toFixed(1) : "0"

                return (
                  <div key={disease.disease_type} className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        {disease.disease_type.toLowerCase().includes("healthy") ? (
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                        ) : (
                          <AlertTriangle className="h-4 w-4 text-orange-600" />
                        )}
                        <span className="font-medium capitalize">{disease.disease_type}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-muted-foreground">{disease.count}</span>
                        <span className="text-xs text-muted-foreground w-12 text-right">{percentage}%</span>
                      </div>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          disease.disease_type.toLowerCase().includes("healthy") ? "bg-green-600" : "bg-orange-600"
                        }`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
