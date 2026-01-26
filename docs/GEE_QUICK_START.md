# Google Earth Engine Quick Start Guide

You've already registered for Google Earth Engine non-commercial use. Here's what to do next:

## Quick Setup Steps

### 1. Create Google Cloud Project (5 minutes)
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "New Project" → Name it `tobacco-farm-monitoring`
3. Go to "APIs & Services" → "Library"
4. Search "Earth Engine API" → Click "Enable"

### 2. Create Service Account (3 minutes)
1. Go to "IAM & Admin" → "Service Accounts"
2. Click "Create Service Account"
3. Name: `earth-engine-service`
4. Role: Select "Earth Engine Resource Admin" (or "Editor")
5. Click "Done"

### 3. Download Credentials (2 minutes)
1. Click on your service account email
2. Go to "Keys" tab
3. Click "Add Key" → "Create new key"
4. Select "JSON" → Click "Create"
5. Save the file as `gee-service-account.json` in your project root

### 4. Configure Your App (1 minute)
Open `.env.local` and add:

\`\`\`bash
GEE_SERVICE_ACCOUNT_EMAIL=earth-engine-service@tobacco-farm-monitoring.iam.gserviceaccount.com
GEE_PRIVATE_KEY_PATH=./gee-service-account.json
GEE_PROJECT_ID=tobacco-farm-monitoring
\`\`\`

Replace with your actual values from the JSON file.

### 5. Test It (1 minute)
1. Restart your dev server: `npm run dev`
2. Visit: `http://localhost:3000/api/gee/test`
3. You should see: `"success": true`

### 6. View Satellite Imagery
1. Go to your dashboard
2. Click the "Farm Map" tab
3. Click the satellite layer buttons (NDVI, Moisture, True Color)
4. You should see satellite overlays on your farm!

## Troubleshooting

### "Service account not registered"
Run this in terminal:
\`\`\`bash
earthengine authenticate
\`\`\`

### "Earth Engine API not enabled"
Go to Google Cloud Console → APIs & Services → Library → Search "Earth Engine API" → Enable

### "Invalid credentials"
Check that:
- JSON file is in the correct location
- Path in `.env.local` is correct
- Service account email matches

## What You Get

- **NDVI**: Vegetation health (red = stressed, green = healthy)
- **Moisture**: Soil water content (brown = dry, blue = wet)
- **True Color**: Natural satellite view
- **Free**: 250,000 requests/day for non-commercial use

## Next Steps

1. Set up automatic daily updates
2. Configure alerts based on NDVI thresholds
3. Compare sensor data with satellite imagery
4. Track crop health over time

For detailed instructions, see `docs/GOOGLE_EARTH_ENGINE_SETUP.md`
