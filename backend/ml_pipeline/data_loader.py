"""
Data Pipeline for ST-GNN Yield Prediction
Loads and preprocesses data from MongoDB for spatio-temporal graph neural network
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from pymongo import MongoClient
from sklearn.preprocessing import StandardScaler
import pickle
import os

logger = logging.getLogger(__name__)


class CropDataLoader:
    """
    Loads and preprocesses crop data from MongoDB for ST-GNN training
    
    Data sources:
    - sensor_data: IoT sensor readings (soil moisture, temp, humidity, pH)
    - disease_detections: YOLOv8 disease detection results
    - yield_data: Ground truth yield measurements (to be added)
    - satellite_data: NDVI time series (to be added)
    """
    
    def __init__(self, mongodb_uri: str, database: str = 'cropiot'):
        """
        Initialize data loader
        
        Args:
            mongodb_uri: MongoDB connection string
            database: Database name
        """
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[database]
        
        # Collections
        self.sensor_collection = self.db['sensor_data']
        self.disease_collection = self.db['disease_detections']
        self.yield_collection = self.db['yield_records']  # Changed from 'yield_data' to 'yield_records'
        self.satellite_collection = self.db['satellite_data']  # To be created
        
        # Scalers for normalization
        self.sensor_scaler = StandardScaler()
        self.disease_scaler = StandardScaler()
        self.fitted = False
        
        logger.info(f"✓ CropDataLoader initialized with database: {database}")
    
    def load_sensor_data(self, 
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None,
                        sensor_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Load sensor data from MongoDB
        
        Args:
            start_date: Start date for data range
            end_date: End date for data range
            sensor_ids: List of sensor IDs to load (None = all sensors)
        
        Returns:
            DataFrame with columns: [timestamp, sensor_id, soil_moisture, ph, temperature, humidity]
        """
        query = {}
        
        if start_date or end_date:
            query['timestamp'] = {}
            if start_date:
                query['timestamp']['$gte'] = start_date
            if end_date:
                query['timestamp']['$lte'] = end_date
        
        if sensor_ids:
            query['sensor_id'] = {'$in': sensor_ids}
        
        cursor = self.sensor_collection.find(query).sort('timestamp', 1)
        
        data = []
        for doc in cursor:
            data.append({
                'timestamp': doc['timestamp'],
                'sensor_id': doc['sensor_id'],
                'soil_moisture': doc.get('soil_moisture'),
                'ph': doc.get('ph'),
                'temperature': doc.get('temperature'),
                'humidity': doc.get('humidity')
            })
        
        df = pd.DataFrame(data)
        
        if len(df) > 0:
            df = df.ffill().bfill()
            logger.info(f"✓ Loaded {len(df)} sensor readings from {len(df['sensor_id'].unique())} sensors")
        else:
            logger.warning("⚠ No sensor data found for the specified criteria")
        
        return df
    
    def load_disease_data(self,
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None,
                         sensor_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Load disease detection data from MongoDB
        
        Args:
            start_date: Start date for data range
            end_date: End date for data range
            sensor_ids: List of sensor IDs to load
        
        Returns:
            DataFrame with columns: [timestamp, sensor_id, disease_type, confidence, disease_score]
        """
        query = {}
        
        if start_date or end_date:
            query['timestamp'] = {}
            if start_date:
                query['timestamp']['$gte'] = start_date
            if end_date:
                query['timestamp']['$lte'] = end_date
        
        if sensor_ids:
            query['sensor_id'] = {'$in': sensor_ids}
        
        cursor = self.disease_collection.find(query).sort('timestamp', 1)
        
        data = []
        for doc in cursor:
            # Convert disease type to severity score
            disease_type = doc.get('disease_type', '').lower()
            confidence = doc.get('confidence', 0.0)
            
            # Disease severity scoring
            if 'healthy' in disease_type or 'no' in disease_type:
                disease_score = 0.0  # Healthy
            elif 'alternaria' in disease_type:
                disease_score = confidence * 0.6  # Moderate severity
            elif 'cercospora' in disease_type:
                disease_score = confidence * 0.8  # High severity
            else:
                disease_score = confidence * 0.5  # Unknown disease
            
            data.append({
                'timestamp': doc['timestamp'],
                'sensor_id': doc.get('sensor_id', 'unknown'),
                'disease_type': disease_type,
                'confidence': confidence,
                'disease_score': disease_score
            })
        
        df = pd.DataFrame(data)
        
        if len(df) > 0:
            logger.info(f"✓ Loaded {len(df)} disease detections")
        else:
            logger.warning("⚠ No disease data found for the specified criteria")
        
        return df
    
    def load_yield_data(self,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None,
                       sensor_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Load yield ground truth data from MongoDB
        
        Args:
            start_date: Start date for data range
            end_date: End date for data range
            sensor_ids: List of sensor IDs to load
        
        Returns:
            DataFrame with columns: [harvest_date, sensor_id, yield_value, crop_type, unit]
        """
        query = {}
        
        if start_date or end_date:
            query['harvest_date'] = {}
            if start_date:
                query['harvest_date']['$gte'] = start_date
            if end_date:
                query['harvest_date']['$lte'] = end_date
        
        if sensor_ids:
            query['sensor_id'] = {'$in': sensor_ids}
        
        cursor = self.yield_collection.find(query).sort('harvest_date', 1)
        
        data = []
        for doc in cursor:
            data.append({
                'harvest_date': doc['harvest_date'],
                'sensor_id': doc['sensor_id'],
                'yield_value': doc['yield_value'],
                'crop_type': doc.get('crop_type', 'tobacco'),
                'unit': doc.get('unit', 'kg/hectare')
            })
        
        df = pd.DataFrame(data)
        
        if len(df) > 0:
            logger.info(f"✓ Loaded {len(df)} yield records from {len(df['sensor_id'].unique())} sensors")
        else:
            logger.warning("⚠ No yield data found for the specified criteria")
        
        return df
    
    def create_time_series(self,
                          sensor_df: pd.DataFrame,
                          disease_df: pd.DataFrame,
                          window_size: int = 7,
                          stride: int = 1) -> Dict[str, np.ndarray]:
        """
        Create aligned time series windows for ST-GNN training
        
        Args:
            sensor_df: Sensor data DataFrame
            disease_df: Disease data DataFrame
            window_size: Number of days in each window
            stride: Stride between windows (days)
        
        Returns:
            Dictionary containing:
                - sensor_features: (N, T, F_sensor) array
                - disease_features: (N, T, F_disease) array
                - timestamps: (N, T) array of timestamps
                - sensor_ids: (N,) array of sensor IDs
        """
        # Get unique sensors
        sensor_ids = sensor_df['sensor_id'].unique()
        
        all_windows = []
        all_disease_windows = []
        all_timestamps = []
        all_sensor_ids = []
        
        for sensor_id in sensor_ids:
            # Filter data for this sensor
            sensor_data = sensor_df[sensor_df['sensor_id'] == sensor_id].copy()
            disease_data = disease_df[disease_df['sensor_id'] == sensor_id].copy()
            
            if len(sensor_data) < window_size:
                continue
            
            sensor_data = sensor_data.set_index('timestamp')
            # Select only numeric columns for aggregation
            numeric_cols = ['soil_moisture', 'ph', 'temperature', 'humidity']
            sensor_data = sensor_data[numeric_cols].resample('D').mean()
            
            # Create disease score time series (aggregate daily)
            if len(disease_data) > 0:
                disease_data = disease_data.set_index('timestamp')
                disease_daily = disease_data.resample('D').agg({
                    'disease_score': 'max',  # Take worst disease score per day
                    'confidence': 'mean'
                })
            else:
                # No disease data - create zeros
                disease_daily = pd.DataFrame(
                    0.0,
                    index=sensor_data.index,
                    columns=['disease_score', 'confidence']
                )
            
            # Align sensor and disease data
            combined = sensor_data.join(disease_daily, how='left')
            combined = combined.fillna(0.0)  # Fill missing disease scores with 0
            
            # Create sliding windows
            for i in range(0, len(combined) - window_size + 1, stride):
                window = combined.iloc[i:i+window_size]
                
                # Sensor features
                sensor_features = window[['soil_moisture', 'ph', 'temperature', 'humidity']].values
                
                # Disease features
                disease_features = window[['disease_score', 'confidence']].values
                
                # Store window
                all_windows.append(sensor_features)
                all_disease_windows.append(disease_features)
                all_timestamps.append(window.index.values)
                all_sensor_ids.append(sensor_id)
        
        if len(all_windows) == 0:
            logger.error("✗ No valid time series windows created")
            return None
        
        result = {
            'sensor_features': np.array(all_windows),  # (N, T, 4)
            'disease_features': np.array(all_disease_windows),  # (N, T, 2)
            'timestamps': np.array(all_timestamps),  # (N, T)
            'sensor_ids': np.array(all_sensor_ids)  # (N,)
        }
        
        logger.info(f"✓ Created {len(all_windows)} time series windows")
        logger.info(f"  - Sensor features shape: {result['sensor_features'].shape}")
        logger.info(f"  - Disease features shape: {result['disease_features'].shape}")
        
        return result
    
    def normalize_features(self, data: Dict[str, np.ndarray], fit: bool = True) -> Dict[str, np.ndarray]:
        """
        Normalize sensor and disease features
        
        Args:
            data: Dictionary with sensor_features and disease_features
            fit: Whether to fit scalers (True for training, False for inference)
        
        Returns:
            Normalized data dictionary
        """
        sensor_features = data['sensor_features']  # (N, T, F_sensor)
        disease_features = data['disease_features']  # (N, T, F_disease)
        
        N, T, F_sensor = sensor_features.shape
        _, _, F_disease = disease_features.shape
        
        # Reshape for scaling: (N*T, F)
        sensor_flat = sensor_features.reshape(-1, F_sensor)
        disease_flat = disease_features.reshape(-1, F_disease)
        
        if fit:
            # Fit and transform
            sensor_normalized = self.sensor_scaler.fit_transform(sensor_flat)
            disease_normalized = self.disease_scaler.fit_transform(disease_flat)
            self.fitted = True
            logger.info("✓ Fitted and transformed feature scalers")
        else:
            # Transform only
            if not self.fitted:
                raise ValueError("Scalers not fitted. Call with fit=True first.")
            sensor_normalized = self.sensor_scaler.transform(sensor_flat)
            disease_normalized = self.disease_scaler.transform(disease_flat)
        
        # Reshape back: (N, T, F)
        data['sensor_features'] = sensor_normalized.reshape(N, T, F_sensor)
        data['disease_features'] = disease_normalized.reshape(N, T, F_disease)
        
        return data
    
    def save_scalers(self, path: str):
        """Save fitted scalers to disk"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump({
                'sensor_scaler': self.sensor_scaler,
                'disease_scaler': self.disease_scaler
            }, f)
        logger.info(f"✓ Saved scalers to {path}")
    
    def load_scalers(self, path: str):
        """Load fitted scalers from disk"""
        with open(path, 'rb') as f:
            scalers = pickle.load(f)
            self.sensor_scaler = scalers['sensor_scaler']
            self.disease_scaler = scalers['disease_scaler']
            self.fitted = True
        logger.info(f"✓ Loaded scalers from {path}")
    
    def prepare_training_data(self,
                             start_date: datetime,
                             end_date: datetime,
                             window_size: int = 7,
                             stride: int = 1,
                             train_split: float = 0.8) -> Tuple[Dict, Dict]:
        """
        Prepare complete training and validation datasets
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            window_size: Window size in days
            stride: Stride between windows
            train_split: Fraction of data for training
        
        Returns:
            (train_data, val_data) tuple of dictionaries
        """
        logger.info("=" * 60)
        logger.info("Preparing Training Data")
        logger.info("=" * 60)
        
        # Load data
        sensor_df = self.load_sensor_data(start_date, end_date)
        disease_df = self.load_disease_data(start_date, end_date)
        yield_df = self.load_yield_data(start_date, end_date)
        
        if len(sensor_df) == 0:
            raise ValueError("No sensor data available")
        
        if len(yield_df) == 0:
            raise ValueError("No yield data available. Add yield records first using add_yield_data.py")
        
        # Create time series
        data = self.create_time_series(sensor_df, disease_df, window_size, stride)
        
        if data is None:
            raise ValueError("Failed to create time series windows")
        
        logger.info("=" * 60)
        logger.info("Matching Yield Targets to Windows")
        logger.info("=" * 60)
        logger.info(f"Available yield records: {len(yield_df)}")
        if len(yield_df) > 0:
            logger.info(f"Yield date range: {yield_df['harvest_date'].min()} to {yield_df['harvest_date'].max()}")
        
        # For each window, find the closest yield record (within +/- 90 days of window end)
        yield_targets = []
        matched_count = 0
        
        for i, (timestamps, sensor_id) in enumerate(zip(data['timestamps'], data['sensor_ids'])):
            window_start = pd.Timestamp(timestamps[0])
            window_end = pd.Timestamp(timestamps[-1])
            
            # This accounts for the fact that yield is measured at harvest, which could be
            # before or after the monitoring window
            time_window_start = window_end - timedelta(days=90)
            time_window_end = window_end + timedelta(days=90)
            
            # Find yield records for this sensor within the time window
            sensor_yields = yield_df[
                (yield_df['sensor_id'] == sensor_id) & 
                (yield_df['harvest_date'] >= time_window_start) &
                (yield_df['harvest_date'] <= time_window_end)
            ]
            
            if len(sensor_yields) > 0:
                # Use the closest yield record to the window end
                sensor_yields['time_diff'] = abs((sensor_yields['harvest_date'] - window_end).dt.total_seconds())
                closest_yield = sensor_yields.loc[sensor_yields['time_diff'].idxmin(), 'yield_value']
                yield_targets.append(closest_yield)
                matched_count += 1
                
                if i < 3:  # Log first 3 matches for debugging
                    logger.info(f"  Window {i}: {window_start.date()} to {window_end.date()} -> "
                              f"Yield: {closest_yield:.1f} kg/ha (sensor: {sensor_id})")
            else:
                # No yield data for this window - mark as invalid
                yield_targets.append(np.nan)
                if i < 3:  # Log first 3 non-matches for debugging
                    logger.info(f"  Window {i}: {window_start.date()} to {window_end.date()} -> "
                              f"No yield found (sensor: {sensor_id})")
        
        data['yield_targets'] = np.array(yield_targets)
        
        # Remove windows without yield targets
        valid_mask = ~np.isnan(data['yield_targets'])
        for key in data:
            data[key] = data[key][valid_mask]
        
        logger.info(f"✓ Matched {matched_count} windows with yield targets (out of {len(yield_targets)} windows)")
        logger.info("=" * 60)
        
        if matched_count == 0:
            raise ValueError("No windows matched with yield targets. Check that yield harvest dates "
                           "are within 90 days of sensor reading windows.")
        
        # Split into train/val
        N = len(data['sensor_ids'])
        split_idx = int(N * train_split)
        
        train_data = {
            'sensor_features': data['sensor_features'][:split_idx],
            'disease_features': data['disease_features'][:split_idx],
            'timestamps': data['timestamps'][:split_idx],
            'sensor_ids': data['sensor_ids'][:split_idx],
            'yield_targets': data['yield_targets'][:split_idx]  # Added yield targets
        }
        
        val_data = {
            'sensor_features': data['sensor_features'][split_idx:],
            'disease_features': data['disease_features'][split_idx:],
            'timestamps': data['timestamps'][split_idx:],
            'sensor_ids': data['sensor_ids'][split_idx:],
            'yield_targets': data['yield_targets'][split_idx:]  # Added yield targets
        }
        
        # Normalize (fit on training data only)
        train_data = self.normalize_features(train_data, fit=True)
        val_data = self.normalize_features(val_data, fit=False)
        
        logger.info(f"✓ Training samples: {len(train_data['sensor_ids'])}")
        logger.info(f"✓ Validation samples: {len(val_data['sensor_ids'])}")
        logger.info("=" * 60)
        
        return train_data, val_data


if __name__ == "__main__":
    # Test the data loader
    logging.basicConfig(level=logging.INFO)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://192.168.1.230:27017/')
    
    loader = CropDataLoader(mongodb_uri)
    
    # Test loading data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    try:
        train_data, val_data = loader.prepare_training_data(
            start_date=start_date,
            end_date=end_date,
            window_size=7,
            stride=1
        )
        
        print("\n✓ Data pipeline test successful!")
        print(f"  Training samples: {len(train_data['sensor_ids'])}")
        print(f"  Validation samples: {len(val_data['sensor_ids'])}")
        
    except Exception as e:
        print(f"\n✗ Data pipeline test failed: {e}")
