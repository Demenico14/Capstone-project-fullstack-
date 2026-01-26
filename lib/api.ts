const PRIMARY_IP = "192.168.4.3"
const FALLBACK_IP = "192.168.1.230"

const SENSOR_API_URL = process.env.NEXT_PUBLIC_API_URL || `http://${PRIMARY_IP}:5000`
const DISEASE_API_URL = process.env.NEXT_PUBLIC_DISEASE_API_URL || `http://${PRIMARY_IP}:8000`
const YIELD_API_URL = process.env.NEXT_PUBLIC_YIELD_API_URL || `http://${PRIMARY_IP}:9000`

export interface SensorReading {
  timestamp: string
  sensor_id: string
  soil_moisture: number | null
  ph: number | null
  temperature: number | null
  humidity: number | null
  rssi: number
  snr: number
}

export interface Statistics {
  total_readings: number
  active_sensors: number
  last_update: string
  data_range: string
}

export interface ChartData {
  [sensorId: string]: {
    timestamps: string[]
    soil_moisture: (number | null)[]
    ph: (number | null)[]
    temperature: (number | null)[]
    humidity: (number | null)[]
  }
}

export interface DailyAverage {
  date: string
  soil_moisture: number
  ph: number
  temperature: number
  humidity: number
  readings_count: number
}

export interface TrendSummary {
  [sensorId: string]: {
    soil_moisture: { trend: string; change: number }
    ph: { trend: string; change: number }
    temperature: { trend: string; change: number }
    humidity: { trend: string; change: number }
  }
}

export interface YieldEstimate {
  sensor_id: string
  score: number
  grade: string
  factors: string[]
  recommendations: string[]
}

export interface DiseaseDetection {
  id: string
  timestamp: string
  sensor_id: string
  disease_type: string
  confidence: number
  num_detections: number
  image_filename: string
  detections: Array<{
    class: string
    confidence: number
    bbox: number[]
  }>
}

export interface DiseaseStats {
  total_detections: number
  healthy_count: number
  diseased_count: number
  disease_distribution: Array<{
    disease_type: string
    count: number
    avg_confidence: number
  }>
  recent_detections_7days: number
  last_detection: string
}

export interface DiseaseTrend {
  date: string
  disease_type: string
  count: number
}

export interface SensorDetail {
  sensor_id: string
  total_readings: number
  latest_reading: SensorReading | null
  avg_temperature: number | null
  avg_humidity: number | null
  avg_soil_moisture: number | null
  readings: SensorReading[]
}

export interface YieldPrediction {
  sensor_id: string
  predicted_yield: number
  uncertainty: number
  confidence_interval: [number, number]
  timestamp: string
  prediction_date?: string
  confidence?: number
  data_points_used?: number
  window_days?: number
  window_start?: string
  window_end?: string
  features_used: {
    sensor_readings: number
    disease_detections: number
    temporal_window_days: number
  }
}

export interface YieldPredictionResponse {
  predictions: YieldPrediction[]
  model_info: {
    model_type: string
    trained_on: string
    performance_metrics: {
      mae: number
      rmse: number
      r2: number
    }
  }
  timestamp: string
}

export interface YieldModelInfo {
  model_loaded: boolean
  model_path: string
  model_type: string
  input_features: number
  output_features: number
  trained_on: string | null
  performance_metrics: {
    mae: number | null
    rmse: number | null
    r2: number | null
  }
}

class ApiClient {
  private sensorApiUrl: string
  private diseaseApiUrl: string
  private yieldApiUrl: string

  constructor(
    sensorApiUrl: string = SENSOR_API_URL,
    diseaseApiUrl: string = DISEASE_API_URL,
    yieldApiUrl: string = YIELD_API_URL,
  ) {
    this.sensorApiUrl = sensorApiUrl
    this.diseaseApiUrl = diseaseApiUrl
    this.yieldApiUrl = yieldApiUrl
  }

