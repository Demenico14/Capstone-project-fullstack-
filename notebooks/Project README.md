# Yield Prediction Training Notebook

## Overview

This notebook trains a machine learning model to predict tobacco yield based on environmental sensor data collected from your IoT system.

## Prerequisites

```bash
pip install pandas numpy matplotlib seaborn scikit-learn joblib
```

## Usage

1. Open the notebook in Jupyter:
   ```bash
   jupyter notebook train_yield_model.ipynb
   ```

2. Run all cells to:
   - Load and preprocess sensor data
   - Generate simulated yield data based on optimal growing conditions
   - Engineer features from environmental data
   - Train multiple ML models (Random Forest & Gradient Boosting)
   - Evaluate and compare models
   - Save the best model for deployment

## Important Note

Since this is your first growing season, the notebook generates **simulated yield data** based on agricultural research about optimal tobacco growing conditions. This allows you to:
- Develop and test the prediction pipeline
- Understand feature importance
- Establish a baseline model

**You MUST retrain the model with actual yield data** once you harvest your crop. The simulated data is only for initial development.

## Outputs

The notebook saves:
- `backend/ml_pipeline/models/yield_predictor.pkl` - Trained model
- `backend/ml_pipeline/models/yield_scaler.pkl` - Feature scaler
- `backend/ml_pipeline/models/yield_features.pkl` - Feature list
- `backend/ml_pipeline/models/yield_metadata.json` - Model metadata

## Retraining with Actual Data

When you have actual yield measurements:

1. Create a CSV with columns: `sensor_id`, `timestamp`, and `actual_yield_kg_per_ha`
2. Modify Section 4 of the notebook to load your actual yield data instead of simulating it
3. Re-run the entire notebook
4. The updated model will be saved automatically

## Model Performance

The model uses environmental factors to predict yield:
- Temperature and stability
- Humidity levels
- Soil moisture
- pH levels
- Vapor Pressure Deficit (VPD)

Expected accuracy with simulated data: R² > 0.85
Expected accuracy with real data: Will vary, aim for R² > 0.70
