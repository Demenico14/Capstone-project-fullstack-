# Sentinel Hub Setup Guide for Tobacco Farm Monitoring

## What is Sentinel Hub?

Sentinel Hub is a cloud-based satellite imagery service that provides access to Sentinel-2 satellite data. For your tobacco farm, it can provide:

- **NDVI (Normalized Difference Vegetation Index)**: Measures crop health and vigor
- **Moisture Index**: Monitors soil and plant moisture levels
- **True Color Images**: Visual inspection of your farm
- **Historical Data**: Track changes over time

## Step 1: Create a Sentinel Hub Account

1. Go to [Sentinel Hub](https://www.sentinel-hub.com/)
2. Click **"Sign Up"** in the top right
3. Choose **"Trial Account"** (free for 30 days, includes 10,000 processing units)
4. Fill in your details:
   - Email address
   - Password
   - Organization name (e.g., "Your Farm Name")
   - Country: Zimbabwe

## Step 2: Get Your API Credentials

### 2.1 Create an OAuth Client

1. Log in to [Sentinel Hub Dashboard](https://apps.sentinel-hub.com/dashboard/)
2. Go to **"User Settings"** (top right, click your profile)
3. Click **"OAuth clients"** in the left menu
4. Click **"+ New OAuth Client"**
5. Fill in the form:
   - **Name**: "Tobacco Farm Monitor"
   - **Grant Type**: Select "Client Credentials"
   - **Redirect URI**: Leave empty
6. Click **"Create"**
7. **IMPORTANT**: Copy and save these credentials immediately:
   - **Client ID**: (looks like `a1b2c3d4-e5f6-7890-abcd-ef1234567890`)
   - **Client Secret**: (looks like `xYz123AbC456DeF789...`)

### 2.2 Get Your Instance ID

1. In the Sentinel Hub Dashboard, go to **"Configuration Utility"**
2. Click **"+ Create New Configuration"**
3. **IMPORTANT - Choose the Right Template**:
   
   When asked "Create configuration based on:", select:
   
   **For Tobacco Farm Monitoring (RECOMMENDED):**
   - **"Simple Sentinel-2 L2A template"**
   
   **Why this template?**
   - ✅ **Free**: No additional costs
   - ✅ **Perfect Resolution**: 10-20m per pixel (ideal for field-level monitoring)
   - ✅ **Regular Updates**: New images every 5 days
   - ✅ **Agriculture-Ready**: Includes NDVI, NDWI, EVI, and moisture indices
   - ✅ **Atmospheric Correction**: L2A data is already corrected for clouds and atmosphere
   
   **Alternative Templates (if needed):**
   
   | Template | Use Case | Cost | Resolution |
   |----------|----------|------|------------|
   | **Simple Sentinel-2 L2A** | General farm monitoring (BEST) | Free | 10-20m |
   | **Planetary Variables - Soil Water Content** | Detailed soil moisture only | Paid | 30m |
   | **Planetary Variables - Crop Biomass** | Crop yield estimation | Paid | 30m |
   | **Sentinel-3 OLCI** | Large area monitoring (>100 hectares) | Free | 300m |
   | **Landsat 8-9 L2** | Historical data (since 2013) | Free | 30m |
   
   **Decision Tree:**
   \`\`\`
   Farm Size < 50 hectares? → Use "Simple Sentinel-2 L2A template"
   Need soil moisture only? → Use "Planetary Variables - Soil Water Content"
   Need historical data? → Use "Simple Landsat 8-9 L2 template"
   Farm Size > 100 hectares? → Use "Sentinel-3 OLCI template"
   \`\`\`
4. Fill in the configuration details:
   - **Name**: "Tobacco Farm NDVI"
   - **Description**: "NDVI and moisture monitoring for tobacco farm"
5. Click **"Create"**
6. Copy the **Instance ID** (looks like `12345678-90ab-cdef-1234-567890abcdef`)

## Step 3: Configure Your Project

### 3.1 Add Credentials to Environment Variables

Open your `.env.local` file and add:

\`\`\`bash
# Sentinel Hub Configuration
NEXT_PUBLIC_SENTINEL_HUB_CLIENT_ID=your_client_id_here
SENTINEL_HUB_CLIENT_SECRET=your_client_secret_here
NEXT_PUBLIC_SENTINEL_HUB_INSTANCE_ID=your_instance_id_here

# Your farm center coordinates (already configured)
NEXT_PUBLIC_FARM_CENTER_LAT=-17.8252
NEXT_PUBLIC_FARM_CENTER_LNG=31.0335
\`\`\`

**Security Note**: 
- `NEXT_PUBLIC_*` variables are visible in the browser
- `SENTINEL_HUB_CLIENT_SECRET` (without NEXT_PUBLIC) is only accessible on the server

### 3.2 Install Required Package

\`\`\`bash
npm install @sentinel-hub/sentinelhub-js
\`\`\`

## Step 4: Understanding Your Farm Coordinates

Your sensor nodes are configured in `.env.local`:

\`\`\`bash
# Sensor 1 coordinates
NEXT_PUBLIC_SENSOR_1_LAT=-17.8252
NEXT_PUBLIC_SENSOR_1_LNG=31.0335

# Add more sensors as needed
NEXT_PUBLIC_SENSOR_2_LAT=-17.8260
NEXT_PUBLIC_SENSOR_2_LNG=31.0340
\`\`\`

Sentinel Hub will fetch satellite data for the area around these coordinates.

## Step 5: How Sentinel Hub Works for Your Farm

### 5.1 What Data You'll Get

**NDVI (Vegetation Health)**:
- **Range**: -1 to +1
- **Interpretation**:
  - `0.8 - 1.0`: Very healthy, dense vegetation (dark green)
  - `0.6 - 0.8`: Healthy vegetation (green)
  - `0.4 - 0.6`: Moderate vegetation (light green)
  - `0.2 - 0.4`: Sparse vegetation (yellow)
  - `< 0.2`: Bare soil or stressed plants (red)

**Moisture Index**:
- **Range**: -1 to +1
- **Interpretation**:
  - `> 0.3`: High moisture (blue)
  - `0.1 - 0.3`: Moderate moisture (light blue)
  - `< 0.1`: Low moisture/dry (orange/red)

### 5.2 Satellite Revisit Time

- **Sentinel-2**: Passes over your farm every **5 days**
- **Cloud Coverage**: Zimbabwe's dry season (May-October) has less cloud cover
- **Best Time**: Request images from the last 10 days to ensure cloud-free data

## Step 6: API Request Examples

### 6.1 Get NDVI for Your Farm

\`\`\`javascript
// This will be in your backend API route
const response = await fetch('https://services.sentinel-hub.com/api/v1/process', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    input: {
      bounds: {
        bbox: [
          31.0300, -17.8280,  // Bottom-left: [lng, lat]
          31.0370, -17.8220   // Top-right: [lng, lat]
        ],
        properties: { crs: 'http://www.opengis.net/def/crs/EPSG/0/4326' }
      },
      data: [{
        type: 'sentinel-2-l2a',
        dataFilter: {
          timeRange: {
            from: '2025-10-01T00:00:00Z',
            to: '2025-10-09T23:59:59Z'
          },
          maxCloudCoverage: 30
        }
      }]
    },
    output: {
      width: 512,
      height: 512,
      responses: [{
        identifier: 'default',
        format: { type: 'image/png' }
      }]
    },
    evalscript: `
      //VERSION=3
      function setup() {
        return {
          input: ["B04", "B08", "dataMask"],
          output: { bands: 4 }
        };
      }
      
      function evaluatePixel(sample) {
        let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
        
        // Color coding for NDVI
        if (ndvi < 0.2) return [0.8, 0.2, 0.2, sample.dataMask]; // Red - stressed
        if (ndvi < 0.4) return [0.9, 0.7, 0.3, sample.dataMask]; // Yellow - sparse
        if (ndvi < 0.6) return [0.6, 0.9, 0.4, sample.dataMask]; // Light green - moderate
        if (ndvi < 0.8) return [0.2, 0.8, 0.3, sample.dataMask]; // Green - healthy
        return [0.1, 0.5, 0.2, sample.dataMask]; // Dark green - very healthy
      }
    `
  })
});
\`\`\`

### 6.2 Understanding the Bounding Box

Your farm area is defined by coordinates:

\`\`\`
Top-Left: (-17.8220, 31.0300)
Top-Right: (-17.8220, 31.0370)
Bottom-Left: (-17.8280, 31.0300)
Bottom-Right: (-17.8280, 31.0370)
\`\`\`

This creates a rectangle covering approximately **0.7 km × 0.7 km** (about 50 hectares).

## Step 7: Integration with Your System

### 7.1 Create Backend API Route

Create `app/api/satellite/route.ts`:

\`\`\`typescript
import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get('type') || 'ndvi'; // ndvi, moisture, or true-color
  
  try {
    // Get OAuth token
    const tokenResponse = await fetch('https://services.sentinel-hub.com/oauth/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'client_credentials',
        client_id: process.env.NEXT_PUBLIC_SENTINEL_HUB_CLIENT_ID!,
        client_secret: process.env.SENTINEL_HUB_CLIENT_SECRET!,
      }),
    });
    
    const { access_token } = await tokenResponse.json();
    
    // Get satellite image
    const imageResponse = await fetch('https://services.sentinel-hub.com/api/v1/process', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${access_token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        // ... (request body from example above)
      }),
    });
    
    const imageBlob = await imageResponse.blob();
    
    return new NextResponse(imageBlob, {
      headers: {
        'Content-Type': 'image/png',
      },
    });
  } catch (error) {
    console.error('Sentinel Hub error:', error);
    return NextResponse.json({ error: 'Failed to fetch satellite data' }, { status: 500 });
  }
}
\`\`\`

### 7.2 Display in Your Dashboard

The farm map component will automatically fetch and display satellite overlays:

\`\`\`tsx
// In your FarmMap component
const [satelliteLayer, setSatelliteLayer] = useState<'ndvi' | 'moisture' | 'none'>('ndvi');

// Fetch satellite image
const fetchSatelliteImage = async () => {
  const response = await fetch(`/api/satellite?type=${satelliteLayer}`);
  const blob = await response.blob();
  const imageUrl = URL.createObjectURL(blob);
  
  // Display as overlay on map
  // ... (map overlay code)
};
\`\`\`

## Step 8: Cost Management

### Free Tier Limits:
- **10,000 Processing Units (PU)** per month
- Each request costs approximately:
  - 512×512 image: ~3 PU
  - 1024×1024 image: ~12 PU
- **Your usage**: ~3,000 requests per month = 9,000 PU (within free tier)

### Tips to Stay Within Free Tier:
1. **Cache images**: Store satellite images for 5 days (satellite revisit time)
2. **Request only when needed**: Don't auto-refresh every page load
3. **Use smaller images**: 512×512 is sufficient for farm monitoring
4. **Limit time range**: Request last 10 days only

## Step 9: Testing Your Setup

### 9.1 Test API Credentials

\`\`\`bash
curl -X POST https://services.sentinel-hub.com/oauth/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=client_credentials' \
  -d 'client_id=YOUR_CLIENT_ID' \
  -d 'client_secret=YOUR_CLIENT_SECRET'
\`\`\`

Expected response:
\`\`\`json
{
  "access_token": "eyJhbGc...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
\`\`\`

### 9.2 Test Image Request

Use the Sentinel Hub Playground:
1. Go to [EO Browser](https://apps.sentinel-hub.com/eo-browser/)
2. Search for your coordinates: `-17.8252, 31.0335`
3. Select **Sentinel-2 L2A**
4. Choose **NDVI** visualization
5. Pick a recent cloud-free date
6. Verify you can see your farm

## Step 10: Troubleshooting

### Common Issues:

**1. "Invalid credentials" error**
- Double-check Client ID and Secret
- Ensure no extra spaces when copying
- Verify OAuth client is active in dashboard

**2. "No data available" error**
- Check date range (last 10 days)
- Verify coordinates are correct
- Ensure maxCloudCoverage is not too restrictive (try 50%)

**3. "Quota exceeded" error**
- You've used all 10,000 PU for the month
- Wait until next month or upgrade plan
- Implement caching to reduce requests

**4. Images are all black/white**
- Cloud coverage is too high
- Try different date range
- Check evalscript syntax

## Next Steps

1. **Set up credentials** (Steps 1-3)
2. **Test API connection** (Step 9)
3. **Integrate with dashboard** (Step 7)
4. **Monitor usage** in Sentinel Hub Dashboard
5. **Set up caching** to optimize costs

## Support Resources

- [Sentinel Hub Documentation](https://docs.sentinel-hub.com/)
- [API Reference](https://docs.sentinel-hub.com/api/latest/)
- [Custom Scripts](https://custom-scripts.sentinel-hub.com/) - Pre-made evalscripts
- [Community Forum](https://forum.sentinel-hub.com/)

## Questions?

If you encounter issues:
1. Check the Sentinel Hub Dashboard for error logs
2. Verify your coordinates are within Zimbabwe
3. Ensure your trial account is still active
4. Contact Sentinel Hub support: support@sentinel-hub.com
