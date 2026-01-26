"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
} from "recharts"
import type { DailyAverage } from "@/lib/api"

interface TrendChartsProps {
  dailyAverages: { [sensorId: string]: DailyAverage[] }
}

export function TrendCharts({ dailyAverages }: TrendChartsProps) {
  console.log("[v0] TrendCharts received dailyAverages:", dailyAverages)

  // Combine all sensor data for correlation analysis
  const allData = Object.values(dailyAverages).flat()

  console.log("[v0] Combined allData:", allData)

  if (!dailyAverages || Object.keys(dailyAverages).length === 0 || allData.length === 0) {
    return (
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Soil Moisture Trends</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-center h-[300px] text-muted-foreground">
              No trend data available yet. Sensor data will appear here once collected.
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Temperature & Humidity Trends</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-center h-[300px] text-muted-foreground">
              No trend data available yet. Sensor data will appear here once collected.
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Moisture vs Temperature Correlation</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-center h-[300px] text-muted-foreground">
              No trend data available yet. Sensor data will appear here once collected.
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Prepare data for moisture vs yield correlation
  const correlationData = allData.map((day) => ({
    moisture: day.soil_moisture,
    temperature: day.temperature,
    humidity: day.humidity,
    date: day.date,
  }))

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Soil Moisture Trends</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={allData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="soil_moisture" stroke="#3b82f6" name="Moisture %" />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Temperature & Humidity Trends</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={allData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="temperature" stroke="#ef4444" name="Temp °C" />
              <Line type="monotone" dataKey="humidity" stroke="#10b981" name="Humidity %" />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Moisture vs Temperature Correlation</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="moisture" name="Soil Moisture %" />
              <YAxis dataKey="temperature" name="Temperature °C" />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} />
              <Legend />
              <Scatter name="Readings" data={correlationData} fill="#8b5cf6" />
            </ScatterChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
