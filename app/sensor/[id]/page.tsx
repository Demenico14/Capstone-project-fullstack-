"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { api, type YieldPrediction, type TrendSummary, type DailyAverage } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Thermometer,
  Droplets,
  Activity,
  Calendar,
  TrendingUp,
  TrendingDown,
  Minus,
  Sprout,
  AlertCircle,
} from "lucide-react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { YieldEstimates } from "@/components/analytics/yield-estimates"
import { DailyAverages } from "@/components/analytics/daily-averages"
import { DiseaseStats } from "@/components/crop-health/disease-stats"
import { DiseaseHistory } from "@/components/crop-health/disease-history"
import { DiseaseUpload } from "@/components/crop-health/disease-upload"

export default function SensorPage() {
  const params = useParams()
  const sensorId = params.id as string

  // Sensor data state
  const [sensorData, setSensorData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  // Analytics state
  const [yieldEstimates, setYieldEstimates] = useState<any>(null)
  const [dailyAverages, setDailyAverages] = useState<DailyAverage[]>([])

  // Yield prediction state
  const [yieldPrediction, setYieldPrediction] = useState<YieldPrediction | null>(null)
  const [yieldLoading, setYieldLoading] = useState(false)
  const [yieldError, setYieldError] = useState<string | null>(null)

  const [refreshTrigger, setRefreshTrigger] = useState(0)

  useEffect(() => {
    async function loadSensorData() {
      try {
        setLoading(true)
        setError(null)

        const [data, trends, yields, averages] = await Promise.all([
          api.getSensorData(sensorId, 168, 500),
          api.getTrends().catch(() => ({}) as TrendSummary),
          api.getYieldEstimates().catch(() => null),
          api.getDailyAverages(14).catch(() => ({}) as { [sensorId: string]: DailyAverage[] }),
        ])

        if (!data) {
          setError("Sensor not found")
          return
        }

        const sensorTrends = (trends as TrendSummary)[sensorId] || {}

        setSensorData({
          ...data,
          trends: sensorTrends,
        })

        setYieldEstimates(yields ? { [sensorId]: yields[sensorId] } : null)
        const sensorAverages = (averages as { [sensorId: string]: DailyAverage[] })[sensorId] || []
        setDailyAverages(sensorAverages)

        loadYieldPrediction()
      } catch (err) {
        console.error("[v0] Error loading sensor data:", err)
        setError(err instanceof Error ? err.message : "Failed to load sensor data")
      } finally {
        setLoading(false)
      }
    }

    if (sensorId) {
      loadSensorData()
    }
  }, [sensorId])

  const loadYieldPrediction = async () => {
    try {
      setYieldLoading(true)
      setYieldError(null)

      const health = await api.yieldHealthCheck()
      if (!health.model_loaded) {
        setYieldError("Model not loaded")
        return
      }

      const response = await api.getYieldPredictions()
      console.log("[v0] Full yield predictions response:", JSON.stringify(response, null, 2))
      console.log("[v0] Looking for sensor_id:", sensorId)

      const predictions = Array.isArray(response) ? response : response?.predictions || []
      console.log("[v0] Predictions array:", predictions)
      console.log(
        "[v0] Available sensor_ids:",
        predictions.map((p: any) => p.sensor_id),
      )

      const sensorPrediction = predictions.find((p: YieldPrediction) => {
        console.log("[v0] Comparing:", p.sensor_id, "===", sensorId, "?", p.sensor_id === sensorId)
        return p.sensor_id === sensorId
      })

      console.log("[v0] Found sensor prediction:", sensorPrediction)

      if (!sensorPrediction) {
        console.log("[v0] No prediction found for sensor:", sensorId)
        console.log("[v0] This could be because:")
        console.log("[v0] 1. The sensor_id format doesn't match (check case sensitivity)")
        console.log("[v0] 2. The prediction hasn't been generated yet")
        console.log("[v0] 3. The response structure is different than expected")
      }

      setYieldPrediction(sensorPrediction || null)
    } catch (err) {
      console.error("[v0] Error loading yield prediction:", err)
      setYieldError(err instanceof Error ? err.message : "Failed to load prediction")
    } finally {
      setYieldLoading(false)
    }
  }

  const handleUploadComplete = () => {
    setRefreshTrigger((prev) => prev + 1)
  }

  const getYieldGrade = (yieldValue: number): { grade: string; color: string } => {
    if (yieldValue >= 80) return { grade: "Excellent", color: "bg-green-500" }
    if (yieldValue >= 60) return { grade: "Good", color: "bg-blue-500" }
    if (yieldValue >= 40) return { grade: "Fair", color: "bg-yellow-500" }
    return { grade: "Poor", color: "bg-red-500" }
  }

  const totalPages = Math.ceil((sensorData?.readings?.length || 0) / itemsPerPage)
  const paginatedReadings =
    sensorData?.readings?.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage) || []

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

  const metricLabels: Record<string, string> = {
    soil_moisture: "Soil Moisture",
    ph: "pH Level",
    temperature: "Temperature",
    humidity: "Humidity",
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold text-balance">{sensorId}</h1>
        <p className="mt-2 text-muted-foreground">Comprehensive sensor monitoring, analytics, and crop health</p>
      </div>

      {/* Overview Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Temperature</CardTitle>
            <Thermometer className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{sensorData?.latest_reading?.temperature?.toFixed(1) || "N/A"}°C</div>
            <p className="text-xs text-muted-foreground">Avg: {sensorData?.avg_temperature?.toFixed(1) || "N/A"}°C</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Humidity</CardTitle>
            <Droplets className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{sensorData?.latest_reading?.humidity?.toFixed(1) || "N/A"}%</div>
            <p className="text-xs text-muted-foreground">Avg: {sensorData?.avg_humidity?.toFixed(1) || "N/A"}%</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Soil Moisture</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{sensorData?.latest_reading?.soil_moisture?.toFixed(1) || "N/A"}%</div>
            <p className="text-xs text-muted-foreground">Avg: {sensorData?.avg_soil_moisture?.toFixed(1) || "N/A"}%</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Readings</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{sensorData?.total_readings || 0}</div>
            <p className="text-xs text-muted-foreground">Last: {sensorData?.latest_reading?.timestamp || "Never"}</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="data" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="data">Sensor Data</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="health">Crop Health</TabsTrigger>
          <TabsTrigger value="yield">Yield Prediction</TabsTrigger>
        </TabsList>

        {/* Sensor Data Tab */}
        <TabsContent value="data" className="space-y-6">
          {/* Trend Analysis */}
          {sensorData?.trends && Object.keys(sensorData.trends).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Trend Analysis</CardTitle>
                <CardDescription>Comparing last 7 days vs previous 7 days</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(sensorData.trends).map(([metric, data]: [string, any]) => (
                    <div key={metric} className="flex items-center justify-between border-b pb-2 last:border-0">
                      <div className="flex items-center gap-2">
                        {getTrendIcon(data.trend)}
                        <span className="text-sm font-medium">{metricLabels[metric] || metric}</span>
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
          )}

          {/* Data Collection History */}
          <Card>
            <CardHeader>
              <CardTitle>Data Collection History</CardTitle>
              <CardDescription>
                Showing {(currentPage - 1) * itemsPerPage + 1} to{" "}
                {Math.min(currentPage * itemsPerPage, sensorData?.readings?.length || 0)} of{" "}
                {sensorData?.readings?.length || 0} readings
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Timestamp</TableHead>
                      <TableHead className="text-right">Temperature (°C)</TableHead>
                      <TableHead className="text-right">Humidity (%)</TableHead>
                      <TableHead className="text-right">Soil Moisture (%)</TableHead>
                      <TableHead className="text-right">pH</TableHead>
                      <TableHead className="text-right">RSSI (dBm)</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedReadings.map((reading: any, idx: number) => (
                      <TableRow key={idx}>
                        <TableCell className="font-medium">{reading.timestamp}</TableCell>
                        <TableCell className="text-right">
                          {reading.temperature !== null ? reading.temperature.toFixed(1) : "N/A"}
                        </TableCell>
                        <TableCell className="text-right">
                          {reading.humidity !== null ? reading.humidity.toFixed(1) : "N/A"}
                        </TableCell>
                        <TableCell className="text-right">
                          {reading.soil_moisture !== null ? reading.soil_moisture.toFixed(1) : "N/A"}
                        </TableCell>
                        <TableCell className="text-right">
                          {reading.ph !== null ? reading.ph.toFixed(2) : "N/A"}
                        </TableCell>
                        <TableCell className="text-right">
                          <Badge variant={reading.rssi > -80 ? "default" : "destructive"}>{reading.rssi}</Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <button
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="px-4 py-2 text-sm font-medium border rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-accent"
                  >
                    Previous
                  </button>
                  <span className="text-sm text-muted-foreground">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className="px-4 py-2 text-sm font-medium border rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-accent"
                  >
                    Next
                  </button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="space-y-6">
          {yieldEstimates && <YieldEstimates estimates={yieldEstimates} />}
          {dailyAverages && dailyAverages.length > 0 && <DailyAverages data={{ [sensorId]: dailyAverages }} />}
        </TabsContent>

        {/* Crop Health Tab */}
        <TabsContent value="health" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <DiseaseUpload sensorId={sensorId} onUploadComplete={handleUploadComplete} />
            <DiseaseStats sensorId={sensorId} refreshTrigger={refreshTrigger} />
          </div>

          <DiseaseHistory sensorId={sensorId} refreshTrigger={refreshTrigger} />
        </TabsContent>

        {/* Yield Prediction Tab */}
        <TabsContent value="yield" className="space-y-6">
          {yieldLoading ? (
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-center py-8">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                  <span className="ml-3 text-muted-foreground">Loading yield prediction...</span>
                </div>
              </CardContent>
            </Card>
          ) : yieldError ? (
            <Card>
              <CardHeader>
                <CardTitle>Yield Prediction for {sensorId}</CardTitle>
                <CardDescription>AI-powered yield forecasting based on sensor data and crop health</CardDescription>
              </CardHeader>
              <CardContent>
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    {yieldError === "Model not loaded"
                      ? "The yield prediction model is not loaded. Please train the model first."
                      : yieldError}
                  </AlertDescription>
                </Alert>
                {yieldError === "Model not loaded" && (
                  <div className="mt-4 space-y-2 text-sm text-muted-foreground">
                    <p>To enable yield predictions:</p>
                    <ol className="list-decimal list-inside space-y-1 ml-2">
                      <li>Ensure you have historical sensor readings and yield data</li>
                      <li>
                        Run: <code className="bg-muted px-2 py-1 rounded">python backend/ml_pipeline/train.py</code>
                      </li>
                      <li>
                        Start the yield API:{" "}
                        <code className="bg-muted px-2 py-1 rounded">python backend/yield_api.py</code>
                      </li>
                    </ol>
                  </div>
                )}
              </CardContent>
            </Card>
          ) : yieldPrediction && yieldPrediction.predicted_yield ? (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Yield Prediction for {sensorId}</CardTitle>
                    <CardDescription>
                      Predicted on{" "}
                      {yieldPrediction.prediction_date
                        ? new Date(yieldPrediction.prediction_date).toLocaleDateString()
                        : yieldPrediction.timestamp
                          ? new Date(yieldPrediction.timestamp).toLocaleDateString()
                          : "recently"}
                    </CardDescription>
                  </div>
                  <Badge className={getYieldGrade(yieldPrediction.predicted_yield).color}>
                    {getYieldGrade(yieldPrediction.predicted_yield).grade}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Predicted Yield */}
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Sprout className="h-5 w-5 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">Predicted Yield</span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-bold">{yieldPrediction.predicted_yield.toFixed(2)}</span>
                    <span className="text-xl text-muted-foreground">kg</span>
                  </div>
                </div>

                {/* Confidence Interval */}
                {yieldPrediction.confidence_interval && yieldPrediction.confidence_interval.length === 2 && (
                  <div>
                    <p className="text-sm font-medium mb-3">Confidence Interval (95%)</p>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">Lower bound</span>
                        <span className="font-semibold">{yieldPrediction.confidence_interval[0].toFixed(2)} kg</span>
                      </div>
                      <div className="h-3 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{
                            width: `${((yieldPrediction.predicted_yield - yieldPrediction.confidence_interval[0]) / (yieldPrediction.confidence_interval[1] - yieldPrediction.confidence_interval[0])) * 100}%`,
                          }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">Upper bound</span>
                        <span className="font-semibold">{yieldPrediction.confidence_interval[1].toFixed(2)} kg</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Uncertainty Warning */}
                {yieldPrediction.uncertainty && yieldPrediction.uncertainty > 15 && (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      High uncertainty ({yieldPrediction.uncertainty.toFixed(1)}%). More historical data is needed for
                      more accurate predictions.
                    </AlertDescription>
                  </Alert>
                )}

                {/* Data Used */}
                <div className="border-t pt-4">
                  <p className="text-sm font-medium mb-3">Data Used for Prediction</p>
                  <div className="grid grid-cols-2 gap-4">
                    {yieldPrediction.data_points_used !== undefined && (
                      <div className="text-center p-3 bg-muted rounded-lg">
                        <div className="text-2xl font-bold">{yieldPrediction.data_points_used}</div>
                        <div className="text-xs text-muted-foreground mt-1">Data Points</div>
                      </div>
                    )}
                    {yieldPrediction.confidence !== undefined && (
                      <div className="text-center p-3 bg-muted rounded-lg">
                        <div className="text-2xl font-bold">{(yieldPrediction.confidence * 100).toFixed(0)}%</div>
                        <div className="text-xs text-muted-foreground mt-1">Confidence</div>
                      </div>
                    )}
                    {yieldPrediction.window_days !== undefined && (
                      <div className="text-center p-3 bg-muted rounded-lg col-span-2">
                        <div className="text-2xl font-bold">{yieldPrediction.window_days}</div>
                        <div className="text-xs text-muted-foreground mt-1">Days of Data</div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Recommendations */}
                <div className="border-t pt-4">
                  <p className="text-sm font-medium mb-2">Recommendations</p>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-0.5">•</span>
                      <span>Continue monitoring sensor readings daily for optimal crop management</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-0.5">•</span>
                      <span>Perform regular disease scans to catch issues early</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-0.5">•</span>
                      <span>Record actual yield at harvest to improve future predictions</span>
                    </li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Yield Prediction for {sensorId}</CardTitle>
                <CardDescription>AI-powered yield forecasting based on sensor data and crop health</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  No yield prediction available for this sensor. The model may need more historical data to generate
                  predictions.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
