import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Droplets, Thermometer, Wind, Activity } from "lucide-react"
import type { SensorReading } from "@/lib/api"
import { cn } from "@/lib/utils"

interface SensorCardProps {
  reading: SensorReading
}

export function SensorCard({ reading }: SensorCardProps) {
  const getStatusColor = (value: number | null, min: number, max: number) => {
    if (value === null) return "text-muted-foreground"
    if (value >= min && value <= max) return "text-green-600"
    return "text-orange-600"
  }

  const formatValue = (value: number | null, unit: string) => {
    if (value === null) return "N/A"
    return `${value.toFixed(1)}${unit}`
  }

  return (
    <Link href={`/sensor/${reading.sensor_id}`}>
      <Card className="transition-all hover:shadow-lg hover:border-primary">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">{reading.sensor_id}</CardTitle>
            <Badge variant="outline" className="text-xs">
              <Activity className="mr-1 h-3 w-3" />
              {reading.rssi} dBm
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">{reading.timestamp}</p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center gap-2">
              <Droplets className={cn("h-5 w-5", getStatusColor(reading.soil_moisture, 40, 70))} />
              <div>
                <p className="text-xs text-muted-foreground">Soil</p>
                <p className="font-semibold">{formatValue(reading.soil_moisture, "%")}</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Thermometer className={cn("h-5 w-5", getStatusColor(reading.temperature, 18, 28))} />
              <div>
                <p className="text-xs text-muted-foreground">Temp</p>
                <p className="font-semibold">{formatValue(reading.temperature, "°C")}</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Wind className={cn("h-5 w-5", getStatusColor(reading.humidity, 50, 80))} />
              <div>
                <p className="text-xs text-muted-foreground">Humidity</p>
                <p className="font-semibold">{formatValue(reading.humidity, "%")}</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Signal</p>
                <p className="font-semibold">{reading.snr ? `${reading.snr.toFixed(1)} dB` : "N/A"}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
