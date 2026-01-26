# Google Earth Engine Setup Guide

## Overview
Google Earth Engine (GEE) provides free access to satellite imagery and geospatial analysis. This guide will help you integrate GEE with your tobacco farm monitoring system to get NDVI, moisture, and other agricultural indices.

## Prerequisites
- ✅ Google Earth Engine account (non-commercial use) - You already have this!
- Google Cloud Platform account
- Node.js project with Next.js

---

## Step 1: Set Up Google Cloud Project

### 1.1 Create a Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a project"** → **"New Project"**
3. Enter project name: `tobacco-farm-monitoring`
4. Click **"Create"**

### 1.2 Enable Earth Engine API
1. In your project, go to **"APIs & Services"** → **"Library"**
2. Search for **"Earth Engine API"**
3. Click on it and press **"Enable"**
4. Wait for the API to be enabled (takes a few seconds)

---

## Step 2: Create Service Account

### 2.1 Create the Service Account
1. Go to **"IAM & Admin"** → **"Service Accounts"**
2. Click **"Create Service Account"**
3. Fill in the details:
   - **Service account name**: `earth-engine-service`
   - **Service account ID**: `earth-engine-service` (auto-generated)
   - **Description**: `Service account for Earth Engine API access`
4. Click **"Create and Continue"**

### 2.2 Grant Permissions
1. In the **"Grant this service account access to project"** section:
   - Select role: **"Earth Engine Resource Admin"**
   - If not available, select **"Editor"** or **"Owner"**
2. Click **"Continue"**
3. Click **"Done"**

### 2.3 Create and Download Key
1. Find your newly created service account in the list
2. Click on the service account email
3. Go to the **"Keys"** tab
4. Click **"Add Key"** → **"Create new key"**
5. Select **"JSON"** format
6. Click **"Create"**
7. The JSON key file will download automatically
8. **IMPORTANT**: Keep this file secure! It contains credentials.

---

## Step 3: Register Service Account with Earth Engine

### 3.1 Get Service Account Email
Open the downloaded JSON file and find the `client_email` field:
\`\`\`json
{
  "client_email": "earth-engine-service@tobacco-farm-monitoring.iam.gserviceaccount.com",
  ...
}
\`\`\`

### 3.2 Register with Earth Engine
1. Go to [Earth Engine Code Editor](https://code.earthengine.google.com/)
2. Sign in with your Google account (the one registered for Earth Engine)
3. Click on **"Assets"** tab in the left panel
4. Click **"NEW"** → **"Cloud Project"**
5. Enter your Google Cloud project ID: `tobacco-farm-monitoring`
6. Click **"Select"**

### 3.3 Grant Access to Service Account
Run this command in your terminal (replace with your service account email):
\`\`\`bash
earthengine authenticate
earthengine acl set -u earth-engine-service@tobacco-farm-monitoring.iam.gserviceaccount.com:R users/YOUR_USERNAME
\`\`\`

Or use the Earth Engine Python API:
\`\`\`python
import ee
ee.Authenticate()
ee.Initialize()
\`\`\`

---

## Step 4: Configure Your Application

### 4.1 Store Service Account Key
1. Rename the downloaded JSON file to `gee-service-account.json`
2. Move it to your project root directory
3. **Add to .gitignore** to prevent committing credentials:
\`\`\`bash
echo "gee-service-account.json" >> .gitignore
\`\`\`

### 4.2 Update .env.local
Add these environment variables to your `.env.local` file:

\`\`\`bash
# Google Earth Engine Configuration
GEE_SERVICE_ACCOUNT_EMAIL=earth-engine-service@tobacco-farm-monitoring.iam.gserviceaccount.com
GEE_PRIVATE_KEY_PATH=./gee-service-account.json
GEE_PROJECT_ID=tobacco-farm-monitoring
\`\`\`

**Alternative**: Store the entire JSON as a base64 string (better for deployment):
\`\`\`bash
# Convert JSON to base64
cat gee-service-account.json | base64 > gee-key-base64.txt

# Add to .env.local
GEE_SERVICE_ACCOUNT_JSON=<paste the base64 string here>
\`\`\`

---

## Step 5: Install Required Packages

Install the Google Earth Engine Node.js client:

\`\`\`bash
npm install @google/earthengine
\`\`\`

---

## Step 6: Test Your Setup

### 6.1 Test Authentication
Visit: `http://localhost:3000/api/gee/test`

