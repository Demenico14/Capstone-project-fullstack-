"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Upload, Loader2, AlertCircle, CheckCircle2 } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"

interface DiseaseUploadProps {
  sensorId: string
  onUploadComplete?: () => void
}

export function DiseaseUpload({ sensorId, onUploadComplete }: DiseaseUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError(null)
    setResult(null)

    const reader = new FileReader()
    reader.onload = (e) => {
      setImagePreview(e.target?.result as string)
    }
    reader.readAsDataURL(file)

    try {
      const formData = new FormData()
      formData.append("image", file)
      formData.append("sensor_id", sensorId)

      const response = await fetch(`${process.env.NEXT_PUBLIC_DISEASE_API_URL}/api/detect`, {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        throw new Error("Failed to analyze image")
      }

      const data = await response.json()
      setResult(data)

      // Notify parent component to refresh data
      if (onUploadComplete) {
        onUploadComplete()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred")
    } finally {
      setUploading(false)
    }
  }

  useEffect(() => {
    if (!result || !imagePreview || !canvasRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const img = new Image()
    img.onload = () => {
      // Set canvas size to match image
      canvas.width = img.width
      canvas.height = img.height

      // Draw the image
      ctx.drawImage(img, 0, 0)

      // Draw bounding boxes if available
      if (result.bounding_boxes && Array.isArray(result.bounding_boxes)) {
        result.bounding_boxes.forEach((box: any) => {
          const { x, y, width, height, confidence } = box

          // Draw rectangle
          ctx.strokeStyle = "#ef4444" // red color for disease
          ctx.lineWidth = 3
          ctx.strokeRect(x, y, width, height)

          // Draw label background
          const label = `${(confidence * 100).toFixed(1)}%`
          ctx.font = "16px sans-serif"
          const textWidth = ctx.measureText(label).width
          ctx.fillStyle = "#ef4444"
          ctx.fillRect(x, y - 25, textWidth + 10, 25)

          // Draw label text
          ctx.fillStyle = "#ffffff"
          ctx.fillText(label, x + 5, y - 7)
        })
      } else if (result.bbox) {
        // Handle single bounding box format
        const { x, y, width, height } = result.bbox

        ctx.strokeStyle = "#ef4444"
        ctx.lineWidth = 3
        ctx.strokeRect(x, y, width, height)

        const label = `${(result.confidence * 100).toFixed(1)}%`
        ctx.font = "16px sans-serif"
        const textWidth = ctx.measureText(label).width
        ctx.fillStyle = "#ef4444"
        ctx.fillRect(x, y - 25, textWidth + 10, 25)
        ctx.fillStyle = "#ffffff"
        ctx.fillText(label, x + 5, y - 7)
      }
    }
    img.src = imagePreview
  }, [result, imagePreview])

  return (
    <Card>
      <CardHeader>
        <CardTitle>Disease Detection</CardTitle>
        <CardDescription>Upload a tobacco leaf image for {sensorId} to detect diseases</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-center w-full">
          <label
            htmlFor={`dropzone-file-${sensorId}`}
            className="flex flex-col items-center justify-center w-full h-64 border-2 border-dashed rounded-lg cursor-pointer bg-muted/50 hover:bg-muted transition-colors"
          >
            <div className="flex flex-col items-center justify-center pt-5 pb-6">
              {uploading ? (
                <>
                  <Loader2 className="w-10 h-10 mb-3 text-muted-foreground animate-spin" />
                  <p className="text-sm text-muted-foreground">Analyzing image...</p>
                </>
              ) : (
                <>
                  <Upload className="w-10 h-10 mb-3 text-muted-foreground" />
                  <p className="mb-2 text-sm text-muted-foreground">
                    <span className="font-semibold">Click to upload</span> or drag and drop
                  </p>
                  <p className="text-xs text-muted-foreground">PNG, JPG or JPEG (MAX. 10MB)</p>
                </>
              )}
            </div>
            <input
              id={`dropzone-file-${sensorId}`}
              type="file"
              className="hidden"
              accept="image/*"
              onChange={handleFileUpload}
              disabled={uploading}
            />
          </label>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {result && imagePreview && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Detection Result</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="relative w-full overflow-hidden rounded-lg bg-muted">
                  <canvas ref={canvasRef} className="w-full h-auto" />
                </div>
              </CardContent>
            </Card>

            <Alert variant={result.recommendations?.is_healthy ? "default" : "destructive"}>
              <div className="flex items-start gap-3">
                {result.recommendations?.is_healthy ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
                ) : (
                  <AlertCircle className="h-5 w-5 mt-0.5" />
                )}
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-semibold text-lg">{result.disease_type}</span>
                    <Badge variant="secondary">{(result.confidence * 100).toFixed(1)}% confidence</Badge>
                  </div>
                  {result.recommendations && (
                    <div className="space-y-3 text-sm">
                      <p>{result.recommendations.description}</p>

                      {result.recommendations.symptoms && result.recommendations.symptoms.length > 0 && (
                        <div>
                          <p className="font-semibold mb-1">Symptoms:</p>
                          <ul className="list-disc list-inside space-y-1">
                            {result.recommendations.symptoms.map((symptom: string, idx: number) => (
                              <li key={idx}>{symptom}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {result.recommendations.actions && result.recommendations.actions.length > 0 && (
                        <div>
                          <p className="font-semibold mb-1">Recommended Actions:</p>
                          <ul className="list-disc list-inside space-y-1">
                            {result.recommendations.actions.map((action: string, idx: number) => (
                              <li key={idx}>{action}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </Alert>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