  private async fetchWithFallback<T>(
    endpoint: string,
    apiType: "sensor" | "disease" | "yield" = "sensor",
    options: RequestInit = {},
  ): Promise<T> {
    const port = apiType === "disease" ? "8000" : apiType === "yield" ? "9000" : "5000"
    const primaryUrl =
      apiType === "disease" ? this.diseaseApiUrl : apiType === "yield" ? this.yieldApiUrl : this.sensorApiUrl
    const fallbackUrl = `http://${FALLBACK_IP}:${port}`

    // Try primary URL first
    try {
      console.log(`[v0] Trying primary URL: ${primaryUrl}${endpoint}`)
      const response = await fetch(`${primaryUrl}${endpoint}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
        cache: "no-store",
        signal: AbortSignal.timeout(5000), // 5 second timeout
      })

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`)
      }

      console.log(`[v0] Primary URL succeeded`)
      return response.json()
    } catch (primaryError) {
      console.log(`[v0] Primary URL failed, trying fallback: ${fallbackUrl}${endpoint}`)

      // Try fallback URL
      try {
        const response = await fetch(`${fallbackUrl}${endpoint}`, {
          ...options,
          headers: {
            "Content-Type": "application/json",
            ...options.headers,
          },
          cache: "no-store",
          signal: AbortSignal.timeout(5000),
        })

        if (!response.ok) {
          throw new Error(`API error: ${response.statusText}`)
        }

        console.log(`[v0] Fallback URL succeeded`)
        return response.json()
      } catch (fallbackError) {
        console.error(`[v0] Both URLs failed. Primary:`, primaryError, `Fallback:`, fallbackError)
        throw new Error(`Failed to connect to both ${primaryUrl} and ${fallbackUrl}`)
      }
    }
  }

  private async fetch<T>(endpoint: string, apiType: "sensor" | "disease" | "yield" = "sensor"): Promise<T> {
    return this.fetchWithFallback<T>(endpoint, apiType)
  }

  private async post<T>(
    endpoint: string,
    body: FormData,
    apiType: "sensor" | "disease" | "yield" = "sensor",
  ): Promise<T> {
    const port = apiType === "disease" ? "8000" : apiType === "yield" ? "9000" : "5000"
    const primaryUrl =
      apiType === "disease" ? this.diseaseApiUrl : apiType === "yield" ? this.yieldApiUrl : this.sensorApiUrl
    const fallbackUrl = `http://${FALLBACK_IP}:${port}`

    // Try primary URL first
    try {
      console.log(`[v0] POST to primary URL: ${primaryUrl}${endpoint}`)
      const response = await fetch(`${primaryUrl}${endpoint}`, {
        method: "POST",
        body,
        cache: "no-store",
        signal: AbortSignal.timeout(10000), // 10 second timeout for uploads
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.message || `API error: ${response.statusText}`)
      }

      console.log(`[v0] Primary POST succeeded`)
      return response.json()
    } catch (primaryError) {
      console.log(`[v0] Primary POST failed, trying fallback: ${fallbackUrl}${endpoint}`)

      // Try fallback URL
      try {
        const response = await fetch(`${fallbackUrl}${endpoint}`, {
          method: "POST",
          body,
          cache: "no-store",
          signal: AbortSignal.timeout(10000),
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.message || `API error: ${response.statusText}`)
        }

        console.log(`[v0] Fallback POST succeeded`)
        return response.json()
      } catch (fallbackError) {
        console.error(`[v0] Both POST URLs failed. Primary:`, primaryError, `Fallback:`, fallbackError)
        throw new Error(`Failed to connect to both ${primaryUrl} and ${fallbackUrl}`)
      }
    }
  }

  private async postJson<T>(
    endpoint: string,
    body: any,
    apiType: "sensor" | "disease" | "yield" = "sensor",
  ): Promise<T> {
    const port = apiType === "disease" ? "8000" : apiType === "yield" ? "9000" : "5000"
    const primaryUrl =
      apiType === "disease" ? this.diseaseApiUrl : apiType === "yield" ? this.yieldApiUrl : this.sensorApiUrl
    const fallbackUrl = `http://${FALLBACK_IP}:${port}`

    // Try primary URL first
    try {
      console.log(`[v0] POST JSON to primary URL: ${primaryUrl}${endpoint}`)
      const response = await fetch(`${primaryUrl}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || `API error: ${response.statusText}`)
      }

      console.log(`[v0] Primary POST JSON succeeded`)
      return response.json()
    } catch (primaryError) {
      console.log(`[v0] Primary POST JSON failed, trying fallback: ${fallbackUrl}${endpoint}`)

      // Try fallback URL
      try {
        const response = await fetch(`${fallbackUrl}${endpoint}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(body),
          cache: "no-store",
          signal: AbortSignal.timeout(10000),
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.error || `API error: ${response.statusText}`)
        }

        console.log(`[v0] Fallback POST JSON succeeded`)
        return response.json()
      } catch (fallbackError) {
        console.error(`[v0] Both POST JSON URLs failed. Primary:`, primaryError, `Fallback:`, fallbackError)
        throw new Error(`Failed to connect to both ${primaryUrl} and ${fallbackUrl}`)
      }
    }
  }

  // Sensor API endpoints (port 5000)
  async getLatestReadings(): Promise<SensorReading[]> {
    return this.fetch<SensorReading[]>("/api/latest", "sensor")
  }

  async getStatistics(): Promise<Statistics> {
    return this.fetch<Statistics>("/api/stats", "sensor")
  }

  async getChartData(hours = 24): Promise<ChartData> {
    return this.fetch<ChartData>(`/api/chart-data?hours=${hours}`, "sensor")
  }

  async getDailyAverages(days = 14): Promise<{ [sensorId: string]: DailyAverage[] }> {
    return this.fetch(`/api/analytics/daily-averages?days=${days}`, "sensor")
  }

  async getTrends(): Promise<TrendSummary> {
    return this.fetch<TrendSummary>("/api/analytics/trends", "sensor")
  }

  async getYieldEstimates(): Promise<YieldEstimate[]> {
    return this.fetch<YieldEstimate[]>("/api/analytics/yield-estimates", "sensor")
  }

  async getSensorStats(): Promise<any> {
    return this.fetch("/api/analytics/sensor-stats", "sensor")
  }

  async getSensorData(sensorId: string, hours = 24, limit = 100): Promise<SensorDetail> {
    return this.fetch<SensorDetail>(`/api/sensor/${sensorId}?hours=${hours}&limit=${limit}`, "sensor")
  }

  async detectDisease(file: File, sensorId?: string): Promise<any> {
    const formData = new FormData()
    formData.append("image", file)
    if (sensorId) {
      formData.append("sensor_id", sensorId)
    }
    return this.post("/api/detect", formData, "disease")
  }

  async getDiseaseHistory(params?: {
    limit?: number
    sensor_id?: string
    disease_type?: string
    days?: number
  }): Promise<DiseaseDetection[]> {
    const queryParams = new URLSearchParams()
    if (params?.limit) queryParams.append("limit", params.limit.toString())
    if (params?.sensor_id) queryParams.append("sensor_id", params.sensor_id)
    if (params?.disease_type) queryParams.append("disease_type", params.disease_type)
    if (params?.days) queryParams.append("days", params.days.toString())

    const query = queryParams.toString()
    return this.fetch<DiseaseDetection[]>(`/api/disease-history${query ? `?${query}` : ""}`, "sensor")
  }

  async getDiseaseStats(sensorId?: string): Promise<DiseaseStats> {
    const query = sensorId ? `?sensor_id=${sensorId}` : ""
    return this.fetch<DiseaseStats>(`/api/disease-stats${query}`, "sensor")
  }

  async getDiseaseTrends(days = 30, sensorId?: string): Promise<DiseaseTrend[]> {
    const params = new URLSearchParams()
    params.append("days", days.toString())
    if (sensorId) params.append("sensor_id", sensorId)
    return this.fetch<DiseaseTrend[]>(`/api/disease-trends?${params.toString()}`, "sensor")
  }

  async healthCheck(): Promise<{ status: string; model_loaded: boolean; model_path: string }> {
    return this.fetch("/health", "disease")
  }

  async detectDiseaseFromFile(file: File): Promise<{
    success: boolean
    prediction: { class: string; confidence: number }
    all_predictions: Array<{ class: string; confidence: number }>
    filename: string
  }> {
    const formData = new FormData()
    formData.append("image", file)
    return this.post("/api/detect", formData, "disease")
  }

  async detectDiseaseFromBase64(base64Image: string): Promise<{
    success: boolean
    prediction: { class: string; confidence: number }
    all_predictions: Array<{ class: string; confidence: number }>
  }> {
    return this.postJson("/api/detect/base64", { image: base64Image }, "disease")
  }

  async getModelInfo(): Promise<{
    model_path: string
    classes: { [key: number]: string }
    num_classes: number
  }> {
    return this.fetch("/api/model/info", "disease")
  }

  // Yield Prediction API methods (port 9000)
  async getYieldPredictions(sensorIds?: string[], days?: number): Promise<YieldPredictionResponse> {
    const params = new URLSearchParams()
    if (sensorIds && sensorIds.length > 0) {
      params.append("sensor_ids", sensorIds.join(","))
    }
    if (days) {
      params.append("days", days.toString())
    }
    const query = params.toString()
    return this.fetch<YieldPredictionResponse>(`/api/yield/predict-all${query ? `?${query}` : ""}`, "yield")
  }

  async getYieldModelInfo(): Promise<YieldModelInfo> {
    return this.fetch<YieldModelInfo>("/api/yield/model-info", "yield")
  }

  async yieldHealthCheck(): Promise<{ status: string; model_loaded: boolean }> {
    return this.fetch<{ status: string; model_loaded: boolean }>("/health", "yield")
  }
}

export const api = new ApiClient()
