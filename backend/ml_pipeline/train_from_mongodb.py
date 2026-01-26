"""
Training script that fetches data from MongoDB
Integrates with web interface for automated training
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from datetime import datetime, timedelta
import logging
import os
import json
import sys
from pathlib import Path
from typing import Dict, Tuple, Optional
import pymongo
from tqdm import tqdm

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.st_gnn import create_model

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MongoDBTrainer:
    """
    Trainer that fetches data from MongoDB and trains ST-GNN model
    """
    
    def __init__(self, mongodb_uri: str, database: str = "cropiot"):
        self.mongodb_uri = mongodb_uri
        self.database = database
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Connect to MongoDB
        self.client = pymongo.MongoClient(mongodb_uri)
        self.db = self.client[database]
        
        # Training status file
        self.status_file = Path(__file__).parent / "training_status.json"
        
        logger.info(f"✓ Connected to MongoDB: {database}")
        logger.info(f"✓ Device: {self.device}")
    
    def update_status(self, status: str, progress: float = 0, message: str = ""):
        """Update training status"""
        status_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(self.status_file, 'w') as f:
            json.dump(status_data, f, indent=2)
        
        logger.info(f"Status: {status} ({progress}%) - {message}")
    
    def fetch_sensor_data(self, days: int = 30) -> Dict:
        """Fetch sensor data from MongoDB"""
        self.update_status("running", 10, "Fetching sensor data from MongoDB...")
        
        # Get sensor readings from last N days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        readings = list(self.db.sensor_readings.find({
            "timestamp": {"$gte": start_date, "$lte": end_date}
        }).sort("timestamp", 1))
        
        logger.info(f"✓ Fetched {len(readings)} sensor readings")
        
        if len(readings) == 0:
            raise ValueError("No sensor data found in MongoDB")
        
        return readings
    
    def fetch_yield_data(self) -> Dict:
        """Fetch yield records from MongoDB"""
        self.update_status("running", 20, "Fetching yield records...")
        
        yield_records = list(self.db.yield_data.find().sort("harvest_date", -1))
        
        logger.info(f"✓ Fetched {len(yield_records)} yield records")
        
        if len(yield_records) == 0:
            raise ValueError("No yield data found. Please add harvest records first.")
        
        return yield_records
    
    def prepare_training_data(self, sensor_data: list, yield_data: list, window_days: int = 7) -> Tuple:
        """Prepare training data from MongoDB records"""
        self.update_status("running", 30, "Preparing training data...")
        
        # Group sensor data by sensor_id and date
        sensor_dict = {}
        for reading in sensor_data:
            sensor_id = reading['sensor_id']
            date = reading['timestamp'].date()
            
            if sensor_id not in sensor_dict:
                sensor_dict[sensor_id] = {}
            
            if date not in sensor_dict[sensor_id]:
                sensor_dict[sensor_id][date] = []
            
            sensor_dict[sensor_id][date].append(reading)
        
        # Create training samples
        X_list = []
        y_list = []
        sensor_ids = []
        
        for yield_record in yield_data:
            sensor_id = yield_record['sensor_id']
            harvest_date = yield_record['harvest_date']
            actual_yield = yield_record['actual_yield']
            
            # Get sensor readings for window_days before harvest
            end_date = harvest_date.date() if isinstance(harvest_date, datetime) else harvest_date
            start_date = end_date - timedelta(days=window_days)
            
            # Collect features for this window
            features = []
            for day_offset in range(window_days):
                current_date = start_date + timedelta(days=day_offset)
                
                if sensor_id in sensor_dict and current_date in sensor_dict[sensor_id]:
                    # Average readings for this day
                    day_readings = sensor_dict[sensor_id][current_date]
                    
                    soil_moisture = np.mean([r.get('soil_moisture', 0) for r in day_readings])
                    temperature = np.mean([r.get('temperature', 0) for r in day_readings])
                    humidity = np.mean([r.get('humidity', 0) for r in day_readings])
                    ndvi = np.mean([r.get('ndvi', 0.5) for r in day_readings])
                    disease = max([r.get('disease_detected', 0) for r in day_readings])
                    disease_conf = max([r.get('disease_confidence', 0) for r in day_readings])
                    
                    features.append([soil_moisture, temperature, humidity, ndvi, disease, disease_conf])
                else:
                    # Missing data - use zeros or interpolate
                    features.append([0, 0, 0, 0.5, 0, 0])
            
            if len(features) == window_days:
                X_list.append(features)
                y_list.append(actual_yield)
                sensor_ids.append(sensor_id)
        
        X = np.array(X_list, dtype=np.float32)  # (N, T, F)
        y = np.array(y_list, dtype=np.float32)  # (N,)
        
        logger.info(f"✓ Prepared {len(X)} training samples")
        logger.info(f"  - Shape: {X.shape}")
        logger.info(f"  - Features: soil_moisture, temperature, humidity, ndvi, disease, disease_confidence")
        
        # Normalize features
        self.feature_mean = X.mean(axis=(0, 1))
        self.feature_std = X.std(axis=(0, 1)) + 1e-8
        X = (X - self.feature_mean) / self.feature_std
        
        # Normalize targets
        self.target_mean = y.mean()
        self.target_std = y.std() + 1e-8
        y = (y - self.target_mean) / self.target_std
        
        # Split train/val
        split_idx = int(0.8 * len(X))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        return X_train, y_train, X_val, y_val, sensor_ids
    
    def create_adjacency_matrix(self, sensor_ids: list) -> np.ndarray:
        """Create adjacency matrix from sensor locations"""
        # Get unique sensors
        unique_sensors = list(set(sensor_ids))
        n = len(unique_sensors)
        
        # For now, use identity matrix (each sensor is independent)
        # TODO: Calculate based on actual sensor distances
        adjacency = np.eye(n, dtype=np.float32)
        
        logger.info(f"✓ Created adjacency matrix: {adjacency.shape}")
        
        return adjacency
    
    def train_model(self, X_train, y_train, X_val, y_val, adjacency, num_epochs: int = 50):
        """Train the ST-GNN model"""
        self.update_status("running", 40, "Initializing model...")
        
        # Model configuration
        config = {
            'num_features': X_train.shape[2],  # 6 features
            'num_nodes': 1,  # Treat each sample as single node
            'hidden_dim': 64,
            'num_gcn_layers': 2,
            'tcn_channels': [64, 64, 64],
            'kernel_size': 3,
            'dropout': 0.2
        }
        
        # Create model
        model = create_model(config).to(self.device)
        
        # Optimizer and loss
        optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-5)
        criterion = nn.MSELoss()
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs)
        
        # Convert to tensors
        X_train_t = torch.FloatTensor(X_train).unsqueeze(2)  # (N, T, 1, F)
        y_train_t = torch.FloatTensor(y_train)
        X_val_t = torch.FloatTensor(X_val).unsqueeze(2)
        y_val_t = torch.FloatTensor(y_val)
        adj_t = torch.FloatTensor(adjacency).to(self.device)
        
        # Create data loaders
        train_dataset = TensorDataset(X_train_t, y_train_t)
        val_dataset = TensorDataset(X_val_t, y_val_t)
        
        train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False)
        
        # Training history
        history = {
            'train_loss': [],
            'val_loss': [],
            'train_mae': [],
            'val_mae': []
        }
        
        best_val_loss = float('inf')
        patience = 10
        patience_counter = 0
        
        logger.info(f"✓ Starting training for {num_epochs} epochs...")
        
        for epoch in range(num_epochs):
            # Training
            model.train()
            train_loss = 0
            train_mae = 0
            
            for X_batch, y_batch in train_loader:
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device)
                
                optimizer.zero_grad()
                predictions = model(X_batch, adj_t).squeeze()
                
                loss = criterion(predictions, y_batch)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
                train_mae += torch.abs(predictions - y_batch).mean().item()
            
            train_loss /= len(train_loader)
            train_mae /= len(train_loader)
            
            # Validation
            model.eval()
            val_loss = 0
            val_mae = 0
            
            with torch.no_grad():
                for X_batch, y_batch in val_loader:
                    X_batch = X_batch.to(self.device)
                    y_batch = y_batch.to(self.device)
                    
                    predictions = model(X_batch, adj_t).squeeze()
                    loss = criterion(predictions, y_batch)
                    
                    val_loss += loss.item()
                    val_mae += torch.abs(predictions - y_batch).mean().item()
            
            val_loss /= len(val_loader)
            val_mae /= len(val_loader)
            
            # Update scheduler
            scheduler.step()
            
            # Save history
            history['train_loss'].append(train_loss)
            history['val_loss'].append(val_loss)
            history['train_mae'].append(train_mae)
            history['val_mae'].append(val_mae)
            
            # Update progress
            progress = 40 + int((epoch + 1) / num_epochs * 50)
            self.update_status("running", progress, f"Epoch {epoch+1}/{num_epochs} - Val Loss: {val_loss:.4f}")
            
            logger.info(f"Epoch {epoch+1}/{num_epochs} - Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")
            
            # Save best model
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                self.save_model(model, config, history)
            else:
                patience_counter += 1
            
            # Early stopping
            if patience_counter >= patience:
                logger.info(f"✓ Early stopping at epoch {epoch+1}")
                break
        
        logger.info(f"✓ Training complete! Best val loss: {best_val_loss:.4f}")
        
        return model, history
    
    def save_model(self, model, config, history):
        """Save trained model"""
        models_dir = Path(__file__).parent / "models" / "saved"
        models_dir.mkdir(parents=True, exist_ok=True)
        
        model_path = models_dir / "best_model.pt"
        
        # Save normalization parameters
        normalization = {
            'feature_mean': self.feature_mean.tolist(),
            'feature_std': self.feature_std.tolist(),
            'target_mean': float(self.target_mean),
            'target_std': float(self.target_std)
        }
        
        torch.save({
            'model_state_dict': model.state_dict(),
            'config': config,
            'normalization': normalization,
            'history': history,
            'timestamp': datetime.now().isoformat()
        }, model_path)
        
        logger.info(f"✓ Model saved: {model_path}")
        
        # Save history
        history_path = Path(__file__).parent / "results" / "training_history.json"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(history_path, 'w') as f:
            json.dump(history, f, indent=2)
    
    def train(self, window_days: int = 7, num_epochs: int = 50):
        """Main training pipeline"""
        try:
            self.update_status("running", 0, "Starting training...")
            
            # Fetch data
            sensor_data = self.fetch_sensor_data(days=90)
            yield_data = self.fetch_yield_data()
            
            # Prepare training data
            X_train, y_train, X_val, y_val, sensor_ids = self.prepare_training_data(
                sensor_data, yield_data, window_days
            )
            
            # Create adjacency matrix
            adjacency = self.create_adjacency_matrix(sensor_ids)
            
            # Train model
            model, history = self.train_model(X_train, y_train, X_val, y_val, adjacency, num_epochs)
            
            self.update_status("completed", 100, "Training completed successfully!")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Training failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.update_status("failed", 0, f"Training failed: {str(e)}")
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train ST-GNN model from MongoDB data')
    parser.add_argument('--mongodb-uri', type=str, required=True, help='MongoDB connection URI')
    parser.add_argument('--database', type=str, default='cropiot', help='Database name')
    parser.add_argument('--window-days', type=int, default=7, help='Time window in days')
    parser.add_argument('--epochs', type=int, default=50, help='Number of training epochs')
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("ST-GNN Training from MongoDB")
    logger.info("=" * 60)
    
    trainer = MongoDBTrainer(args.mongodb_uri, args.database)
    success = trainer.train(window_days=args.window_days, num_epochs=args.epochs)
    
    if success:
        logger.info("\n✓ Training completed successfully!")
        sys.exit(0)
    else:
        logger.error("\n✗ Training failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
