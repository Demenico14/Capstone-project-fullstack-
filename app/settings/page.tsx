"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Settings, MapPin, Database, Satellite, Save, RefreshCw, Loader2 } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

export default function SettingsPage() {
  const { toast } = useToast()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  // Sensor Coordinates
  const [sensor1Lat, setSensor1Lat] = useState("")
  const [sensor1Lng, setSensor1Lng] = useState("")
  const [sensor2Lat, setSensor2Lat] = useState("")
  const [sensor2Lng, setSensor2Lng] = useState("")
  const [sensor3Lat, setSensor3Lat] = useState("")
  const [sensor3Lng, setSensor3Lng] = useState("")
  const [farmCenterLat, setFarmCenterLat] = useState("")
  const [farmCenterLng, setFarmCenterLng] = useState("")

  // API Endpoints
  const [apiUrl, setApiUrl] = useState("")
  const [diseaseApiUrl, setDiseaseApiUrl] = useState("")
  const [yieldApiUrl, setYieldApiUrl] = useState("")

  // Satellite Configuration
  const [sentinelClientId, setSentinelClientId] = useState("")
  const [sentinelInstanceId, setSentinelInstanceId] = useState("")
  const [geeServiceAccount, setGeeServiceAccount] = useState("")

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/config")
      if (response.ok) {
        const data = await response.json()
        const config = data.config

        if (config.nodes) {
          const sensor1 = config.nodes.Sensor_1?.split(",") || []
          const sensor2 = config.nodes.Sensor_2?.split(",") || []
          const sensor3 = config.nodes.Sensor_3?.split(",") || []

          setSensor1Lat(sensor1[0] || "")
          setSensor1Lng(sensor1[1] || "")
          setSensor2Lat(sensor2[0] || "")
          setSensor2Lng(sensor2[1] || "")
          setSensor3Lat(sensor3[0] || "")
          setSensor3Lng(sensor3[1] || "")
        }

        if (config.farmCenter) {
          setFarmCenterLat(config.farmCenter.lat?.toString() || "")
          setFarmCenterLng(config.farmCenter.lng?.toString() || "")
        }

        setApiUrl(config.sensorApiUrl || "")
        setDiseaseApiUrl(config.diseaseApiUrl || "")
        setYieldApiUrl(config.yieldApiUrl || "")

        setSentinelClientId(config.sentinelClientId || "")
        setSentinelInstanceId(config.sentinelInstanceId || "")
        setGeeServiceAccount(config.geeServiceAccount || "")
      }
    } catch (error) {
      console.error("Failed to load config:", error)
      toast({
        title: "Error",
        description: "Failed to load configuration from database",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSaveToDatabase = async () => {
    setSaving(true)
    try {
      const config = {
        nodes: {
          Sensor_1: `${sensor1Lat},${sensor1Lng}`,
          Sensor_2: `${sensor2Lat},${sensor2Lng}`,
          Sensor_3: `${sensor3Lat},${sensor3Lng}`,
        },
        farmCenter: {
          lat: Number.parseFloat(farmCenterLat),
          lng: Number.parseFloat(farmCenterLng),
        },
        sensorApiUrl: apiUrl,
        diseaseApiUrl: diseaseApiUrl,
        yieldApiUrl: yieldApiUrl,
        sentinelClientId: sentinelClientId,
        sentinelInstanceId: sentinelInstanceId,
        geeServiceAccount: geeServiceAccount,
      }

      const response = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      })

      if (response.ok) {
        toast({
          title: "Success",
          description: "Configuration saved to database successfully!",
        })
        setTimeout(() => window.location.reload(), 1500)
      } else {
        throw new Error("Failed to save configuration")
      }
    } catch (error) {
      console.error("Failed to save config:", error)
      toast({
        title: "Error",
        description: "Failed to save configuration to database",
        variant: "destructive",
      })
    } finally {
      setSaving(false)
    }
  }

  const handleCopyToClipboard = () => {
    const envContent = `# Sensor Coordinates
NEXT_PUBLIC_SENSOR_1_LAT=${sensor1Lat}
NEXT_PUBLIC_SENSOR_1_LNG=${sensor1Lng}
NEXT_PUBLIC_SENSOR_2_LAT=${sensor2Lat}
NEXT_PUBLIC_SENSOR_2_LNG=${sensor2Lng}
NEXT_PUBLIC_SENSOR_3_LAT=${sensor3Lat}
NEXT_PUBLIC_SENSOR_3_LNG=${sensor3Lng}
NEXT_PUBLIC_FARM_CENTER_LAT=${farmCenterLat}
NEXT_PUBLIC_FARM_CENTER_LNG=${farmCenterLng}

# Node Coordinates JSON
NEXT_PUBLIC_NODE_COORDINATES={"Sensor_1":"${sensor1Lat},${sensor1Lng}","Sensor_2":"${sensor2Lat},${sensor2Lng}","Sensor_3":"${sensor3Lat},${sensor3Lng}"}

# API Endpoints
NEXT_PUBLIC_API_URL=${apiUrl}
NEXT_PUBLIC_DISEASE_API_URL=${diseaseApiUrl}
NEXT_PUBLIC_YIELD_API_URL=${yieldApiUrl}

# Satellite Configuration
NEXT_PUBLIC_SENTINELHUB_CLIENT_ID=${sentinelClientId}
NEXT_PUBLIC_SENTINEL_HUB_INSTANCE_ID=${sentinelInstanceId}
GEE_SERVICE_ACCOUNT_EMAIL=${geeServiceAccount}

# MongoDB Connection (add your MongoDB URI)
MONGODB_URI=mongodb://localhost:27017/cropiot
`

    navigator.clipboard.writeText(envContent)
    toast({
      title: "Copied to Clipboard",
      description: "Environment variables copied. Paste into .env.local if needed.",
    })
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-4 sm:space-y-6 lg:space-y-8">
      <div>
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-balance flex items-center gap-2 sm:gap-3">
          <Settings className="h-7 w-7 sm:h-8 sm:w-8 lg:h-10 lg:w-10 shrink-0" />
          Settings
        </h1>
        <p className="mt-1 sm:mt-2 text-sm sm:text-base text-muted-foreground">
          Configure your CropIoT system settings and credentials
        </p>
      </div>

      <Tabs defaultValue="coordinates" className="space-y-4 sm:space-y-6">
        <TabsList className="w-full flex-wrap h-auto gap-1 sm:gap-0 sm:h-10 sm:w-auto">
          <TabsTrigger value="coordinates" className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm">
            <MapPin className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            <span className="hidden xs:inline">Sensor</span> Coordinates
          </TabsTrigger>
          <TabsTrigger value="api" className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm">
            <Database className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            API <span className="hidden xs:inline">Endpoints</span>
          </TabsTrigger>
          <TabsTrigger value="satellite" className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm">
            <Satellite className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            Satellite <span className="hidden xs:inline">Config</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="coordinates">
          <Card>
            <CardHeader className="p-4 sm:p-6">
              <CardTitle className="text-lg sm:text-xl">Sensor Location Configuration</CardTitle>
              <CardDescription className="text-sm">
                Configure the GPS coordinates for your sensor nodes and farm center
              </CardDescription>
            </CardHeader>
            <CardContent className="p-4 sm:p-6 pt-0 sm:pt-0 space-y-4 sm:space-y-6">
              <div className="grid gap-4 sm:gap-6 md:grid-cols-2">
                <div className="space-y-3 sm:space-y-4">
                  <h3 className="font-semibold text-base sm:text-lg">Sensor 1</h3>
                  <div className="space-y-2">
                    <Label htmlFor="sensor1-lat" className="text-sm">
                      Latitude
                    </Label>
                    <Input
                      id="sensor1-lat"
                      type="number"
                      step="0.00000001"
                      placeholder="-18.30252535"
                      value={sensor1Lat}
                      onChange={(e) => setSensor1Lat(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="sensor1-lng" className="text-sm">
                      Longitude
                    </Label>
                    <Input
                      id="sensor1-lng"
                      type="number"
                      step="0.00000001"
                      placeholder="31.56415345"
                      value={sensor1Lng}
                      onChange={(e) => setSensor1Lng(e.target.value)}
                    />
                  </div>
                </div>

                <div className="space-y-3 sm:space-y-4">
                  <h3 className="font-semibold text-base sm:text-lg">Sensor 2</h3>
                  <div className="space-y-2">
                    <Label htmlFor="sensor2-lat" className="text-sm">
                      Latitude
                    </Label>
                    <Input
                      id="sensor2-lat"
                      type="number"
                      step="0.00000001"
                      placeholder="-18.303550260"
                      value={sensor2Lat}
                      onChange={(e) => setSensor2Lat(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="sensor2-lng" className="text-sm">
                      Longitude
                    </Label>
                    <Input
                      id="sensor2-lng"
                      type="number"
                      step="0.00000001"
                      placeholder="31.56498854"
                      value={sensor2Lng}
                      onChange={(e) => setSensor2Lng(e.target.value)}
                    />
                  </div>
                </div>

                <div className="space-y-3 sm:space-y-4">
                  <h3 className="font-semibold text-base sm:text-lg">Sensor 3</h3>
                  <div className="space-y-2">
                    <Label htmlFor="sensor3-lat" className="text-sm">
                      Latitude
                    </Label>
                    <Input
                      id="sensor3-lat"
                      type="number"
                      step="0.00000001"
                      placeholder="-18.30284377"
                      value={sensor3Lat}
                      onChange={(e) => setSensor3Lat(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="sensor3-lng" className="text-sm">
                      Longitude
                    </Label>
                    <Input
                      id="sensor3-lng"
                      type="number"
                      step="0.00000001"
                      placeholder="31.56554022"
                      value={sensor3Lng}
                      onChange={(e) => setSensor3Lng(e.target.value)}
                    />
                  </div>
                </div>

                <div className="space-y-3 sm:space-y-4">
                  <h3 className="font-semibold text-base sm:text-lg">Farm Center</h3>
                  <div className="space-y-2">
                    <Label htmlFor="center-lat" className="text-sm">
                      Latitude
                    </Label>
                    <Input
                      id="center-lat"
                      type="number"
                      step="0.00000001"
                      placeholder="-18.30252535"
                      value={farmCenterLat}
                      onChange={(e) => setFarmCenterLat(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="center-lng" className="text-sm">
                      Longitude
                    </Label>
                    <Input
                      id="center-lng"
                      type="number"
                      step="0.00000001"
                      placeholder="31.56415345"
                      value={farmCenterLng}
                      onChange={(e) => setFarmCenterLng(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 pt-2 sm:pt-4">
                <Button onClick={handleSaveToDatabase} disabled={saving} className="w-full sm:w-auto">
                  {saving ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="mr-2 h-4 w-4" />
                      Save to Database
                    </>
                  )}
                </Button>
                <Button variant="outline" onClick={handleCopyToClipboard} className="w-full sm:w-auto bg-transparent">
                  Copy .env Format
                </Button>
                <Button variant="outline" onClick={() => window.location.reload()} className="w-full sm:w-auto">
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Reload
                </Button>
              </div>

              <div className="rounded-lg bg-muted p-3 sm:p-4 text-sm">
                <p className="font-medium mb-2">How it works:</p>
                <ol className="list-decimal list-inside space-y-1 text-muted-foreground text-xs sm:text-sm">
                  <li>Enter your sensor coordinates above</li>
                  <li>Click "Save to Database" to store in MongoDB</li>
                  <li>Configuration is loaded dynamically at runtime</li>
                  <li>No need to restart the server - changes apply immediately!</li>
                  <li>Optionally copy .env format for backup</li>
                </ol>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="api">
          <Card>
            <CardHeader className="p-4 sm:p-6">
              <CardTitle className="text-lg sm:text-xl">API Endpoint Configuration</CardTitle>
              <CardDescription className="text-sm">
                Configure the backend API endpoints for sensor data and predictions
              </CardDescription>
            </CardHeader>
            <CardContent className="p-4 sm:p-6 pt-0 sm:pt-0 space-y-4 sm:space-y-6">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="api-url" className="text-sm">
                    Sensor Data API URL
                  </Label>
                  <Input
                    id="api-url"
                    type="url"
                    placeholder="http://192.168.4.2:5000"
                    value={apiUrl}
                    onChange={(e) => setApiUrl(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">Main API for sensor readings and statistics</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="disease-api-url" className="text-sm">
                    Disease Detection API URL
                  </Label>
                  <Input
                    id="disease-api-url"
                    type="url"
                    placeholder="http://192.168.4.2:8000"
                    value={diseaseApiUrl}
                    onChange={(e) => setDiseaseApiUrl(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">API for disease detection and health monitoring</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="yield-api-url" className="text-sm">
                    Yield Prediction API URL
                  </Label>
                  <Input
                    id="yield-api-url"
                    type="url"
                    placeholder="http://192.168.4.2:9000"
                    value={yieldApiUrl}
                    onChange={(e) => setYieldApiUrl(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">API for crop yield predictions</p>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 pt-2 sm:pt-4">
                <Button onClick={handleSaveToDatabase} disabled={saving} className="w-full sm:w-auto">
                  {saving ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="mr-2 h-4 w-4" />
                      Save to Database
                    </>
                  )}
                </Button>
              </div>

              <div className="rounded-lg bg-muted p-3 sm:p-4 text-sm">
                <p className="font-medium mb-2">Note:</p>
                <p className="text-muted-foreground text-xs sm:text-sm">
                  The system will automatically try fallback IPs (192.168.4.2 and 192.168.1.235) if the primary
                  connection fails.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="satellite">
          <Card>
            <CardHeader className="p-4 sm:p-6">
              <CardTitle className="text-lg sm:text-xl">Satellite Imagery Configuration</CardTitle>
              <CardDescription className="text-sm">
                Configure credentials for Sentinel Hub and Google Earth Engine
              </CardDescription>
            </CardHeader>
            <CardContent className="p-4 sm:p-6 pt-0 sm:pt-0 space-y-4 sm:space-y-6">
              <div className="space-y-3 sm:space-y-4">
                <h3 className="font-semibold text-base sm:text-lg">Sentinel Hub</h3>
                <div className="space-y-2">
                  <Label htmlFor="sentinel-client-id" className="text-sm">
                    Client ID
                  </Label>
                  <Input
                    id="sentinel-client-id"
                    type="text"
                    placeholder="your-client-id"
                    value={sentinelClientId}
                    onChange={(e) => setSentinelClientId(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sentinel-instance-id" className="text-sm">
                    Instance ID
                  </Label>
                  <Input
                    id="sentinel-instance-id"
                    type="text"
                    placeholder="your-instance-id"
                    value={sentinelInstanceId}
                    onChange={(e) => setSentinelInstanceId(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-3 sm:space-y-4">
                <h3 className="font-semibold text-base sm:text-lg">Google Earth Engine</h3>
                <div className="space-y-2">
                  <Label htmlFor="gee-service-account" className="text-sm">
                    Service Account Email
                  </Label>
                  <Input
                    id="gee-service-account"
                    type="email"
                    placeholder="your-service-account@project.iam.gserviceaccount.com"
                    value={geeServiceAccount}
                    onChange={(e) => setGeeServiceAccount(e.target.value)}
                  />
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 pt-2 sm:pt-4">
                <Button onClick={handleSaveToDatabase} disabled={saving} className="w-full sm:w-auto">
                  {saving ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="mr-2 h-4 w-4" />
                      Save to Database
                    </>
                  )}
                </Button>
              </div>

              <div className="rounded-lg bg-muted p-3 sm:p-4 text-sm">
                <p className="font-medium mb-2">Setup Guides:</p>
                <ul className="list-disc list-inside space-y-1 text-muted-foreground text-xs sm:text-sm">
                  <li>Sentinel Hub: See docs/SENTINEL_HUB_SETUP.md</li>
                  <li>Google Earth Engine: See docs/GOOGLE_EARTH_ENGINE_SETUP.md</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
