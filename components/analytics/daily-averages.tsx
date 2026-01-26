import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { DailyAverage } from "@/lib/api"

interface DailyAveragesProps {
  data: { [sensorId: string]: DailyAverage[] }
}

export function DailyAverages({ data }: DailyAveragesProps) {
  return (
    <div>
      <h2 className="mb-4 text-2xl font-semibold">Daily Averages (Last 14 Days)</h2>
      <div className="grid gap-6">
        {Object.entries(data).map(([sensorId, averages]) => {
          // Convert object to array if needed
          const avgArray = Array.isArray(averages)
            ? averages
            : Object.entries(averages).map(([date, values]) => ({
                date,
                ...values,
              }))

          return (
            <Card key={sensorId}>
              <CardHeader>
                <CardTitle>{sensorId}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2 px-2">Date</th>
                        <th className="text-right py-2 px-2">Soil (%)</th>
                        <th className="text-right py-2 px-2">Temp (°C)</th>
                        <th className="text-right py-2 px-2">Humidity (%)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {avgArray.slice(-7).map((avg: any, idx: number) => (
                        <tr key={idx} className="border-b last:border-0">
                          <td className="py-2 px-2 text-muted-foreground">{avg.date}</td>
                          <td className="text-right py-2 px-2">
                            {avg.soil_moisture !== null ? avg.soil_moisture.toFixed(1) : "N/A"}
                          </td>
                          <td className="text-right py-2 px-2">
                            {avg.temperature !== null ? avg.temperature.toFixed(1) : "N/A"}
                          </td>
                          <td className="text-right py-2 px-2">
                            {avg.humidity !== null ? avg.humidity.toFixed(1) : "N/A"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
