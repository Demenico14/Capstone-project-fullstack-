# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

CropIoT is an agricultural IoT monitoring system for tobacco farming. It combines real-time sensor data collection, disease detection using computer vision, and yield prediction using machine learning.

## Tech Stack

- **Frontend**: Next.js 15, TypeScript, Tailwind CSS 4, Radix UI components, Leaflet for maps
- **Backend**: Python Flask (three separate microservices)
- **Database**: MongoDB
- **ML/AI**: YOLOv8 (Ultralytics) for disease classification, PyTorch
- **IoT**: ESP8266 with LoRa modules

## Build & Development Commands

### Frontend (Next.js)
```bash
pnpm install          # Install dependencies
pnpm dev              # Start development server (localhost:3000)
pnpm build            # Production build
pnpm lint             # Run ESLint
```

### Backend (Python)
```bash
# Create virtual environment (requires Python 3.11 or 3.12 for PyTorch compatibility)
python3.11 -m venv tobacco
source tobacco/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Start individual services (each in a separate terminal)
python backend/api_server.py     # Sensor API (port 5000)
python backend/app.py            # Disease Detection API (port 8000)
python backend/yield_api.py      # Yield Prediction API (port 9000)
```

### MongoDB
```bash
# Ensure MongoDB is running before starting backend
mongod                            # Start MongoDB
mongo --eval "db.version()"       # Verify MongoDB is running
```

## Architecture

### Backend Microservices

Three Flask servers communicate with a single MongoDB instance (`cropiot` database):

1. **api_server.py (port 5000)**: Main sensor data API
   - Receives data from LoRa sensors via ESP8266 bridge
   - Collections: `sensor_data`, `disease_detections`
   - Endpoints: `/api/latest`, `/api/stats`, `/api/chart-data`, `/api/sensor/{id}`

2. **app.py (port 8000)**: Disease detection service
   - Uses YOLOv8 classification model
   - Model path: `backend/disease_detection/runs/classify/tobacco_disease_classification/weights/best.pt`
   - Endpoints: `/api/detect`, `/api/detect/base64`, `/health`
   - Detects: Cercospora nicotianae, Alternaria alternata, Healthy plants

3. **yield_api.py (port 9000)**: Yield prediction service
   - ML pipeline in `backend/ml_pipeline/`
   - Endpoints: `/api/yield/predict-all`, `/api/yield/model-info`

### Frontend API Client

`lib/api.ts` contains the `ApiClient` class that handles all backend communication with automatic fallback between primary/fallback IP addresses. Uses environment variables:
- `NEXT_PUBLIC_API_URL` (sensor API)
- `NEXT_PUBLIC_DISEASE_API_URL` (disease API)
- `NEXT_PUBLIC_YIELD_API_URL` (yield API)

### IoT Data Flow

```
Field Sensors → ESP8266 LoRa Transmitter → LoRa → ESP8266 WiFi Bridge → HTTP POST → api_server.py → MongoDB
```

- Transmitter code: `esp8266/lora_transmitter/`
- Bridge code: `esp8266/lora_wifi_bridge/`

### ML Pipeline (`backend/ml_pipeline/`)

- `train.py`: Model training
- `predict.py`: Yield predictions
- `data_loader.py`: Data preparation from MongoDB
- `disease_integration.py`: Integrates disease data into yield predictions

### Disease Detection (`backend/disease_detection/`)

- `train_classification.py`: Train YOLOv8 classifier
- `detect.py`: Inference code
- Pre-trained models: `yolov8n-cls.pt`, `yolov8n.pt`

## Environment Configuration

Copy `.env.example` to `.env.local` and configure:
- API URLs and farm coordinates
- MongoDB connection string
- Sentinel Hub credentials (optional, for satellite imagery)

## Key Directories

- `app/`: Next.js pages and API routes
- `components/`: React components (dashboard, analytics, yield, crop-health)
- `lib/`: Utilities, API client, MongoDB connection
- `backend/`: Python microservices and ML code
- `docs/`: Setup guides (MongoDB, Sentinel Hub, Water Balance, etc.)
- `esp8266/`: Arduino code for IoT hardware

## Notes

- PyTorch requires Python 3.11 or 3.12 on macOS with Apple Silicon
- The frontend uses `components/ui/` which contains shadcn/ui components
- Satellite imagery integration uses Sentinel Hub API (requires account)
- Google Earth Engine setup available in `docs/GOOGLE_EARTH_ENGINE_SETUP.md`
