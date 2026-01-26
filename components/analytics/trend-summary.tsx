import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"
import type { TrendSummary as TrendSummaryType } from "@/lib/api"

interface TrendSummaryProps {
  trends: TrendSummaryType
}

export function TrendSummary({ trends }: TrendSummaryProps) {
  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case "Increasing":
        return <TrendingUp className="h-4 w-4 text-green-600" />
      case "Decreasing":
        return <TrendingDown className="h-4 w-4 text-red-600" />
      case "Stable":
        return <Minus className="h-4 w-4 text-blue-600" />
      default:
        return <Minus className="h-4 w-4 text-muted-foreground" />
    }
  }

  const metricLabels = {
    soil_moisture: "Soil Moisture",
    ph: "pH Level",
    temperature: "Temperature",
    humidity: "Humidity",
  }

  return (
    <div>
      <h2 className="mb-4 text-2xl font-semibold">Trend Analysis</h2>
      <p className="mb-4 text-sm text-muted-foreground">Comparing last 7 days vs previous 7 days</p>
      <div className="grid gap-6 md:grid-cols-2">
        {Object.entries(trends).map(([sensorId, sensorTrends]) => (
          <Card key={sensorId}>
            <CardHeader>
              <CardTitle>{sensorId}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {Object.entries(sensorTrends).map(([metric, data]) => (
                  <div key={metric} className="flex items-center justify-between border-b pb-2 last:border-0">
                    <div className="flex items-center gap-2">
                      {getTrendIcon(data.trend)}
                      <span className="text-sm font-medium">{metricLabels[metric as keyof typeof metricLabels]}</span>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-semibold">
                        {data.last_week_avg !== null ? data.last_week_avg.toFixed(1) : "N/A"}
                      </div>
                      {data.change !== null && (
                        <div className="text-xs text-muted-foreground">
                          {data.change > 0 ? "+" : ""}
                          {data.change.toFixed(1)}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
