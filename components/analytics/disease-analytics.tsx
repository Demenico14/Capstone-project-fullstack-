"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { AlertTriangle, TrendingUp, TrendingDown, Activity, CheckCircle2, Leaf } from "lucide-react"
import type { DiseaseStats, DiseaseTrend } from "@/lib/api"
import { useMemo } from "react"

interface DiseaseAnalyticsProps {
  stats: DiseaseStats
  trends: DiseaseTrend[]
}

export function DiseaseAnalytics({ stats, trends }: DiseaseAnalyticsProps) {
  // Calculate trend insights
  const trendInsights = useMemo(() => {
    if (!trends || trends.length === 0) return null

    // Group by disease type and calculate weekly trends
    const diseaseGroups = trends.reduce(
      (acc, trend) => {
        if (!acc[trend.disease_type]) {
          acc[trend.disease_type] = []
        }
        acc[trend.disease_type].push(trend)
        return acc
      },
      {} as Record<string, DiseaseTrend[]>,
    )

    // Calculate if diseases are increasing or decreasing
    const insights = Object.entries(diseaseGroups).map(([diseaseType, data]) => {
      const sortedData = data.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
      const recentWeek = sortedData.slice(-7)
      const previousWeek = sortedData.slice(-14, -7)

      const recentTotal = recentWeek.reduce((sum, d) => sum + d.count, 0)
      const previousTotal = previousWeek.reduce((sum, d) => sum + d.count, 0)

      const change = previousTotal > 0 ? ((recentTotal - previousTotal) / previousTotal) * 100 : 0

      return {
        diseaseType,
        recentTotal,
        previousTotal,
        change,
        trend: change > 5 ? "increasing" : change < -5 ? "decreasing" : "stable",
      }
    })

    return insights
  }, [trends])

  const healthPercentage =
    stats.total_detections > 0 ? ((stats.healthy_count / stats.total_detections) * 100).toFixed(1) : "0"

  const diseasePercentage =
    stats.total_detections > 0 ? ((stats.diseased_count / stats.total_detections) * 100).toFixed(1) : "0"

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Leaf className="h-6 w-6 text-primary" />
          Crop Health Analytics
        </h2>
        <p className="text-muted-foreground mt-1">Disease detection insights and trends</p>
      </div>

      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Scans</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_detections}</div>
            <p className="text-xs text-muted-foreground mt-1">All-time disease scans</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Healthy Crops</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{healthPercentage}%</div>
            <p className="text-xs text-muted-foreground mt-1">{stats.healthy_count} healthy detections</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Disease Rate</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{diseasePercentage}%</div>
            <p className="text-xs text-muted-foreground mt-1">{stats.diseased_count} diseased detections</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recent Activity</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.recent_detections_7days}</div>
            <p className="text-xs text-muted-foreground mt-1">Scans in last 7 days</p>
          </CardContent>
        </Card>
      </div>

      {/* Disease Distribution and Trends */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Disease Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Disease Distribution</CardTitle>
            <CardDescription>Breakdown of detected conditions</CardDescription>
          </CardHeader>
          <CardContent>
            {stats.disease_distribution.length === 0 ? (
              <div className="text-sm text-muted-foreground text-center py-8">No disease data available yet</div>
            ) : (
              <div className="space-y-4">
                {stats.disease_distribution.map((disease) => {
                  const percentage =
                    stats.total_detections > 0 ? ((disease.count / stats.total_detections) * 100).toFixed(1) : "0"

                  return (
                    <div key={disease.disease_type} className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          {disease.disease_type.toLowerCase() === "healthy" ? (
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
                            disease.disease_type.toLowerCase() === "healthy" ? "bg-green-600" : "bg-orange-600"
                          }`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Avg confidence: {(disease.avg_confidence * 100).toFixed(1)}%
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Trend Insights */}
        <Card>
          <CardHeader>
            <CardTitle>Trend Analysis</CardTitle>
            <CardDescription>Weekly disease trends (last 7 vs previous 7 days)</CardDescription>
          </CardHeader>
          <CardContent>
            {!trendInsights || trendInsights.length === 0 ? (
              <div className="text-sm text-muted-foreground text-center py-8">Not enough data for trend analysis</div>
            ) : (
              <div className="space-y-4">
                {trendInsights.map((insight) => (
                  <div
                    key={insight.diseaseType}
                    className="flex items-center justify-between p-3 rounded-lg border border-border"
                  >
                    <div className="flex items-center gap-3">
                      {insight.diseaseType.toLowerCase() === "healthy" ? (
                        <CheckCircle2 className="h-5 w-5 text-green-600" />
                      ) : (
                        <AlertTriangle className="h-5 w-5 text-orange-600" />
                      )}
                      <div>
                        <div className="font-medium capitalize text-sm">{insight.diseaseType}</div>
                        <div className="text-xs text-muted-foreground">{insight.recentTotal} recent detections</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {insight.trend === "increasing" && (
                        <>
                          <TrendingUp className="h-4 w-4 text-orange-600" />
                          <span className="text-sm font-medium text-orange-600">
                            +{Math.abs(insight.change).toFixed(0)}%
                          </span>
                        </>
                      )}
                      {insight.trend === "decreasing" && (
                        <>
                          <TrendingDown className="h-4 w-4 text-green-600" />
                          <span className="text-sm font-medium text-green-600">{insight.change.toFixed(0)}%</span>
                        </>
                      )}
                      {insight.trend === "stable" && (
                        <span className="text-sm font-medium text-muted-foreground">Stable</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recommendations */}
      {stats.diseased_count > 0 && (
        <Card className="border-orange-200 bg-orange-50 dark:bg-orange-950/20 dark:border-orange-900">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-orange-900 dark:text-orange-100">
              <AlertTriangle className="h-5 w-5" />
              Health Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-orange-900 dark:text-orange-100">
            {stats.diseased_count > stats.healthy_count && (
              <p>⚠️ Disease rate is high. Consider immediate intervention and treatment.</p>
            )}
            <p>📊 Monitor affected areas closely and track disease progression over time.</p>
            <p>🔬 Upload regular leaf samples to detect early signs of disease spread.</p>
            <p>
              💡 Review environmental conditions (temperature, humidity, soil moisture) that may contribute to disease.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
