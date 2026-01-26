# ST-GNN Yield Prediction Setup Guide

Complete guide to setting up and using the Spatio-Temporal Graph Neural Network for tobacco yield prediction.

## What You Need

### 1. Data Requirements

**Spatial Data (Graph Structure)**
- Sensor locations (latitude/longitude) - Already configured in your system
- Spatial relationships between sensors (automatically computed based on distance)

**Temporal Data (Time Series)**
- Soil moisture, temperature, humidity from IoT sensors
- NDVI and vegetation indices from satellite imagery
- Disease detection history
- Weather data (rainfall, temperature)

**Target Data (Ground Truth)**
- Historical harvest yields (kg/hectare) for each sensor location
- You can input this through the web interface

### 2. System Architecture

\`\`\`
┌─────────────────────────────────────────────────────────────┐
│                    ST-GNN Yield Prediction                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Spatial    │    │   Temporal   │    │   Fusion &   │  │
│  │     GCN      │───▶│     TCN      │───▶│  Prediction  │  │
│  │  (Sensors)   │    │ (Time Series)│    │    Head      │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                    │                    │          │
│         ▼                    ▼                    ▼          │
│  Sensor Graph         Temporal Patterns      Yield Output   │
│  Relationships        (7-30 days)            (kg/hectare)   │
└─────────────────────────────────────────────────────────────┘
\`\`\`

## Quick Start

### Step 1: Add Your Expected Yield Data

Since you don't have historical harvest data yet, you can:

1. **Input Expected Yields**: Go to Yield Prediction → Training Data tab
2. **Add Records**: For each sensor location, add your expected yield per hectare
3. **Example Values for Tobacco**:
   - Good conditions: 2800-3200 kg/hectare
   - Average conditions: 2400-2800 kg/hectare
   - Poor conditions: 1800-2400 kg/hectare

### Step 2: Collect Sensor Data

The system automatically collects:
- Soil moisture, temperature, humidity from your LoRa sensors
- NDVI and vegetation indices from Sentinel Hub/Google Earth Engine
- Disease detection results from your ML model

**Minimum Data Required**: 7-14 days of continuous sensor readings

### Step 3: Train the Model

\`\`\`bash
# Navigate to backend directory
cd backend/ml_pipeline

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Train the model
python train.py
\`\`\`

The training script will:
- Fetch sensor data from MongoDB
- Fetch yield records you entered
- Create spatial graph based on sensor locations
- Build temporal sequences (time windows)
- Train the ST-GNN model
- Save the trained model to `models/st_gnn_model.pth`

### Step 4: Start the Yield API

\`\`\`bash
# From backend directory
bash start_yield_api.sh

# Or manually:
python yield_api.py
\`\`\`

The API will run on `http://192.168.4.2:9000`

### Step 5: View Predictions

1. Go to the Yield Prediction page in your web app
2. View predictions for each sensor location
3. See confidence intervals and uncertainty estimates

## How It Works

### Graph Construction

The system automatically creates a spatial graph:

\`\`\`python
# Example: 3 sensors
Sensor_1 ←→ Sensor_2 ←→ Sensor_3
    ↓           ↓           ↓
  (lat,lng)  (lat,lng)  (lat,lng)
\`\`\`

Edges are created between sensors based on:
- Physical proximity (distance threshold)
- Shared field characteristics

### Feature Engineering

For each sensor at each timestep, the model uses:

1. **Sensor Features** (4 features):
   - Soil moisture (%)
   - Temperature (°C)
   - Humidity (%)
   - pH level

2. **Satellite Features** (2 features):
   - NDVI (vegetation index)
   - Soil moisture index

3. **Disease Features** (1 feature):
   - Disease detection count (last 7 days)

**Total**: 7 features per sensor per timestep

### Temporal Windows

The model looks at historical data:
- Default window: 7 days
- Configurable: 7-30 days
- Daily aggregation of sensor readings

### Prediction Output

For each sensor location:
- **Mean yield**: Expected harvest (kg/hectare)
- **Uncertainty**: Confidence in the prediction
- **Confidence interval**: 95% range (lower, upper bounds)

## Adding Real Harvest Data

As you harvest your tobacco crop:

1. **Record Actual Yields**:
   - Go to Yield Prediction → Training Data
   - Add harvest date, sensor location, and actual yield
   - Include notes about conditions

2. **Retrain the Model**:
   \`\`\`bash
   python backend/ml_pipeline/train.py
   \`\`\`

3. **Improved Predictions**:
   - More data = better accuracy
   - Model learns from your specific farm conditions
   - Adapts to local climate and soil patterns

## Model Performance

The model tracks these metrics:

- **MAE** (Mean Absolute Error): Average prediction error in kg/hectare
- **RMSE** (Root Mean Square Error): Penalizes large errors
- **R²** (R-squared): How well the model explains variance (0-1, higher is better)

**Target Performance**:
- MAE < 200 kg/hectare (< 7% error for 2800 kg/hectare yield)
- R² > 0.7 (explains 70%+ of variance)

## Troubleshooting

### "Model not loaded" Error

**Solution**: Train the model first
\`\`\`bash
cd backend/ml_pipeline
python train.py
\`\`\`

### "Not enough data" Error

**Solution**: Collect more sensor readings
- Minimum: 7 days of data
- Recommended: 14+ days for better accuracy

### Low Prediction Confidence

**Causes**:
- Limited training data
- High variability in sensor readings
- Missing satellite imagery

**Solutions**:
- Add more historical yield records
- Ensure sensors are reporting consistently
- Check satellite API connectivity

### Predictions Don't Match Reality

**Solutions**:
1. Add actual harvest data to training set
2. Retrain model with real yields
3. Increase temporal window (use more days of history)
4. Check sensor calibration

## Advanced Configuration

Edit `backend/ml_pipeline/config.py`:

\`\`\`python
# Model architecture
MODEL_CONFIG = {
    'hidden_dim': 64,        # Increase for more capacity
    'num_gcn_layers': 2,     # More layers = deeper spatial understanding
    'tcn_channels': [64, 64, 64],  # Temporal feature extraction
    'dropout': 0.2,          # Regularization
}

# Training parameters
TRAINING_CONFIG = {
    'batch_size': 16,
    'learning_rate': 0.001,
    'num_epochs': 100,
    'early_stopping_patience': 15,
}

# Data parameters
DATA_CONFIG = {
    'temporal_window': 7,    # Days of history to use
    'spatial_threshold': 500, # Meters for sensor connections
}
\`\`\`

## Best Practices

1. **Regular Data Collection**:
   - Ensure sensors report every hour
   - Check for missing data gaps
   - Validate sensor readings

2. **Seasonal Training**:
   - Retrain model each growing season
   - Use previous season's data
   - Account for weather variations

3. **Continuous Improvement**:
   - Add harvest data immediately after collection
   - Retrain model with new data
   - Monitor prediction accuracy

4. **Data Quality**:
   - Remove outliers (sensor malfunctions)
   - Fill missing values appropriately
   - Validate satellite imagery availability

## Next Steps

1. **Add Your First Yield Records**: Input expected yields for your sensors
2. **Collect 7-14 Days of Data**: Let sensors gather environmental data
3. **Train the Model**: Run the training script
4. **Monitor Predictions**: Check daily yield forecasts
5. **Record Actual Harvests**: Add real yields as you harvest
6. **Retrain Periodically**: Improve accuracy with real data

## Support

For issues or questions:
- Check logs: `backend/ml_pipeline/logs/`
- Review training history: `backend/ml_pipeline/results/training_history.json`
- Test model: `python backend/ml_pipeline/predict.py`
