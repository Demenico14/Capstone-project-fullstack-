"use client"

import { useState, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Droplets, Thermometer, Wind, Leaf, TrendingUp, AlertCircle, RefreshCw } from "lucide-react"
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  ComposedChart,
} from "recharts"
import "katex/dist/katex.min.css"
import { InlineMath, BlockMath } from "react-katex"

interface WaterBalanceData {
  waterBalance: Array<{
    date: string
    value: number
    et0: number
    etc: number
    precipitation: number
    runoff: number
    deltaS: number
    vpd: number
    vpdStress: number
    kc: number
    components: {
      p: number
      i: number
      et: number
      r: number
      ds: number
    }
  }>
  cropGrowth: Array<{
    date: string
    gdd: number
    accumulatedGdd: number
    lai: number
    kc: number
    growthStage: string
  }>
  vpdAnalysis: Array<{
    date: string
    vpd: number
    stressFactor: number
    category: string
    temperature: number
    humidity: number
  }>
  yieldStress: Array<{
    date: string
    vpdStress: number
    waterStress: number
    combinedStress: number
    yieldImpact: number
  }>
  ndvi: Array<{ date: string; value: number }>
  rainfall: Array<{ date: string; value: number }>
  et: Array<{ date: string; value: number }>
  kc: Array<{ date: string; value: number }>
  deltaS: Array<{ date: string; value: number }>
}

interface Summary {
  totalWaterBalance: number
  averageWaterBalance: number
  totalPrecipitation: number
  totalET: number
  averageVPD: number
  maxVPD: number
  waterDeficitDays: number
  waterExcessDays: number
  currentGrowthStage: string
  accumulatedGDD: number
  currentLAI: number
}

