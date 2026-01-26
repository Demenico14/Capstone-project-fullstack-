"use client"

import { useState, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Droplets } from "lucide-react"
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
} from "recharts"
import "katex/dist/katex.min.css"
import { InlineMath, BlockMath } from "react-katex"

export default function WaterBalancePage() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
    end: new Date().toISOString().split("T")[0],
  })
  const [viewMode, setViewMode] = useState<"daily" | "weekly" | "seasonal">("daily")

  const farmCenter = {
    lat: Number.parseFloat(process.env.NEXT_PUBLIC_FARM_CENTER_LAT || "-18.30252535"),
    lng: Number.parseFloat(process.env.NEXT_PUBLIC_FARM_CENTER_LNG || "31.56415345"),
  }

  useEffect(() => {
    fetchWaterBalanceData()
  }, [dateRange])

  const fetchWaterBalanceData = async () => {
    setLoading(true)
    try {
      const response = await fetch(
        `/api/water-balance?lat=${farmCenter.lat}&lng=${farmCenter.lng}&startDate=${dateRange.start}&endDate=${dateRange.end}`,
      )
      const result = await response.json()

      if (result.success) {
        setData(result.data)
      } else {
        console.error("Failed to fetch water balance data:", result.error)
      }
    } catch (error) {
      console.error("Error fetching water balance data:", error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <Droplets className="mx-auto h-12 w-12 animate-pulse text-blue-500" />
          <p className="mt-4 text-lg">Loading water balance data...</p>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <p className="text-lg text-red-500">Failed to load water balance data</p>
          <Button onClick={fetchWaterBalanceData} className="mt-4">
            Retry
          </Button>
        </div>
      </div>
    )
  }

  const currentBalance = data.waterBalance[data.waterBalance.length - 1]?.value || 0

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-balance flex items-center gap-2 sm:gap-3">
            <Droplets className="h-8 w-8 sm:h-10 sm:w-10 text-blue-500 shrink-0" />
            <span>Water Balance</span>
          </h1>
          <p className="mt-1 sm:mt-2 text-sm sm:text-base text-muted-foreground">
            Physics-informed water balance computation
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant={viewMode === "daily" ? "default" : "outline"}
            onClick={() => setViewMode("daily")}
            className="flex-1 sm:flex-none"
          >
            Daily
          </Button>
          <Button
            size="sm"
            variant={viewMode === "weekly" ? "default" : "outline"}
            onClick={() => setViewMode("weekly")}
            className="flex-1 sm:flex-none"
          >
            Weekly
          </Button>
          <Button
            size="sm"
            variant={viewMode === "seasonal" ? "default" : "outline"}
            onClick={() => setViewMode("seasonal")}
            className="flex-1 sm:flex-none"
          >
            Seasonal
          </Button>
        </div>
      </div>

      {/* Water Balance Equation */}
      <Card className="p-4 sm:p-6">
        <h2 className="text-lg sm:text-xl font-semibold mb-4">Water Balance Equation</h2>
        <div className="bg-blue-50 dark:bg-blue-950 p-4 sm:p-6 rounded-lg overflow-x-auto">
          <div className="text-center text-xl sm:text-2xl">
            <BlockMath math="ET = P + I - R - \Delta S" />
          </div>
          <div className="mt-4 sm:mt-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 sm:gap-4 text-sm">
            <TooltipCard
              symbol="ET"
              title="Evapotranspiration"
              description="Water lost through evaporation"
              formula="K_c \times ET_o"
            />
            <TooltipCard symbol="P" title="Precipitation" description="Daily rainfall from CHIRPS" formula="CHIRPS" />
            <TooltipCard symbol="I" title="Irrigation" description="Irrigation input from sensors" formula="IoT" />
            <TooltipCard symbol="R" title="Runoff" description="Surface runoff estimate" formula="FAO CN" />
            <TooltipCard
              symbol="\Delta S"
              title="Soil Moisture"
              description="Change in soil-water storage"
              formula="S_{t} - S_{t-1}"
              className="col-span-2 sm:col-span-1"
            />
          </div>
        </div>
      </Card>

      {/* Current Water Balance */}
      <Card className="p-4 sm:p-6">
        <h2 className="text-lg sm:text-xl font-semibold mb-4">Current Water Balance</h2>
        <div className="flex items-center justify-center py-4">
          <div className="text-center">
            <div
              className={`text-4xl sm:text-5xl lg:text-6xl font-bold ${currentBalance > 0 ? "text-green-500" : "text-red-500"}`}
            >
              {currentBalance > 0 ? "+" : ""}
              {currentBalance.toFixed(2)} mm
            </div>
            <p className="mt-2 text-sm sm:text-base text-muted-foreground">
              {currentBalance > 0 ? "Water surplus" : "Water deficit"}
            </p>
          </div>
        </div>
      </Card>

      {/* Charts */}
      <div className="grid gap-4 sm:gap-6 md:grid-cols-2">
        {/* NDVI Trend */}
        <Card className="p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold mb-4">NDVI Trend (Vegetation Health)</h3>
          <div className="h-64 sm:h-72 lg:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.ndvi}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="value" stroke="#22c55e" name="NDVI" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* ET vs Rainfall */}
        <Card className="p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold mb-4">ET vs Rainfall</h3>
          <div className="h-64 sm:h-72 lg:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.waterBalance}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="components.et" fill="#ef4444" name="ET (mm)" />
                <Bar dataKey="components.p" fill="#3b82f6" name="Rainfall (mm)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Kc (Crop Coefficient) */}
        <Card className="p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold mb-4">Crop Coefficient (Kc)</h3>
          <div className="mb-2 text-xs sm:text-sm text-muted-foreground overflow-x-auto">
            <InlineMath math="K_c = \frac{NDVI - NDVI_{min}}{NDVI_{max} - NDVI_{min}}" />
          </div>
          <div className="h-64 sm:h-72 lg:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.kc}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="value" stroke="#f59e0b" name="Kc" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Soil Moisture Change */}
        <Card className="p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold mb-4">Soil Moisture Change (ΔS)</h3>
          <div className="h-64 sm:h-72 lg:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.deltaS}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="value" fill="#8b5cf6" name="ΔS (mm)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Water Balance Timeline */}
      <Card className="p-4 sm:p-6">
        <h3 className="text-base sm:text-lg font-semibold mb-4">Water Balance Timeline</h3>
        <div className="h-72 sm:h-80 lg:h-96">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.waterBalance}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="value" stroke="#06b6d4" name="Water Balance (mm)" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  )
}

function TooltipCard({ symbol, title, description, formula, className }: any) {
  return (
    <div
      className={`bg-white dark:bg-gray-800 p-3 sm:p-4 rounded-lg border border-gray-200 dark:border-gray-700 ${className || ""}`}
    >
      <div className="text-xl sm:text-2xl font-bold text-blue-600 mb-1 sm:mb-2">
        <InlineMath math={symbol} />
      </div>
      <div className="font-semibold text-xs sm:text-sm mb-1">{title}</div>
      <div className="text-xs text-muted-foreground mb-1 sm:mb-2 line-clamp-2">{description}</div>
      <div className="text-xs font-mono bg-gray-100 dark:bg-gray-900 p-1 rounded overflow-x-auto">
        <InlineMath math={formula} />
      </div>
    </div>
  )
}
