"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Play, RefreshCw, CheckCircle2, XCircle, Clock } from "lucide-react"

interface TrainingStatus {
  status: "idle" | "running" | "completed" | "failed"
  progress: number
  message: string
  timestamp: string
}

export function TrainingPanel() {
  const [status, setStatus] = useState<TrainingStatus>({
    status: "idle",
    progress: 0,
    message: "Ready to train",
    timestamp: new Date().toISOString(),
  })
  const [windowDays, setWindowDays] = useState(7)
  const [epochs, setEpochs] = useState(50)
  const [isStarting, setIsStarting] = useState(false)

  useEffect(() => {
    // Poll training status
    const interval = setInterval(async () => {
      try {
        const response = await fetch("/api/train/status")
        const data = await response.json()
        setStatus(data)
      } catch (error) {
        console.error("Error fetching training status:", error)
      }
    }, 2000) // Poll every 2 seconds

    return () => clearInterval(interval)
  }, [])

  const startTraining = async () => {
    try {
      setIsStarting(true)
      const response = await fetch("/api/train/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ windowDays, epochs }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || "Failed to start training")
      }

      setStatus({
        status: "running",
        progress: 0,
        message: "Training started...",
        timestamp: new Date().toISOString(),
      })
    } catch (error) {
      console.error("Error starting training:", error)
      alert(error instanceof Error ? error.message : "Failed to start training")
    } finally {
      setIsStarting(false)
    }
  }

  const getStatusIcon = () => {
    switch (status.status) {
      case "running":
        return <RefreshCw className="h-5 w-5 animate-spin text-blue-500" />
      case "completed":
        return <CheckCircle2 className="h-5 w-5 text-green-500" />
      case "failed":
        return <XCircle className="h-5 w-5 text-red-500" />
      default:
        return <Clock className="h-5 w-5 text-muted-foreground" />
    }
  }

  const getStatusBadge = () => {
    switch (status.status) {
      case "running":
        return <Badge variant="default">Training</Badge>
      case "completed":
        return <Badge className="bg-green-500">Completed</Badge>
      case "failed":
        return <Badge variant="destructive">Failed</Badge>
      default:
        return <Badge variant="outline">Idle</Badge>
    }
  }

  const isTraining = status.status === "running"
  const canStartTraining = status.status === "idle" || status.status === "completed" || status.status === "failed"

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              {getStatusIcon()}
              Model Training
            </CardTitle>
            <CardDescription>Train ST-GNN model with your harvest data</CardDescription>
          </div>
          {getStatusBadge()}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Training Configuration */}
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="windowDays">Time Window (days)</Label>
            <Input
              id="windowDays"
              type="number"
              min={3}
              max={30}
              value={windowDays}
              onChange={(e) => setWindowDays(Number.parseInt(e.target.value))}
              disabled={isTraining}
            />
            <p className="text-xs text-muted-foreground">Days of sensor data before harvest</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="epochs">Training Epochs</Label>
            <Input
              id="epochs"
              type="number"
              min={10}
              max={200}
              value={epochs}
              onChange={(e) => setEpochs(Number.parseInt(e.target.value))}
              disabled={isTraining}
            />
            <p className="text-xs text-muted-foreground">Number of training iterations</p>
          </div>
        </div>

        {/* Training Progress */}
        {isTraining && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Progress</span>
              <span className="font-medium">{status.progress}%</span>
            </div>
            <Progress value={status.progress} />
            <p className="text-sm text-muted-foreground">{status.message}</p>
          </div>
        )}

        {/* Status Message */}
        {!isTraining && status.message && (
          <Alert variant={status.status === "failed" ? "destructive" : "default"}>
            <AlertDescription>{status.message}</AlertDescription>
          </Alert>
        )}

        {/* Action Button */}
        <Button onClick={startTraining} disabled={!canStartTraining || isStarting} className="w-full" size="lg">
          <Play className="h-4 w-4 mr-2" />
          {isStarting ? "Starting..." : "Start Training"}
        </Button>

        {/* Info */}
        <div className="rounded-lg bg-muted p-4 space-y-2">
          <p className="text-sm font-medium">Training Requirements:</p>
          <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
            <li>At least 10 harvest records with actual yield data</li>
            <li>Sensor data for {windowDays} days before each harvest</li>
            <li>MongoDB connection configured</li>
            <li>Training takes 5-15 minutes depending on data size</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  )
}
