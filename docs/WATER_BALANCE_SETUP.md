# Water Balance Dashboard Setup Guide

## Overview

The Water Balance Dashboard computes and visualizes evapotranspiration (ET), precipitation (P), soil moisture change (ΔS), and irrigation (I) using Google Earth Engine satellite data and IoT sensor data.

## Features

- **Real-time Water Balance Calculation**: Computes `ET = P + I - R - ΔS`
- **Satellite Data Integration**: NDVI, rainfall (CHIRPS), and ET (MOD16A2GF) from Google Earth Engine
- **IoT Sensor Integration**: Soil moisture and irrigation data from your ESP8266 sensors
- **Interactive Visualizations**: Charts showing NDVI trends, ET vs rainfall, crop coefficient (Kc), and water balance timeline
- **Mathematical Formulas**: LaTeX-rendered equations with tooltips explaining each parameter

## Prerequisites

1. **Google Earth Engine Account**: Already registered for non-commercial use ✓
2. **GEE Service Account**: Follow `docs/GOOGLE_EARTH_ENGINE_SETUP.md` to create service account
3. **Environment Variables**: Configure in `.env.local`
4. **IoT Sensors**: ESP8266 sensors collecting soil moisture data

## Installation

### 1. Install Dependencies

The required packages are already in `package.json`:
- `@google/earthengine`: Google Earth Engine API client
- `katex` & `react-katex`: Mathematical formula rendering
- `recharts`: Chart visualizations

Run:
\`\`\`bash
npm install
\`\`\`

### 2. Configure Environment Variables

Your `.env.local` should have:
\`\`\`bash
# Google Earth Engine (from service account JSON)
GEE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
GEE_CLIENT_EMAIL="your-service-account@your-project.iam.gserviceaccount.com"

# Farm coordinates
NEXT_PUBLIC_FARM_CENTER_LAT=-18.30252535
NEXT_PUBLIC_FARM_CENTER_LNG=31.56415345

# Backend API for IoT sensor data
NEXT_PUBLIC_API_URL=http://192.168.4.2:5000
\`\`\`

### 3. Verify GEE Connection

Test your Google Earth Engine setup:
\`\`\`bash
# Start dev server
npm run dev

# Visit test endpoint
http://localhost:3000/api/gee/test
\`\`\`

You should see: `{"success": true, "message": "Google Earth Engine is configured correctly"}`

## How It Works

### Water Balance Equation

$$ET = P + I - R - \Delta S$$

Where:
- **ET** (Evapotranspiration): Water lost through evaporation and plant transpiration
  - Calculated as: `ET = Kc × ETo`
- **P** (Precipitation): Daily rainfall from CHIRPS satellite dataset
- **I** (Irrigation): Measured from IoT flow sensors (currently mock data)
- **R** (Runoff): Surface water runoff (assumed ≈ 0 for simplicity)
- **ΔS** (Soil Moisture Change): Change in soil water storage from IoT sensors
  - Calculated as: `ΔS = SoilMoisture_today - SoilMoisture_previous`

### Crop Coefficient (Kc)

$$K_c = \frac{NDVI - NDVI_{min}}{NDVI_{max} - NDVI_{min}}$$

- Derived from NDVI (Normalized Difference Vegetation Index)
- Ranges from 0 to 1.2
- Higher values indicate healthier, more water-demanding crops

### Data Sources

1. **Sentinel-2 (NDVI)**: `COPERNICUS/S2_SR_HARMONIZED`
   - 10m resolution
   - Updated every 5 days
   - Measures vegetation health

2. **CHIRPS (Rainfall)**: `UCSB-CHG/CHIRPS/DAILY`
   - Daily precipitation data
   - 5km resolution
   - Global coverage

3. **MOD16A2GF (ET)**: `MODIS/061/MOD16A2GF`
   - 500m resolution
   - 8-day composite
   - Evapotranspiration estimates

4. **IoT Sensors**: Your ESP8266 network
   - Soil moisture readings
   - Irrigation flow data (to be implemented)

## Usage

### Access the Dashboard

1. **Via Sidebar**: Click "Water Balance" in the sidebar
2. **Via Dashboard Tab**: Click the "Water Balance" tab on the main dashboard
3. **Direct URL**: Navigate to `/water-balance`

### Features

- **Date Range Selection**: Choose custom date ranges for analysis
- **View Modes**: Switch between daily, weekly, and seasonal summaries
- **Interactive Charts**: Hover over charts to see detailed values
- **Formula Tooltips**: Click on formula components to see explanations
- **Current Balance**: See real-time water surplus or deficit

### Interpreting Results

- **Positive Balance (+)**: Water surplus - reduce irrigation
- **Negative Balance (-)**: Water deficit - increase irrigation
- **NDVI Trends**: Monitor crop health over time
- **Kc Values**: Understand crop water requirements
- **ΔS Changes**: Track soil moisture variations

## API Endpoints

### `/api/water-balance`

Fetches water balance data for a specific location and date range.

**Parameters:**
- `lat`: Latitude (default: farm center)
- `lng`: Longitude (default: farm center)
- `startDate`: Start date (YYYY-MM-DD)
- `endDate`: End date (YYYY-MM-DD)

**Response:**
\`\`\`json
{
  "success": true,
  "data": {
    "ndvi": [...],
    "rainfall": [...],
    "et": [...],
    "kc": [...],
    "deltaS": [...],
    "irrigation": [...],
    "waterBalance": [...]
  },
  "metadata": {
    "location": { "lat": -18.30252535, "lng": 31.56415345 },
    "dateRange": { "start": "2025-01-01", "end": "2025-01-30" },
    "areaSize": "500m radius"
  }
}
\`\`\`

## Troubleshooting

### "Failed to fetch water balance data"

1. **Check GEE credentials**: Visit `/api/gee/test`
2. **Verify environment variables**: Ensure `GEE_PRIVATE_KEY` and `GEE_CLIENT_EMAIL` are set
3. **Check date range**: Ensure dates are valid and not in the future
4. **Restart dev server**: Environment variables require server restart

### "No sensor data available"

1. **Check backend API**: Ensure `NEXT_PUBLIC_API_URL` is correct
2. **Verify sensors are active**: Check sensor status in dashboard
3. **Check date range**: Ensure sensors were collecting data during selected period

### Charts not displaying

1. **Check browser console**: Look for JavaScript errors
2. **Verify data format**: Ensure API returns valid data structure
3. **Clear cache**: Try hard refresh (Ctrl+Shift+R)

## Next Steps

1. **Implement Irrigation Sensors**: Add flow meters to track irrigation input
2. **Add Runoff Calculation**: Implement FAO curve number method for runoff estimation
3. **Historical Analysis**: Store computed values in database for trend analysis
4. **Alerts**: Set up notifications for water deficit/surplus conditions
5. **Recommendations**: Add AI-powered irrigation recommendations based on water balance

## References

- [FAO-56 Evapotranspiration](http://www.fao.org/3/x0490e/x0490e00.htm)
- [Google Earth Engine Datasets](https://developers.google.com/earth-engine/datasets)
- [CHIRPS Rainfall Data](https://www.chc.ucsb.edu/data/chirps)
- [MODIS ET Product](https://modis.gsfc.nasa.gov/data/dataprod/mod16.php)
