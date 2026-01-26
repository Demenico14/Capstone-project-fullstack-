import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft } from "lucide-react"
import Link from "next/link"

interface SensorDetailProps {
  sensorId: string
  stats: any
  yieldData?: any
  dailyAverages?: any
}

export function SensorDetail({ sensorId, stats, yieldData, dailyAverages }: SensorDetailProps) {
  return (
    <div>
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Dashboard
      </Link>

      <div className="mb-8">
        <h1 className="text-4xl font-bold text-balance">{sensorId}</h1>
        <p className="mt-2 text-muted-foreground">Detailed sensor information</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Statistics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">Total Readings</p>
                <p className="text-2xl font-bold">{stats?.total_readings || 0}</p>
              </div>
              {stats?.date_range && (
                <div>
                  <p className="text-sm text-muted-foreground">Date Range</p>
                  <p className="text-sm">
                    {stats.date_range.start} to {stats.date_range.end}
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {yieldData && (
          <Card>
            <CardHeader>
              <CardTitle>Yield Estimate</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm text-muted-foreground">Score</span>
                <Badge>Grade {yieldData.grade}</Badge>
              </div>
              <div className="text-3xl font-bold">{yieldData.score}</div>
            </CardContent>
          </Card>
        )}
      </div>

      {stats?.metrics && Object.keys(stats.metrics).length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Current Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {Object.entries(stats.metrics).map(([metric, data]: [string, any]) => (
                <div key={metric}>
                  <p className="text-sm text-muted-foreground capitalize">{metric.replace("_", " ")}</p>
                  {data ? (
                    <>
                      <p className="text-2xl font-bold">{data.current}</p>
                      <p className="text-xs text-muted-foreground">
                        Avg: {data.average} | Min: {data.min} | Max: {data.max}
                      </p>
                    </>
                  ) : (
                    <p className="text-sm text-muted-foreground">No data</p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
