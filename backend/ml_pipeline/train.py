"""
Training script for ST-GNN crop yield prediction model
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import numpy as np
from datetime import datetime, timedelta
import logging
import os
import json
from tqdm import tqdm
from typing import Dict, Tuple

from data_loader import CropDataLoader
from dataset import CropYieldDataset, SpatialGraphBuilder
from models import create_model
from config import get_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Trainer:
    """
    Trainer for ST-GNN model
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Create model
        self.model = create_model(config['model']).to(self.device)
        
        # Optimizer
        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=config['train']['learning_rate'],
            weight_decay=config['train']['weight_decay']
        )
        
        # Learning rate scheduler
        if config['train']['lr_scheduler'] == 'cosine':
            self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer,
                T_max=config['train']['num_epochs']
            )
        elif config['train']['lr_scheduler'] == 'step':
            self.scheduler = optim.lr_scheduler.StepLR(
                self.optimizer,
                step_size=20,
                gamma=0.5
            )
        else:
            self.scheduler = None
        
        # Loss function
        self.criterion = nn.MSELoss()
        
        # Training history
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'train_mae': [],
            'val_mae': []
        }
        
        # Best model tracking
        self.best_val_loss = float('inf')
        self.patience_counter = 0
        
        logger.info(f"✓ Trainer initialized on device: {self.device}")
        logger.info(f"  - Model parameters: {sum(p.numel() for p in self.model.parameters()):,}")
    
    def train_epoch(self, train_loader: DataLoader) -> Tuple[float, float]:
        """Train for one epoch"""
        self.model.train()
        total_loss = 0.0
        total_mae = 0.0
        num_batches = 0
        
        pbar = tqdm(train_loader, desc='Training')
        for batch in pbar:
            # Move to device
            features = batch['features'].to(self.device)
            adjacency = batch['adjacency'].to(self.device)
            targets = batch['target'].to(self.device)
            
            # Reshape features for ST-GNN
            # From (batch, T, F) to (batch, T, num_nodes, F)
            # For now, treat each sample as single node
            batch_size, T, F = features.shape
            features = features.unsqueeze(2)  # (batch, T, 1, F)
            
            # Forward pass
            self.optimizer.zero_grad()
            predictions = self.model(features, adjacency)
            
            # Compute loss
            loss = self.criterion(predictions.squeeze(), targets)
            
            # Backward pass
            loss.backward()
            
            # Gradient clipping
            if self.config['train']['gradient_clip'] > 0:
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(),
                    self.config['train']['gradient_clip']
                )
            
            self.optimizer.step()
            
            # Metrics
            mae = torch.abs(predictions.squeeze() - targets).mean()
            
            total_loss += loss.item()
            total_mae += mae.item()
            num_batches += 1
            
            pbar.set_postfix({
                'loss': f'{loss.item():.4f}',
                'mae': f'{mae.item():.4f}'
            })
        
        avg_loss = total_loss / num_batches
        avg_mae = total_mae / num_batches
        
        return avg_loss, avg_mae
    
    def validate(self, val_loader: DataLoader) -> Tuple[float, float]:
        """Validate model"""
        self.model.eval()
        total_loss = 0.0
        total_mae = 0.0
        num_batches = 0
        
        with torch.no_grad():
            for batch in val_loader:
                features = batch['features'].to(self.device)
                adjacency = batch['adjacency'].to(self.device)
                targets = batch['target'].to(self.device)
                
                # Reshape
                batch_size, T, F = features.shape
                features = features.unsqueeze(2)
                
                # Forward pass
                predictions = self.model(features, adjacency)
                
                # Compute loss
                loss = self.criterion(predictions.squeeze(), targets)
                mae = torch.abs(predictions.squeeze() - targets).mean()
                
                total_loss += loss.item()
                total_mae += mae.item()
                num_batches += 1
        
        avg_loss = total_loss / num_batches
        avg_mae = total_mae / num_batches
        
        return avg_loss, avg_mae
    
    def train(self, train_loader: DataLoader, val_loader: DataLoader):
        """Full training loop"""
        logger.info("=" * 60)
        logger.info("Starting Training")
        logger.info("=" * 60)
        
        num_epochs = self.config['train']['num_epochs']
        patience = self.config['train']['early_stopping_patience']
        
        for epoch in range(num_epochs):
            logger.info(f"\nEpoch {epoch+1}/{num_epochs}")
            
            # Train
            train_loss, train_mae = self.train_epoch(train_loader)
            
            # Validate
            val_loss, val_mae = self.validate(val_loader)
            
            # Update scheduler
            if self.scheduler is not None:
                self.scheduler.step()
            
            # Log metrics
            logger.info(f"  Train Loss: {train_loss:.4f} | Train MAE: {train_mae:.4f}")
            logger.info(f"  Val Loss: {val_loss:.4f} | Val MAE: {val_mae:.4f}")
            
            # Save history
            self.history['train_loss'].append(train_loss)
            self.history['val_loss'].append(val_loss)
            self.history['train_mae'].append(train_mae)
            self.history['val_mae'].append(val_mae)
            
            # Check for improvement
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.patience_counter = 0
                self.save_checkpoint('best_model.pt')
                logger.info(f"  ✓ New best model saved (val_loss: {val_loss:.4f})")
            else:
                self.patience_counter += 1
                logger.info(f"  No improvement ({self.patience_counter}/{patience})")
            
            # Early stopping
            if self.patience_counter >= patience:
                logger.info(f"\n✓ Early stopping triggered after {epoch+1} epochs")
                break
        
        logger.info("=" * 60)
        logger.info("Training Complete")
        logger.info(f"Best Val Loss: {self.best_val_loss:.4f}")
        logger.info("=" * 60)
        
        # Save final model
        self.save_checkpoint('final_model.pt')
        self.save_history()
    
    def save_checkpoint(self, filename: str):
        """Save model checkpoint"""
        checkpoint_path = os.path.join(self.config['paths']['models'], filename)
        
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'config': self.config,
            'history': self.history,
            'best_val_loss': self.best_val_loss
        }, checkpoint_path)
        
        logger.info(f"  Checkpoint saved: {checkpoint_path}")
    
    def load_checkpoint(self, filename: str):
        """Load model checkpoint"""
        checkpoint_path = os.path.join(self.config['paths']['models'], filename)
        
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.history = checkpoint['history']
        self.best_val_loss = checkpoint['best_val_loss']
        
        logger.info(f"✓ Checkpoint loaded: {checkpoint_path}")
    
    def save_history(self):
        """Save training history"""
        history_path = os.path.join(self.config['paths']['results'], 'training_history.json')
        
        with open(history_path, 'w') as f:
            json.dump(self.history, f, indent=2)
        
        logger.info(f"✓ Training history saved: {history_path}")


