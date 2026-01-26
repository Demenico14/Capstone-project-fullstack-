"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { api, type YieldPrediction, type YieldModelInfo, type SensorReading, type DiseaseStats } from "@/lib/api"
import { AlertCircle, CheckCircle2, Sprout, Activity, Database } from "lucide-react"
import { FarmMap } from "@/components/dashboard/farm-map"
import { YieldDataForm } from "@/components/yield/yield-data-form"
import { YieldHistoryTable } from "@/components/yield/yield-history-table"
import { TrainingPanel } from "@/components/yield/training-panel"

export default function YieldPredictionPage() {
  const [predictions, setPredictions] = useState<YieldPrediction[]>([])
  const [modelInfo, setModelInfo] = useState<YieldModelInfo | null>(null)
  const [latestReadings, setLatestReadings] = useState<SensorReading[]>([])
  const [diseaseStats, setDiseaseStats] = useState<DiseaseStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [modelStatus, setModelStatus] = useState<"loading" | "ready" | "error">("loading")
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)

      const health = await api.yieldHealthCheck()

      if (!health.model_loaded) {
        setModelStatus("error")
        setError("Yield prediction model is not loaded. Please train the model first.")
        const readings = await api.getLatestReadings()
        setLatestReadings(readings)
        return
      }
      setModelStatus("ready")

      const [predData, modelData, readings, disease] = await Promise.all([
        api.getYieldPredictions(),
        api.getYieldModelInfo(),
        api.getLatestReadings(),
        api.getDiseaseStats(),
      ])

      const predictions = Array.isArray(predData) ? predData : predData?.predictions || []

      setPredictions(predictions)
      setModelInfo(modelData)
      setLatestReadings(readings)
      setDiseaseStats(disease)
    } catch (err) {
      console.error("Error loading yield predictions:", err)
      setError(err instanceof Error ? err.message : "Failed to load yield predictions")
      setModelStatus("error")
      setPredictions([])
    } finally {
      setLoading(false)
    }
  }

  const getYieldGrade = (yieldValue: number): { grade: string; color: string } => {
    if (yieldValue >= 80) return { grade: "Excellent", color: "bg-green-500" }
    if (yieldValue >= 60) return { grade: "Good", color: "bg-blue-500" }
    if (yieldValue >= 40) return { grade: "Fair", color: "bg-yellow-500" }
    return { grade: "Poor", color: "bg-red-500" }
  }

  const handleYieldDataSuccess = () => {
    setRefreshTrigger((prev) => prev + 1)
  }

  if (loading) {
    return (
      <div className="space-y-4 sm:space-y-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold">Yield Prediction</h1>
          <p className="text-sm sm:text-base text-muted-foreground">AI-powered crop yield forecasting</p>
        </div>
        <Skeleton className="h-64 sm:h-80 lg:h-96" />
        <div className="grid gap-4 sm:gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-48 sm:h-64" />
          ))}
        </div>
      </div>
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

  const sensorIds = latestReadings.map((r) => r.sensor_id)

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold">Yield Prediction</h1>
        <p className="text-sm sm:text-base text-muted-foreground">AI-powered crop yield forecasting using ST-GNN</p>
      </div>

      <Tabs defaultValue="predictions" className="space-y-4 sm:space-y-6">
        <TabsList className="w-full sm:w-auto">
          <TabsTrigger value="predictions" className="flex-1 sm:flex-none">
            <Sprout className="h-4 w-4 mr-1.5 sm:mr-2" />
            <span className="text-xs sm:text-sm">Predictions</span>
          </TabsTrigger>
          <TabsTrigger value="data" className="flex-1 sm:flex-none">
            <Database className="h-4 w-4 mr-1.5 sm:mr-2" />
            <span className="text-xs sm:text-sm">Training Data</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="predictions" className="space-y-4 sm:space-y-6">
          {latestReadings.length > 0 && <FarmMap readings={latestReadings} diseaseAlerts={diseaseAlerts} />}

          {/* Model Status */}
          {modelInfo && (
            <Card>
              <CardHeader className="p-4 sm:p-6">
                <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
                  <Activity className="h-4 w-4 sm:h-5 sm:w-5" />
                  Model Status
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 sm:p-6 pt-0 sm:pt-0">
                <div className="grid gap-3 sm:gap-4 grid-cols-2 md:grid-cols-4">
                  <div>
                    <p className="text-xs sm:text-sm text-muted-foreground">Status</p>
                    <div className="flex items-center gap-1.5 sm:gap-2 mt-1">
                      <CheckCircle2 className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-green-500" />
                      <span className="font-semibold text-sm sm:text-base">Ready</span>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs sm:text-sm text-muted-foreground">Model Type</p>
                    <p className="font-semibold mt-1 text-sm sm:text-base">{modelInfo.model_type}</p>
                  </div>
                  {modelInfo.performance_metrics?.mae && (
                    <>
                      <div>
                        <p className="text-xs sm:text-sm text-muted-foreground">MAE</p>
                        <p className="font-semibold mt-1 text-sm sm:text-base">
                          {modelInfo.performance_metrics.mae.toFixed(2)}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs sm:text-sm text-muted-foreground">R² Score</p>
                        <p className="font-semibold mt-1 text-sm sm:text-base">
                          {modelInfo.performance_metrics.r2?.toFixed(3)}
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Error State */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-sm">{error}</AlertDescription>
            </Alert>
          )}

          {/* Predictions Grid */}
          {!predictions || predictions.length === 0 ? (
            <Card>
              <CardHeader className="p-4 sm:p-6">
                <CardTitle className="text-base sm:text-lg">No Predictions Available</CardTitle>
                <CardDescription className="text-sm">
                  {modelStatus === "error"
                    ? "Train the model with historical data to start making predictions"
                    : "No sensor data available for yield prediction"}
                </CardDescription>
              </CardHeader>
              <CardContent className="p-4 sm:p-6 pt-0 sm:pt-0">
                <p className="text-xs sm:text-sm text-muted-foreground">
                  {modelStatus === "error"
                    ? "Add harvest data in the Training Data tab, then train the model using the backend scripts."
                    : "Make sure your sensors are collecting data and the system has enough historical data to make predictions."}
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 sm:gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {predictions.map((prediction) => {
                if (!prediction || !prediction.predicted_yield) {
                  return null
                }

                const { grade, color } = getYieldGrade(prediction.predicted_yield)
                const uncertainty = prediction.uncertainty || 0
                const isHighUncertainty = uncertainty > 15
                const confidence = prediction.confidence || 0
                const confidenceInterval = prediction.confidence_interval || [
                  prediction.predicted_yield * 0.9,
                  prediction.predicted_yield * 1.1,
                ]

                return (
                  <Card key={prediction.sensor_id}>
                    <CardHeader className="p-4 sm:p-6">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-base sm:text-lg">Sensor {prediction.sensor_id}</CardTitle>
                        <Badge className={color}>{grade}</Badge>
                      </div>
                      <CardDescription className="text-xs sm:text-sm">
                        {prediction.prediction_date
                          ? new Date(prediction.prediction_date).toLocaleDateString()
                          : "Recent"}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="p-4 sm:p-6 pt-0 sm:pt-0 space-y-3 sm:space-y-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1 sm:mb-2">
                          <Sprout className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-muted-foreground" />
                          <span className="text-xs sm:text-sm text-muted-foreground">Predicted Yield</span>
                        </div>
                        <div className="flex items-baseline gap-1 sm:gap-2">
                          <span className="text-2xl sm:text-3xl font-bold">
                            {prediction.predicted_yield.toFixed(1)}
                          </span>
                          <span className="text-xs sm:text-sm text-muted-foreground">kg/hectare</span>
                        </div>
                      </div>

                      <div>
                        <p className="text-xs sm:text-sm text-muted-foreground mb-1 sm:mb-2">
                          Confidence Interval (95%)
                        </p>
                        <div className="flex items-center gap-1 sm:gap-2">
                          <span className="text-xs sm:text-sm font-medium">{confidenceInterval[0].toFixed(1)}</span>
                          <div className="flex-1 h-1.5 sm:h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary"
                              style={{
                                width: `${((prediction.predicted_yield - confidenceInterval[0]) / (confidenceInterval[1] - confidenceInterval[0])) * 100}%`,
                              }}
                            />
                          </div>
                          <span className="text-xs sm:text-sm font-medium">{confidenceInterval[1].toFixed(1)}</span>
                        </div>
                      </div>

                      {isHighUncertainty && (
                        <Alert>
                          <AlertCircle className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                          <AlertDescription className="text-xs">
                            High uncertainty ({uncertainty.toFixed(1)}%). More data needed.
                          </AlertDescription>
                        </Alert>
                      )}

                      {prediction.data_points_used && (
                        <div className="pt-2 sm:pt-4 border-t space-y-1 sm:space-y-2">
                          <p className="text-xs text-muted-foreground">Data Used</p>
                          <div className="grid grid-cols-2 gap-1 sm:gap-2 text-xs">
                            <div>
                              <span className="text-muted-foreground">Data points:</span>
                              <span className="ml-1 font-medium">{prediction.data_points_used}</span>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Confidence:</span>
                              <span className="ml-1 font-medium">{(confidence * 100).toFixed(0)}%</span>
                            </div>
                            {prediction.window_days && (
                              <div className="col-span-2">
                                <span className="text-muted-foreground">Time window:</span>
                                <span className="ml-1 font-medium">{prediction.window_days} days</span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </TabsContent>

        <TabsContent value="data" className="space-y-4 sm:space-y-6">
          <TrainingPanel />
          <YieldDataForm sensors={sensorIds} onSuccess={handleYieldDataSuccess} />
          <YieldHistoryTable refreshTrigger={refreshTrigger} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
