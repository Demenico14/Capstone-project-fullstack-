"use client"
import DashboardOverview from "@/components/dashboard/dashboard-overview-client"

export default function HomePage() {
  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-balance">CropIoT Dashboard</h1>
        <p className="mt-1 sm:mt-2 text-sm sm:text-base text-muted-foreground">
          Real-time monitoring of your agricultural sensors
        </p>
      </div>

      <DashboardOverview />
    </div>
  )
}
