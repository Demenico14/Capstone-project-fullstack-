"use client"

import type React from "react"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useToast } from "@/hooks/use-toast"
import { Plus } from "lucide-react"

interface YieldDataFormProps {
  sensors: string[]
  onSuccess?: () => void
}

export function YieldDataForm({ sensors, onSuccess }: YieldDataFormProps) {
  const { toast } = useToast()
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState({
    sensor_id: "",
    harvest_date: new Date().toISOString().split("T")[0],
    yield_value: "",
    crop_type: "tobacco",
    unit: "kg/hectare",
    notes: "",
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      const response = await fetch("/api/yield-data", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      })

      const data = await response.json()

      if (data.success) {
        toast({
          title: "Success",
          description: "Yield data recorded successfully",
        })
        setFormData({
          sensor_id: "",
          harvest_date: new Date().toISOString().split("T")[0],
          yield_value: "",
          crop_type: "tobacco",
          unit: "kg/hectare",
          notes: "",
        })
        onSuccess?.()
      } else {
        throw new Error(data.error)
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to save yield data",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Plus className="h-5 w-5" />
          Record Harvest Yield
        </CardTitle>
        <CardDescription>Add actual harvest data to improve prediction accuracy</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="sensor_id">Sensor Location</Label>
              <Select
                value={formData.sensor_id}
                onValueChange={(value) => setFormData({ ...formData, sensor_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select sensor" />
                </SelectTrigger>
                <SelectContent>
                  {sensors.map((sensor) => (
                    <SelectItem key={sensor} value={sensor}>
                      {sensor}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="harvest_date">Harvest Date</Label>
              <Input
                id="harvest_date"
                type="date"
                value={formData.harvest_date}
                onChange={(e) => setFormData({ ...formData, harvest_date: e.target.value })}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="yield_value">Yield Value</Label>
              <Input
                id="yield_value"
                type="number"
                step="0.1"
                placeholder="e.g., 2800"
                value={formData.yield_value}
                onChange={(e) => setFormData({ ...formData, yield_value: e.target.value })}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="unit">Unit</Label>
              <Select value={formData.unit} onValueChange={(value) => setFormData({ ...formData, unit: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="kg/hectare">kg/hectare</SelectItem>
                  <SelectItem value="tons/hectare">tons/hectare</SelectItem>
                  <SelectItem value="kg">kg (total)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="notes">Notes (Optional)</Label>
            <Textarea
              id="notes"
              placeholder="Add any observations about this harvest..."
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows={3}
            />
          </div>

          <Button type="submit" disabled={loading} className="w-full">
            {loading ? "Saving..." : "Record Yield Data"}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