export default function WaterBalancePage() {
  const [data, setData] = useState<WaterBalanceData | null>(null)
  const [summary, setSummary] = useState<Summary | null>(null)
  const [recommendations, setRecommendations] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
    end: new Date().toISOString().split("T")[0],
  })
  const [viewMode, setViewMode] = useState<"water" | "growth" | "stress">("water")

  const farmCenter = {
    lat: Number.parseFloat(process.env.NEXT_PUBLIC_FARM_CENTER_LAT || "-18.30252535"),
    lng: Number.parseFloat(process.env.NEXT_PUBLIC_FARM_CENTER_LNG || "31.56415345"),
  }

  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000"

  useEffect(() => {
    fetchWaterBalanceData()
  }, [dateRange])

  const fetchWaterBalanceData = async () => {
    setLoading(true)
    setError(null)
    try {
      // Fetch from Python backend
      const response = await fetch(
        `${backendUrl}/api/water-balance?lat=${farmCenter.lat}&lng=${farmCenter.lng}&startDate=${dateRange.start}&endDate=${dateRange.end}`,
        { signal: AbortSignal.timeout(30000) },
      )

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`)
      }

      const result = await response.json()

      if (result.success) {
        setData(result.data)
        setSummary(result.summary)
        setRecommendations(result.recommendations || [])
      } else {
        throw new Error(result.error || "Failed to fetch water balance data")
      }
    } catch (err) {
      console.error("Error fetching water balance data:", err)
      setError(err instanceof Error ? err.message : "Failed to load water balance data")
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <Droplets className="mx-auto h-12 w-12 animate-pulse text-primary" />
          <p className="mt-4 text-lg">Loading water balance data from backend...</p>
          <p className="text-sm text-muted-foreground mt-2">Fetching satellite and sensor data</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center max-w-md">
          <AlertCircle className="mx-auto h-12 w-12 text-destructive" />
          <p className="mt-4 text-lg text-destructive">Failed to load water balance data</p>
          <p className="text-sm text-muted-foreground mt-2">{error}</p>
          <Button onClick={fetchWaterBalanceData} className="mt-4">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <p className="text-lg text-muted-foreground">No data available</p>
          <Button onClick={fetchWaterBalanceData} className="mt-4">
            Refresh
          </Button>
        </div>
      </div>
    )
  }

  const currentBalance = data.waterBalance[data.waterBalance.length - 1]?.value || 0
  const latestGrowth = data.cropGrowth[data.cropGrowth.length - 1]
  const latestVpd = data.vpdAnalysis[data.vpdAnalysis.length - 1]

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-balance flex items-center gap-2 sm:gap-3">
            <Droplets className="h-8 w-8 sm:h-10 sm:w-10 text-primary shrink-0" />
            <span>Physics-Informed Water Balance</span>
          </h1>
          <p className="mt-1 sm:mt-2 text-sm sm:text-base text-muted-foreground">
            FAO-56 water balance with VPD stress and crop growth modeling
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button
            size="sm"
            variant={viewMode === "water" ? "default" : "outline"}
            onClick={() => setViewMode("water")}
          >
            <Droplets className="h-4 w-4 mr-1.5" />
            Water
          </Button>
          <Button
            size="sm"
            variant={viewMode === "growth" ? "default" : "outline"}
            onClick={() => setViewMode("growth")}
          >
            <Leaf className="h-4 w-4 mr-1.5" />
            Growth
          </Button>
          <Button
            size="sm"
            variant={viewMode === "stress" ? "default" : "outline"}
            onClick={() => setViewMode("stress")}
          >
            <TrendingUp className="h-4 w-4 mr-1.5" />
            Stress
          </Button>
        </div>
      </div>

      {/* Recommendations Alert */}
      {recommendations.length > 0 && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <strong>Recommendations:</strong>
            <ul className="mt-2 list-disc list-inside space-y-1">
              {recommendations.map((rec, idx) => (
                <li key={idx} className="text-sm">
                  {rec}
                </li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* Summary Cards */}
      <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
        <Card className="p-4">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Droplets className="h-4 w-4" />
            <span className="text-xs sm:text-sm">Water Balance</span>
          </div>
          <div
            className={`text-2xl sm:text-3xl font-bold mt-2 ${currentBalance > 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}
          >
            {currentBalance > 0 ? "+" : ""}
            {currentBalance.toFixed(1)}mm
          </div>
          <p className="text-xs text-muted-foreground mt-1">{currentBalance > 0 ? "Surplus" : "Deficit"}</p>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Wind className="h-4 w-4" />
            <span className="text-xs sm:text-sm">VPD</span>
          </div>
          <div className="text-2xl sm:text-3xl font-bold mt-2">{latestVpd?.vpd?.toFixed(2) || "N/A"} kPa</div>
          <Badge variant={latestVpd?.category === "optimal" ? "default" : "destructive"} className="mt-1">
            {latestVpd?.category || "Unknown"}
          </Badge>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Leaf className="h-4 w-4" />
            <span className="text-xs sm:text-sm">Growth Stage</span>
          </div>
          <div className="text-lg sm:text-xl font-bold mt-2 truncate">{latestGrowth?.growthStage || "Unknown"}</div>
          <p className="text-xs text-muted-foreground mt-1">GDD: {latestGrowth?.accumulatedGdd?.toFixed(0) || 0}</p>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Thermometer className="h-4 w-4" />
            <span className="text-xs sm:text-sm">Crop Coefficient</span>
          </div>
          <div className="text-2xl sm:text-3xl font-bold mt-2">{latestGrowth?.kc?.toFixed(2) || "N/A"}</div>
          <p className="text-xs text-muted-foreground mt-1">LAI: {latestGrowth?.lai?.toFixed(2) || 0}</p>
        </Card>
      </div>

      {/* Physics Equations Card */}
      <Card className="p-4 sm:p-6">
        <h2 className="text-lg sm:text-xl font-semibold mb-4">Physics Equations</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="bg-muted/50 p-4 rounded-lg">
            <h3 className="font-medium mb-2">Water Balance (FAO-56)</h3>
            <div className="text-center text-lg">
              <BlockMath math="ET = P + I - R - \Delta S" />
            </div>
          </div>
          <div className="bg-muted/50 p-4 rounded-lg">
            <h3 className="font-medium mb-2">Vapor Pressure Deficit</h3>
            <div className="text-center text-lg">
              <BlockMath math="VPD = e_s - e_a = 0.6108 \cdot e^{\frac{17.27T}{T+237.3}} \cdot (1 - \frac{RH}{100})" />
            </div>
          </div>
          <div className="bg-muted/50 p-4 rounded-lg">
            <h3 className="font-medium mb-2">Growing Degree Days</h3>
            <div className="text-center text-lg">
              <BlockMath math="GDD = \max(0, \frac{T_{max} + T_{min}}{2} - T_{base})" />
            </div>
          </div>
          <div className="bg-muted/50 p-4 rounded-lg">
            <h3 className="font-medium mb-2">Crop Coefficient from NDVI</h3>
            <div className="text-center text-lg">
              <BlockMath math="K_c = 1.2 \cdot \frac{NDVI - NDVI_{min}}{NDVI_{max} - NDVI_{min}}" />
            </div>
          </div>
        </div>
      </Card>

      {/* Charts based on view mode */}
      {viewMode === "water" && (
        <div className="grid gap-4 sm:gap-6 md:grid-cols-2">
          {/* Water Balance Timeline */}
          <Card className="p-4 sm:p-6 md:col-span-2">
            <h3 className="text-base sm:text-lg font-semibold mb-4">Water Balance Timeline</h3>
            <div className="h-72 sm:h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data.waterBalance}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="components.p" fill="#3b82f6" name="Precipitation (mm)" />
                  <Bar dataKey="components.et" fill="#ef4444" name="ET (mm)" />
                  <Line type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} name="Balance (mm)" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* NDVI Trend */}
          <Card className="p-4 sm:p-6">
            <h3 className="text-base sm:text-lg font-semibold mb-4">NDVI Trend (Vegetation Health)</h3>
            <div className="h-64 sm:h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.ndvi}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} domain={[0, 1]} />
                  <Tooltip />
                  <Area type="monotone" dataKey="value" stroke="#22c55e" fill="#22c55e" fillOpacity={0.3} name="NDVI" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Soil Moisture Change */}
          <Card className="p-4 sm:p-6">
            <h3 className="text-base sm:text-lg font-semibold mb-4">
              Soil Moisture Change (<InlineMath math="\Delta S" />)
            </h3>
            <div className="h-64 sm:h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.deltaS}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#8b5cf6" name="ΔS (mm)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      )}

      {viewMode === "growth" && (
        <div className="grid gap-4 sm:gap-6 md:grid-cols-2">
          {/* Accumulated GDD */}
          <Card className="p-4 sm:p-6">
            <h3 className="text-base sm:text-lg font-semibold mb-4">Accumulated Growing Degree Days</h3>
            <div className="h-72 sm:h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.cropGrowth}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="accumulatedGdd"
                    stroke="#f59e0b"
                    fill="#f59e0b"
                    fillOpacity={0.3}
                    name="Accumulated GDD"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* LAI */}
          <Card className="p-4 sm:p-6">
            <h3 className="text-base sm:text-lg font-semibold mb-4">Leaf Area Index (LAI)</h3>
            <div className="h-72 sm:h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.cropGrowth}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} domain={[0, 6]} />
                  <Tooltip />
                  <Line type="monotone" dataKey="lai" stroke="#22c55e" strokeWidth={2} name="LAI" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Crop Coefficient */}
          <Card className="p-4 sm:p-6 md:col-span-2">
            <h3 className="text-base sm:text-lg font-semibold mb-4">
              Crop Coefficient (<InlineMath math="K_c" />)
            </h3>
            <div className="h-64 sm:h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.cropGrowth}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} domain={[0, 1.5]} />
                  <Tooltip />
                  <Line type="monotone" dataKey="kc" stroke="#3b82f6" strokeWidth={2} name="Kc" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      )}

      {viewMode === "stress" && (
        <div className="grid gap-4 sm:gap-6 md:grid-cols-2">
          {/* VPD Analysis */}
          <Card className="p-4 sm:p-6">
            <h3 className="text-base sm:text-lg font-semibold mb-4">VPD Analysis</h3>
            <div className="h-72 sm:h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data.vpdAnalysis}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis yAxisId="left" tick={{ fontSize: 12 }} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} domain={[0, 1]} />
                  <Tooltip />
                  <Legend />
                  <Bar yAxisId="left" dataKey="vpd" fill="#ef4444" name="VPD (kPa)" />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="stressFactor"
                    stroke="#22c55e"
                    strokeWidth={2}
                    name="Stress Factor"
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Yield Impact */}
          <Card className="p-4 sm:p-6">
            <h3 className="text-base sm:text-lg font-semibold mb-4">Yield Impact from Stress</h3>
            <div className="h-72 sm:h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.yieldStress}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} domain={[0, 50]} />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="yieldImpact"
                    stroke="#ef4444"
                    fill="#ef4444"
                    fillOpacity={0.3}
                    name="Yield Reduction (%)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Combined Stress Factors */}
          <Card className="p-4 sm:p-6 md:col-span-2">
            <h3 className="text-base sm:text-lg font-semibold mb-4">Stress Factor Breakdown</h3>
            <div className="h-64 sm:h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.yieldStress}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} domain={[0, 1]} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="vpdStress" stroke="#f59e0b" strokeWidth={2} name="VPD Stress" />
                  <Line type="monotone" dataKey="waterStress" stroke="#3b82f6" strokeWidth={2} name="Water Stress" />
                  <Line
                    type="monotone"
                    dataKey="combinedStress"
                    stroke="#22c55e"
                    strokeWidth={2}
                    name="Combined (1=No Stress)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      )}

      {/* Summary Statistics */}
      {summary && (
        <Card className="p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold mb-4">Summary Statistics</h3>
          <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
            <div>
              <p className="text-xs sm:text-sm text-muted-foreground">Total Water Balance</p>
              <p className="text-lg font-bold">{summary.totalWaterBalance?.toFixed(1) || 0} mm</p>
            </div>
            <div>
              <p className="text-xs sm:text-sm text-muted-foreground">Total Precipitation</p>
              <p className="text-lg font-bold">{summary.totalPrecipitation?.toFixed(1) || 0} mm</p>
            </div>
            <div>
              <p className="text-xs sm:text-sm text-muted-foreground">Total ET</p>
              <p className="text-lg font-bold">{summary.totalET?.toFixed(1) || 0} mm</p>
            </div>
            <div>
              <p className="text-xs sm:text-sm text-muted-foreground">Avg VPD</p>
              <p className="text-lg font-bold">{summary.averageVPD?.toFixed(2) || 0} kPa</p>
            </div>
            <div>
              <p className="text-xs sm:text-sm text-muted-foreground">Deficit Days</p>
              <p className="text-lg font-bold text-red-600">{summary.waterDeficitDays || 0}</p>
            </div>
            <div>
              <p className="text-xs sm:text-sm text-muted-foreground">Excess Days</p>
              <p className="text-lg font-bold text-blue-600">{summary.waterExcessDays || 0}</p>
            </div>
            <div>
              <p className="text-xs sm:text-sm text-muted-foreground">Accumulated GDD</p>
              <p className="text-lg font-bold">{summary.accumulatedGDD?.toFixed(0) || 0}</p>
            </div>
            <div>
              <p className="text-xs sm:text-sm text-muted-foreground">Current LAI</p>
              <p className="text-lg font-bold">{summary.currentLAI?.toFixed(2) || 0}</p>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
