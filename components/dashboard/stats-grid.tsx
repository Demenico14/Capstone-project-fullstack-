import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Database, Radio, Clock, Calendar } from "lucide-react"
import type { Statistics } from "@/lib/api"

interface StatsGridProps {
  stats: Statistics
}

export function StatsGrid({ stats }: StatsGridProps) {
  const statItems = [
    {
      title: "Total Readings",
      value: stats.total_readings.toLocaleString(),
      icon: Database,
      description: "Data points collected",
    },
    {
      title: "Active Sensors",
      value: stats.active_sensors.toString(),
      icon: Radio,
      description: "Sensors online",
    },
    {
      title: "Last Update",
      value: stats.last_update,
      icon: Clock,
      description: "Most recent data",
    },
    {
      title: "Data Range",
      value: stats.data_range,
      icon: Calendar,
      description: "Collection period",
    },
  ]

  return (
    <div className="grid gap-3 sm:gap-4 grid-cols-2 lg:grid-cols-4">
      {statItems.map((item) => {
        const Icon = item.icon
        return (
          <Card key={item.title}>
            <CardHeader className="flex flex-row items-center justify-between p-3 sm:p-4 pb-1 sm:pb-2">
              <CardTitle className="text-xs sm:text-sm font-medium text-muted-foreground">{item.title}</CardTitle>
              <Icon className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent className="p-3 sm:p-4 pt-0">
              <div className="text-lg sm:text-xl lg:text-2xl font-bold truncate">{item.value}</div>
              <p className="text-xs text-muted-foreground hidden sm:block">{item.description}</p>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
