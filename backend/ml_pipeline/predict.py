"""
Inference module for yield prediction
Supports both scikit-learn models (from notebook) and PyTorch ST-GNN models
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import os
import json
import joblib

logger = logging.getLogger(__name__)

# Get the base directory for models
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, 'models')


class SklearnYieldPredictor:
    """
    Yield prediction using scikit-learn models trained in the notebook
    """
    
    def __init__(self, model_path: str, scaler_path: str, features_path: str, metadata_path: str = None):
        """
        Initialize predictor with sklearn model
        
        Args:
            model_path: Path to trained model (.pkl)
            scaler_path: Path to fitted scaler (.pkl)
            features_path: Path to feature list (.pkl)
            metadata_path: Path to model metadata (.json)
        """
        logger.info(f"Loading sklearn model from: {model_path}")
        
        # Load model
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        self.model = joblib.load(model_path)
        
        # Load scaler
        if not os.path.exists(scaler_path):
            raise FileNotFoundError(f"Scaler file not found: {scaler_path}")
        self.scaler = joblib.load(scaler_path)
        
        # Load feature columns
        if not os.path.exists(features_path):
            raise FileNotFoundError(f"Features file not found: {features_path}")
        self.feature_columns = joblib.load(features_path)
        
        # Load metadata if available
        self.metadata = {}
        if metadata_path and os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)
        
        # Store config for compatibility
        self.config = {
            'model': {
                'model_type': self.metadata.get('model_type', 'sklearn')
            }
        }
        
        logger.info(f"✓ Sklearn predictor initialized")
        logger.info(f"  - Model type: {self.metadata.get('model_type', 'unknown')}")
        logger.info(f"  - Features: {len(self.feature_columns)}")
        
        # Initialize MongoDB connection
        self._init_mongodb()
    
    def _init_mongodb(self):
        """Initialize MongoDB connection"""
        from pymongo import MongoClient
        
        mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        mongodb_database = os.getenv('MONGODB_DATABASE', 'cropiot')
        
        logger.info(f"Connecting to MongoDB: {mongodb_database}")
        
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[mongodb_database]
        self.sensor_collection = self.db['sensor_data']
    
    def _calculate_features(self, sensor_data: List[Dict]) -> Dict:
        """
        Calculate features from sensor data matching notebook preprocessing
        
        Args:
            sensor_data: List of sensor readings
        
        Returns:
            Dictionary of feature values
        """
        import pandas as pd
        
        if not sensor_data:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(sensor_data)
        
        # Replace error values
        df.replace(-999.0, np.nan, inplace=True)
        
        # Get latest values
        latest = df.iloc[-1]
        
        # Calculate rolling averages (24-hour window)
        temp_rolling = df['temperature'].dropna().tail(24).mean() if 'temperature' in df else latest.get('temperature', 25)
        humidity_rolling = df['humidity'].dropna().tail(24).mean() if 'humidity' in df else latest.get('humidity', 60)
        soil_moisture_rolling = df['soil_moisture'].dropna().tail(24).mean() if 'soil_moisture' in df else latest.get('soil_moisture', 70)
        
        # Calculate std (stability measure)
        temp_std = df['temperature'].dropna().tail(24).std() if 'temperature' in df else 0
        humidity_std = df['humidity'].dropna().tail(24).std() if 'humidity' in df else 0
        
        # Handle NaN std
        temp_std = 0 if pd.isna(temp_std) else temp_std
        humidity_std = 0 if pd.isna(humidity_std) else humidity_std
        
        # Calculate VPD (Vapor Pressure Deficit)
        temp = latest.get('temperature', temp_rolling)
        humidity = latest.get('humidity', humidity_rolling)
        vpd = 0.611 * np.exp((17.502 * temp) / (temp + 240.97)) * (1 - humidity / 100)
        
        # Time features
        now = datetime.now()
        
        # Build feature dictionary matching training features
        features = {
            'soil_moisture': latest.get('soil_moisture', soil_moisture_rolling),
            'ph': latest.get('ph', 6.0),  # Default to optimal if not available
            'temperature': temp,
            'humidity': humidity,
            'temp_rolling_24h': temp_rolling,
            'humidity_rolling_24h': humidity_rolling,
            'soil_moisture_rolling_24h': soil_moisture_rolling,
            'temp_std_24h': temp_std,
            'humidity_std_24h': humidity_std,
            'vpd': vpd,
            'hour': now.hour,
            'day_of_week': now.weekday(),
            'day_of_year': now.timetuple().tm_yday
        }
        
        return features
    
    def predict_sensor(self, sensor_id: str, window_days: int = 7) -> Dict:
        """
        Predict yield for a specific sensor
        
        Args:
            sensor_id: Sensor ID
            window_days: Number of days of history to use
        
        Returns:
            Dictionary with prediction and metadata
        """
        # Load recent data for this sensor
        end_date = datetime.now()
        start_date = end_date - timedelta(days=window_days)
        
        # Query MongoDB
        query = {
            'sensor_id': sensor_id,
            'timestamp': {'$gte': start_date, '$lte': end_date}
        }
        
        cursor = self.sensor_collection.find(query).sort('timestamp', 1)
        sensor_data = list(cursor)
        
        if len(sensor_data) < 1:
            raise ValueError(f"No data found for sensor {sensor_id} in the last {window_days} days")
        
        # Calculate features
        features = self._calculate_features(sensor_data)
        
        if features is None:
            raise ValueError(f"Failed to calculate features for sensor {sensor_id}")
        
        # Create feature array in correct order
        feature_array = []
        for col in self.feature_columns:
            if col in features:
                val = features[col]
                # Handle NaN
                if pd.isna(val) if hasattr(pd, 'isna') else (val != val):
                    val = 0
                feature_array.append(val)
            else:
                feature_array.append(0)
        
        # Need pandas for NaN check
        import pandas as pd
        feature_array = [0 if pd.isna(v) else v for v in feature_array]
        
        # Scale features
        feature_array = np.array(feature_array).reshape(1, -1)
        feature_scaled = self.scaler.transform(feature_array)
        
        # Predict
        yield_kg = self.model.predict(feature_scaled)[0]
        
        # Calculate confidence based on data availability
        data_points = len(sensor_data)
        expected_points = window_days * 24  # Assuming hourly data
        confidence = min(1.0, data_points / expected_points)
        
        # Estimate uncertainty (simple heuristic)
        uncertainty = max(50, 200 * (1 - confidence))
        
        result = {
            'sensor_id': sensor_id,
            'predicted_yield': float(yield_kg),
            'predicted_yield_kg_per_ha': float(yield_kg),
            'confidence': float(confidence),
            'uncertainty': float(uncertainty),
            'prediction_date': datetime.now().isoformat(),
            'window_start': start_date.isoformat(),
            'window_end': end_date.isoformat(),
            'window_days': window_days,
            'data_points_used': data_points,
            'features_used': features
        }
        
        logger.info(f"✓ Prediction for {sensor_id}: {yield_kg:.2f} kg/ha (confidence: {confidence:.2f})")
        
        return result
    
    def predict_all_sensors(self, window_days: int = 7) -> List[Dict]:
        """
        Predict yield for all active sensors
        
        Args:
            window_days: Number of days of history to use
        
        Returns:
            List of predictions for each sensor
        """
        # Get all active sensors
        end_date = datetime.now()
        start_date = end_date - timedelta(days=window_days)
        
        # Get unique sensor IDs with recent data
        pipeline = [
            {'$match': {'timestamp': {'$gte': start_date, '$lte': end_date}}},
            {'$group': {'_id': '$sensor_id'}},
            {'$project': {'sensor_id': '$_id', '_id': 0}}
        ]
        
        sensor_ids = [doc['sensor_id'] for doc in self.sensor_collection.aggregate(pipeline)]
        
        if not sensor_ids:
            logger.warning("No sensors with recent data found")
            return []
        
        logger.info(f"Found {len(sensor_ids)} sensors with recent data")
        
        predictions = []
        for sensor_id in sensor_ids:
            try:
                prediction = self.predict_sensor(sensor_id, window_days)
                predictions.append(prediction)
            except Exception as e:
                logger.error(f"Failed to predict for {sensor_id}: {e}")
                continue
        
        logger.info(f"✓ Generated predictions for {len(predictions)}/{len(sensor_ids)} sensors")
        
        return predictions


# Legacy PyTorch predictor for ST-GNN models
class YieldPredictor:
    """
    Yield prediction inference engine using PyTorch ST-GNN model
    (Legacy - for models trained with train.py)
    """
    
    def __init__(self, model_path: str, scalers_path: str, config: Optional[Dict] = None):
        """
        Initialize predictor
        
        Args:
            model_path: Path to trained model checkpoint
            scalers_path: Path to fitted scalers
            config: Model configuration (if None, loads from checkpoint)
        """
        import torch
        from data_loader import CropDataLoader
        from dataset import CropYieldDataset
        from models import create_model
        from config import get_config
        
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Load checkpoint
        checkpoint = torch.load(model_path, map_location=self.device)
        
        if config is None:
            config = checkpoint['config']
        
        self.config = config
        
        # Create model
        self.model = create_model(config['model']).to(self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        
        # Load data loader with scalers
        self.data_loader = CropDataLoader(
            mongodb_uri=config['mongodb']['uri'],
            database=config['mongodb']['database']
        )
        self.data_loader.load_scalers(scalers_path)
        
        logger.info(f"✓ YieldPredictor initialized")
        logger.info(f"  - Model: {model_path}")
        logger.info(f"  - Device: {self.device}")
    
    def predict_sensor(self, 
                      sensor_id: str,
                      window_days: int = 7,
                      adjacency: Optional[np.ndarray] = None) -> Dict:
        """
        Predict yield for a specific sensor
        """
        import torch
        from dataset import CropYieldDataset
        
        # Load recent data for this sensor
        end_date = datetime.now()
        start_date = end_date - timedelta(days=window_days)
        
        sensor_df = self.data_loader.load_sensor_data(
            start_date=start_date,
            end_date=end_date,
            sensor_ids=[sensor_id]
        )
        
        disease_df = self.data_loader.load_disease_data(
            start_date=start_date,
            end_date=end_date,
            sensor_ids=[sensor_id]
        )
        
        if len(sensor_df) < window_days:
            raise ValueError(f"Insufficient data for sensor {sensor_id}. Need {window_days} days, have {len(sensor_df)}")
        
        # Create time series
        data = self.data_loader.create_time_series(
            sensor_df,
            disease_df,
            window_size=window_days,
            stride=window_days
        )
        
        if data is None or len(data['sensor_ids']) == 0:
            raise ValueError(f"Failed to create time series for sensor {sensor_id}")
        
        # Normalize
        data = self.data_loader.normalize_features(data, fit=False)
        
        # Create dataset
        if adjacency is None:
            adjacency = np.eye(1)
        
        dataset = CropYieldDataset(data, adjacency, yield_targets=None)
        
        # Get features
        sample = dataset[0]
        features = sample['features'].unsqueeze(0).to(self.device)
        adj = sample['adjacency'].to(self.device)
        
        # Reshape for model
        features = features.unsqueeze(2)
        
        # Predict
        with torch.no_grad():
            prediction = self.model(features, adj)
            yield_kg = prediction.item()
        
        data_points = len(sensor_df)
        uncertainty = max(5.0, 20.0 * (1 - min(data_points / window_days, 1.0)))
        confidence = max(0.5, min(1.0, data_points / window_days))
        
        result = {
            'sensor_id': sensor_id,
            'predicted_yield': float(yield_kg),
            'confidence': float(confidence),
            'uncertainty': float(uncertainty),
            'prediction_date': datetime.now().isoformat(),
            'window_start': start_date.isoformat(),
            'window_end': end_date.isoformat(),
            'window_days': window_days,
            'data_points_used': data_points
        }
        
        logger.info(f"✓ Prediction for {sensor_id}: {yield_kg:.2f} kg")
        
        return result
    
    def predict_all_sensors(self, 
                           window_days: int = 7,
                           adjacency: Optional[np.ndarray] = None) -> List[Dict]:
        """
        Predict yield for all active sensors
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=window_days)
        
        sensor_df = self.data_loader.load_sensor_data(
            start_date=start_date,
            end_date=end_date
        )
        
        if len(sensor_df) == 0:
            logger.warning("No sensor data available")
            return []
        
        sensor_ids = sensor_df['sensor_id'].unique()
        
        predictions = []
        for sensor_id in sensor_ids:
            try:
                prediction = self.predict_sensor(sensor_id, window_days, adjacency)
                predictions.append(prediction)
            except Exception as e:
                logger.error(f"Failed to predict for {sensor_id}: {e}")
                continue
        
        logger.info(f"✓ Generated predictions for {len(predictions)}/{len(sensor_ids)} sensors")
        
        return predictions


