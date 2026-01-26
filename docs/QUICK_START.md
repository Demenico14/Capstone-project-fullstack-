# Quick Start Guide - Tobacco Farm Monitoring System

## Prerequisites

- Python 3.8+
- Node.js 18+
- MongoDB installed and running
- ESP8266 devices with LoRa modules (optional, for field sensors)

## Step 1: Clone and Install

\`\`\`bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
npm install
\`\`\`

## Step 2: Configure Environment Variables

Copy the example environment file:

\`\`\`bash
cp .env.example .env.local
\`\`\`

Edit `.env.local` with your settings:

\`\`\`bash
# Update API URLs if running on different machine
NEXT_PUBLIC_API_URL=http://192.168.1.235:5000
NEXT_PUBLIC_DISEASE_API_URL=http://192.168.1.235:8000
NEXT_PUBLIC_YIELD_API_URL=http://192.168.1.235:9000

# Update with your actual farm coordinates
NEXT_PUBLIC_FARM_CENTER_LAT=-17.8252
NEXT_PUBLIC_FARM_CENTER_LNG=31.0335

# Add your sensor locations
NEXT_PUBLIC_SENSOR_1_LAT=-17.8252
NEXT_PUBLIC_SENSOR_1_LNG=31.0335
\`\`\`

## Step 3: Start MongoDB

\`\`\`bash
# Windows
net start MongoDB

# Linux/Mac
sudo systemctl start mongod
\`\`\`

## Step 4: Start Backend Services

### Option A: Using Startup Scripts (Recommended)

**Windows:**
\`\`\`bash
python scripts/start_all_windows.py
\`\`\`

**Linux/Mac:**
\`\`\`bash
python scripts/start_all_unix.py
\`\`\`

### Option B: Manual Start

Open 3 separate terminals:

**Terminal 1 - Sensor API:**
\`\`\`bash
cd backend
python api_server.py
\`\`\`

**Terminal 2 - Disease Detection:**
\`\`\`bash
cd backend
python app.py
\`\`\`

**Terminal 3 - Yield Prediction:**
\`\`\`bash
cd backend
python yield_api.py
\`\`\`

## Step 5: Start Frontend

\`\`\`bash
npm run dev
\`\`\`

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Step 6: Add Initial Data

### Option 1: Generate Sample Data

\`\`\`bash
cd backend/scripts
python generate_yield_data.py
\`\`\`

### Option 2: Use Real Sensor Data

1. Flash ESP8266 transmitters with `esp8266/lora_transmitter/lora_transmitter.ino`
2. Flash ESP8266 receiver with `esp8266/lora_wifi_bridge/lora_wifi_bridge.ino`
3. Update WiFi credentials in receiver code
4. Power on devices - data will automatically flow to MongoDB

## Step 7: Set Up Satellite Imagery (Optional)

For NDVI and moisture heatmaps:

1. Follow the detailed guide: `docs/SENTINEL_HUB_SETUP.md`
2. Sign up at [Sentinel Hub](https://www.sentinel-hub.com/)
3. Get your API credentials
4. Add to `.env.local`:

\`\`\`bash
NEXT_PUBLIC_SENTINEL_HUB_CLIENT_ID=your_client_id
SENTINEL_HUB_CLIENT_SECRET=your_client_secret
NEXT_PUBLIC_SENTINEL_HUB_INSTANCE_ID=your_instance_id
\`\`\`

## Verify Installation

### Check Backend Services

1. **Sensor API**: http://localhost:5000/health
2. **Disease API**: http://localhost:8000/health
3. **Yield API**: http://localhost:9000/health

All should return `{"status": "healthy"}`

### Check Frontend

1. Dashboard should show sensor cards
2. Map should display your farm location
3. Click on a sensor to view detailed data

## Troubleshooting

### Backend won't start

- Check MongoDB is running: `mongo --eval "db.version()"`
- Check ports 5000, 8000, 9000 are not in use
- Check Python dependencies: `pip install -r requirements.txt`

### Frontend shows "No data"

- Verify backend services are running
- Check browser console for API errors
- Verify MongoDB has data: `mongo` → `use tobacco_farm` → `db.sensor_data.count()`

### Map not showing

- Check coordinates in `.env.local` are valid
- Verify `NEXT_PUBLIC_FARM_CENTER_LAT` and `NEXT_PUBLIC_FARM_CENTER_LNG` are set
- Check browser console for errors

### Satellite images not loading

- Verify Sentinel Hub credentials are correct
- Check you haven't exceeded free tier (10,000 PU/month)
- Try different date range (last 10 days)
- Check cloud coverage isn't too high

## Next Steps

1. **Collect Field Data**: See `docs/FIELD_DATA_COLLECTION.md`
2. **Train Models**: See `backend/ml_pipeline/README.md`
3. **Deploy to Production**: See `DEPLOYMENT.md`
4. **Set Up LoRa Network**: See `LORA_SETUP.md`

## Support

For issues or questions:
- Check existing documentation in `docs/`
- Review error logs in `backend/*.log`
- Check MongoDB data: `mongo` → `use tobacco_farm` → `db.sensor_data.find().limit(5)`
