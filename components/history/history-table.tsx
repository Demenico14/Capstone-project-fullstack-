"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Download } from "lucide-react"

export function HistoryTable() {
  const [downloading, setDownloading] = useState(false)

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      const response = await fetch(`${apiUrl}/api/download`)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "crop_data.csv"
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error("Error downloading CSV:", error)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Card>
      <CardHeader className="p-4 sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle className="text-lg sm:text-xl">Historical Data Export</CardTitle>
          <Button onClick={handleDownload} disabled={downloading} className="w-full sm:w-auto">
            <Download className="mr-2 h-4 w-4" />
            {downloading ? "Downloading..." : "Download CSV"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-4 sm:p-6 pt-0 sm:pt-0">
        <p className="text-xs sm:text-sm text-muted-foreground">
          Download all historical sensor data as a CSV file for further analysis in Excel, Python, or other data
          analysis tools.
        </p>
        <div className="mt-3 sm:mt-4 rounded-lg bg-muted p-3 sm:p-4">
          <h3 className="font-semibold mb-2 text-sm sm:text-base">CSV Format:</h3>
          <ul className="text-xs sm:text-sm text-muted-foreground grid grid-cols-2 sm:block gap-1 sm:space-y-1">
            <li>• Timestamp</li>
            <li>• Sensor ID</li>
            <li>• Soil Moisture (%)</li>
            <li>• pH Level</li>
            <li>• Temperature (°C)</li>
            <li>• Humidity (%)</li>
            <li>• RSSI (dBm)</li>
            <li>• SNR (dB)</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  )
}