def create_predictor(model_path: str = None, scalers_path: str = None):
    """
    Factory function to create predictor - automatically detects model type
    
    Supports:
    1. Sklearn models from notebook (yield_predictor.pkl)
    2. PyTorch ST-GNN models (best_model.pt)
    
    Args:
        model_path: Path to model (auto-detected if None)
        scalers_path: Path to scalers (auto-detected if None)
    
    Returns:
        Predictor instance (SklearnYieldPredictor or YieldPredictor)
    """
    # Check for sklearn model first (from notebook)
    sklearn_model_path = os.path.join(MODELS_DIR, 'yield_predictor.pkl')
    sklearn_scaler_path = os.path.join(MODELS_DIR, 'yield_scaler.pkl')
    sklearn_features_path = os.path.join(MODELS_DIR, 'yield_features.pkl')
    sklearn_metadata_path = os.path.join(MODELS_DIR, 'yield_metadata.json')
    
    logger.info(f"Looking for sklearn model at: {sklearn_model_path}")
    
    if os.path.exists(sklearn_model_path):
        logger.info("✓ Found sklearn model (from notebook)")
        return SklearnYieldPredictor(
            model_path=sklearn_model_path,
            scaler_path=sklearn_scaler_path,
            features_path=sklearn_features_path,
            metadata_path=sklearn_metadata_path
        )
    
    # Fall back to PyTorch model
    from config import get_config
    config = get_config()
    
    if model_path is None:
        model_path = os.path.join(config['paths']['models'], 'best_model.pt')
    
    if scalers_path is None:
        scalers_path = config['paths']['scalers']
    
    logger.info(f"Looking for PyTorch model at: {model_path}")
    logger.info(f"Looking for scalers at: {scalers_path}")
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"No model found!\n"
            f"Checked sklearn: {sklearn_model_path}\n"
            f"Checked PyTorch: {model_path}\n"
            f"Please train a model first:\n"
            f"  - Run the notebook: notebooks/train_yield_model.ipynb\n"
            f"  - Or run: python train.py"
        )
    
    if not os.path.exists(scalers_path):
        raise FileNotFoundError(
            f"Scalers file not found at: {scalers_path}\n"
            f"Please train the model first using: python train.py"
        )
    
    logger.info("✓ Found PyTorch model")
    
    return YieldPredictor(model_path, scalers_path, config)


if __name__ == "__main__":
    # Test predictor
    logging.basicConfig(level=logging.INFO)
    
    try:
        predictor = create_predictor()
        
        # Test prediction for all sensors
        predictions = predictor.predict_all_sensors(window_days=7)
        
        print(f"\n✓ Predictions generated:")
        for pred in predictions:
            print(f"  - {pred['sensor_id']}: {pred['predicted_yield']:.2f} kg/ha")
    
    except FileNotFoundError as e:
        print(f"✗ {e}")
    except Exception as e:
        print(f"✗ Prediction failed: {e}")
        import traceback
        traceback.print_exc()
