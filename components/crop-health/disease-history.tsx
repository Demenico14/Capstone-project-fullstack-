"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Clock, AlertCircle, CheckCircle2, ChevronLeft, ChevronRight } from "lucide-react"
import { api, type DiseaseDetection } from "@/lib/api"

interface DiseaseHistoryProps {
  sensorId?: string
  refreshTrigger?: number
}

export function DiseaseHistory({ sensorId, refreshTrigger }: DiseaseHistoryProps) {
  const [history, setHistory] = useState<DiseaseDetection[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const itemsPerPage = 10

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true)
      try {
        const data = await api.getDiseaseHistory({
          limit: 100, // Fetch more for pagination
          sensor_id: sensorId,
        })

        // Calculate pagination
        const total = Math.ceil(data.length / itemsPerPage)
        setTotalPages(total)

        // Get current page data
        const startIdx = (page - 1) * itemsPerPage
        const endIdx = startIdx + itemsPerPage
        setHistory(data.slice(startIdx, endIdx))
      } catch (error) {
        console.error("Failed to fetch disease history:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchHistory()
  }, [sensorId, page, refreshTrigger])

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Detections</CardTitle>
          {sensorId && <CardDescription>For {sensorId}</CardDescription>}
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Loading...</div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Detections</CardTitle>
        <CardDescription>
          {sensorId ? `Latest detections for ${sensorId}` : "Latest disease detection results"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {history.length === 0 ? (
          <div className="text-sm text-muted-foreground text-center py-8">
            No detections yet. Upload an image to get started.
          </div>
        ) : (
          <>
            <div className="space-y-4">
              {history.map((detection) => (
                <div
                  key={detection.id}
                  className="flex items-start gap-4 p-4 border border-border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex-shrink-0">
                    {detection.disease_type.toLowerCase().includes("healthy") ? (
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                    ) : (
                      <AlertCircle className="h-5 w-5 text-orange-600" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium capitalize">{detection.disease_type}</span>
                      <Badge variant="secondary" className="text-xs">
                        {(detection.confidence * 100).toFixed(1)}%
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(detection.timestamp).toLocaleString()}
                      </div>
                      {!sensorId && detection.sensor_id !== "unknown" && <span>Sensor: {detection.sensor_id}</span>}
                      <span>{detection.num_detections} detection(s)</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t">
                <div className="text-sm text-muted-foreground">
                  Page {page} of {totalPages}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >
                    Next
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
