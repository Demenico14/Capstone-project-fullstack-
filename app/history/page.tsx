import { Suspense } from "react"
import { HistoryTable } from "@/components/history/history-table"
import { LoadingSpinner } from "@/components/ui/loading-spinner"

export default function HistoryPage() {
  return (
    <div className="space-y-4 sm:space-y-6 lg:space-y-8">
      <div>
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-balance">Historical Data</h1>
        <p className="mt-1 sm:mt-2 text-sm sm:text-base text-muted-foreground">
          View and export historical sensor readings
        </p>
      </div>

      <Suspense fallback={<LoadingSpinner />}>
        <HistoryTable />
      </Suspense>
    </div>
  )
}