def main():
    """Main training function"""
    # Load configuration
    config = get_config()
    
    logger.info("=" * 60)
    logger.info("ST-GNN Crop Yield Prediction Training")
    logger.info("=" * 60)
    
    # Initialize data loader
    data_loader = CropDataLoader(
        mongodb_uri=config['mongodb']['uri'],
        database=config['mongodb']['database']
    )
    
    # Prepare data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # 90 days of data
    
    logger.info(f"Loading data from {start_date.date()} to {end_date.date()}")
    
    try:
        train_data, val_data = data_loader.prepare_training_data(
            start_date=start_date,
            end_date=end_date,
            window_size=config['data']['window_size'],
            stride=config['data']['stride'],
            train_split=config['data']['train_split']
        )
    except Exception as e:
        logger.error(f"✗ Failed to load data: {e}")
        logger.error("Please ensure you have sensor data in MongoDB")
        return
    
    # Save scalers
    data_loader.save_scalers(config['paths']['scalers'])
    
    # Create dummy yield targets (replace with real data)
    logger.warning("⚠ Using dummy yield targets - replace with real ground truth data")
    train_targets = np.random.rand(len(train_data['sensor_ids'])) * 100  # kg
    val_targets = np.random.rand(len(val_data['sensor_ids'])) * 100
    
    # Build spatial graph (dummy - replace with real sensor locations)
    logger.warning("⚠ Using identity adjacency matrix - provide real sensor locations")
    unique_sensors = np.unique(train_data['sensor_ids'])
    adjacency = np.eye(len(unique_sensors))
    
    # Create datasets
    train_dataset = CropYieldDataset(train_data, adjacency, train_targets)
    val_dataset = CropYieldDataset(val_data, adjacency, val_targets)
    
    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=config['train']['batch_size'],
        shuffle=True,
        num_workers=config['data']['num_workers']
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=config['train']['batch_size'],
        shuffle=False,
        num_workers=config['data']['num_workers']
    )
    
    # Update model config with actual values
    config['model']['num_features'] = train_dataset.F
    config['model']['num_nodes'] = len(unique_sensors)
    
    # Create trainer
    trainer = Trainer(config)
    
    # Train model
    trainer.train(train_loader, val_loader)
    
    logger.info("\n✓ Training complete!")
    logger.info(f"  - Best model: {config['paths']['models']}/best_model.pt")
    logger.info(f"  - Training history: {config['paths']['results']}/training_history.json")


if __name__ == "__main__":
    main()