You should see:
\`\`\`json
{
  "success": true,
  "message": "Google Earth Engine authentication successful",
  "serviceAccount": "earth-engine-service@tobacco-farm-monitoring.iam.gserviceaccount.com"
}
\`\`\`

### 6.2 Test NDVI Retrieval
Visit: `http://localhost:3000/api/gee?layer=ndvi`

You should see satellite imagery data for your farm coordinates.

---

## Available Satellite Layers

Once configured, you can request these layers:

### 1. **NDVI** (Normalized Difference Vegetation Index)
- **URL**: `/api/gee?layer=ndvi`
- **Purpose**: Vegetation health and crop vigor
- **Values**: -1 to 1 (higher = healthier vegetation)
- **Color**: Red (poor) → Yellow → Green (healthy)

### 2. **Moisture** (Soil Water Content)
- **URL**: `/api/gee?layer=moisture`
- **Purpose**: Soil moisture levels
- **Values**: 0 to 1 (higher = more moisture)
- **Color**: Brown (dry) → Blue (wet)

### 3. **EVI** (Enhanced Vegetation Index)
- **URL**: `/api/gee?layer=evi`
- **Purpose**: Similar to NDVI but more sensitive in high biomass areas
- **Values**: -1 to 1
- **Color**: Red → Yellow → Green

### 4. **True Color** (RGB)
- **URL**: `/api/gee?layer=true-color`
- **Purpose**: Natural color satellite image
- **Use**: Visual inspection of farm

---

## Troubleshooting

### Error: "Service account not registered"
**Solution**: Make sure you've registered your service account with Earth Engine:
\`\`\`bash
earthengine authenticate
earthengine acl set -u YOUR_SERVICE_ACCOUNT_EMAIL:R users/YOUR_USERNAME
\`\`\`

### Error: "Earth Engine API not enabled"
**Solution**: 
1. Go to Google Cloud Console
2. Navigate to "APIs & Services" → "Library"
3. Search for "Earth Engine API"
4. Click "Enable"

### Error: "Invalid credentials"
**Solution**: 
1. Check that your JSON key file is in the correct location
2. Verify the path in `.env.local` is correct
3. Make sure the file hasn't been corrupted

### Error: "Quota exceeded"
**Solution**: 
- Earth Engine has usage limits
- For non-commercial use: 250,000 requests per day
- Implement caching to reduce API calls
- Consider using Sentinel Hub as a fallback

---

## Cost and Limits

### Free Tier (Non-Commercial)
- ✅ **Free** for non-commercial use
- ✅ 250,000 requests per day
- ✅ Access to all public datasets
- ✅ Sentinel-2, Landsat, MODIS, and more

### Best Practices
1. **Cache results**: Store satellite images locally for 24 hours
2. **Batch requests**: Fetch multiple layers in one request
3. **Use appropriate resolution**: Don't request higher resolution than needed
4. **Monitor usage**: Check Google Cloud Console for API usage

---

## Next Steps

1. ✅ Complete the setup steps above
2. ✅ Test the API endpoints
3. ✅ View satellite imagery on your farm map
4. ✅ Set up automatic daily updates
5. ✅ Configure alerts based on NDVI thresholds

---

## Support

- **Earth Engine Documentation**: https://developers.google.com/earth-engine
- **Earth Engine Forum**: https://groups.google.com/g/google-earth-engine-developers
- **Google Cloud Support**: https://cloud.google.com/support

---

## Security Notes

⚠️ **IMPORTANT**:
- Never commit `gee-service-account.json` to Git
- Never share your service account key
- Add the key file to `.gitignore`
- Use environment variables for deployment
- Rotate keys periodically (every 90 days recommended)
