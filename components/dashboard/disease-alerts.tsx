"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AlertTriangle, CheckCircle, AlertCircle } from "lucide-react"
import type { DiseaseStats } from "@/lib/api"

interface DiseaseAlertsProps {
  stats: DiseaseStats
  sensorId?: string
}

export function DiseaseAlerts({ stats, sensorId }: DiseaseAlertsProps) {
  const getAlertLevel = (): { level: "healthy" | "warning" | "danger"; message: string; icon: any } => {
    const diseaseRate = stats.total_detections > 0 ? stats.diseased_count / stats.total_detections : 0

    if (diseaseRate === 0) {
      return {
        level: "healthy",
        message: "All crops are healthy",
        icon: CheckCircle,
      }
    } else if (diseaseRate < 0.3) {
      return {
        level: "warning",
        message: "Some crops at risk - monitor closely",
        icon: AlertCircle,
      }
    } else {
      return {
        level: "danger",
        message: "Disease outbreak detected - take action",
        icon: AlertTriangle,
      }
    }
  }

  const alert = getAlertLevel()
  const Icon = alert.icon

  const getAlertColor = () => {
    switch (alert.level) {
      case "healthy":
        return "border-green-500 bg-green-50 text-green-900"
      case "warning":
        return "border-yellow-500 bg-yellow-50 text-yellow-900"
      case "danger":
        return "border-red-500 bg-red-50 text-red-900"
    }
  }

  return (
    <Card className={`border-2 ${getAlertColor()}`}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon className="h-5 w-5" />
          Crop Health Alert {sensorId && `- ${sensorId}`}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <p className="text-lg font-semibold">{alert.message}</p>
            <p className="mt-1 text-sm opacity-80">
              {stats.diseased_count} diseased out of {stats.total_detections} total detections
            </p>
          </div>

          {stats.disease_distribution.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Detected Diseases:</p>
              {stats.disease_distribution.map((disease) => (
                <div
                  key={disease.disease_type}
                  className="flex items-center justify-between rounded-lg bg-background p-2"
                >
                  <span className="text-sm">{disease.disease_type}</span>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{disease.count} cases</Badge>
                    <Badge variant="secondary">{(disease.avg_confidence * 100).toFixed(0)}% confidence</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}

          {stats.recent_detections_7days > 0 && (
            <div className="rounded-lg bg-background p-3">
              <p className="text-sm">
                <span className="font-semibold">{stats.recent_detections_7days}</span> new detections in the last 7 days
              </p>
              {stats.last_detection && (
                <p className="mt-1 text-xs opacity-70">
                  Last detected: {new Date(stats.last_detection).toLocaleString()}
                </p>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
