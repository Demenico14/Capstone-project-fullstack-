import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { SensorReading } from "@/lib/api"

interface RecentReadingsProps {
  readings: SensorReading[]
}

export function RecentReadings({ readings }: RecentReadingsProps) {
  const formatValue = (value: number | null) => {
    if (value === null) return "N/A"
    return value.toFixed(1)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Latest Readings</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Sensor ID</TableHead>
              <TableHead>Timestamp</TableHead>
              <TableHead className="text-right">Soil (%)</TableHead>
              <TableHead className="text-right">Temp (°C)</TableHead>
              <TableHead className="text-right">Humidity (%)</TableHead>
              <TableHead className="text-right">RSSI (dBm)</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {readings.map((reading) => (
              <TableRow key={reading.sensor_id}>
                <TableCell className="font-medium">{reading.sensor_id}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{reading.timestamp}</TableCell>
                <TableCell className="text-right">{formatValue(reading.soil_moisture)}</TableCell>
                <TableCell className="text-right">{formatValue(reading.temperature)}</TableCell>
                <TableCell className="text-right">{formatValue(reading.humidity)}</TableCell>
                <TableCell className="text-right">{reading.rssi}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
