"use client"

import type React from "react"

import { useState } from "react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { DiseaseUpload } from "@/components/crop-health/disease-upload"
import { DiseaseStats } from "@/components/crop-health/disease-stats"
import { DiseaseHistory } from "@/components/crop-health/disease-history"

export default function DiseaseDetectionPage() {
  const [selectedSensor, setSelectedSensor] = useState<string>("Sensor_1")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string>("")
  const [detecting, setDetecting] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string>("")
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const handleUploadComplete = () => {
    setRefreshTrigger((prev) => prev + 1)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      setPreviewUrl(URL.createObjectURL(file))
      setResult(null)
      setError("")
    }
  }

  const handleDetect = async () => {
    if (!selectedFile || !selectedSensor) {
      setError("Please select both a sensor and an image")
      return
    }

    setDetecting(true)
    setError("")

    try {
      const formData = new FormData()
      formData.append("file", selectedFile)
      formData.append("sensor_id", selectedSensor)

      const response = await fetch(`${process.env.NEXT_PUBLIC_DISEASE_API_URL || "http://192.168.4.2:8000"}/detect`, {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        throw new Error("Disease detection failed")
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to detect disease")
    } finally {
      setDetecting(false)
    }
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold">Disease Detection</h1>
        <p className="text-sm sm:text-base text-muted-foreground">Upload tobacco leaf images for disease analysis</p>
      </div>

      <div>
        <label className="mb-2 block text-sm font-medium">Select Sensor</label>
        <Select value={selectedSensor} onValueChange={setSelectedSensor}>
          <SelectTrigger className="w-full sm:w-64">
            <SelectValue placeholder="Choose sensor..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="Sensor_1">Sensor 1</SelectItem>
            <SelectItem value="Sensor_2">Sensor 2</SelectItem>
            <SelectItem value="Sensor_3">Sensor 3</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-4 sm:gap-6 lg:grid-cols-2">
        <div className="space-y-4 sm:space-y-6">
          <DiseaseUpload sensorId={selectedSensor} onUploadComplete={handleUploadComplete} />
          <DiseaseStats sensorId={selectedSensor} refreshTrigger={refreshTrigger} />
        </div>

        <div>
          <DiseaseHistory sensorId={selectedSensor} refreshTrigger={refreshTrigger} />
        </div>
      </div>
    </div>
  )
}
