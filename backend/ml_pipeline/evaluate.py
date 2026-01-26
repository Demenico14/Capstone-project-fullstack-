"""
Evaluation script for ST-GNN model
"""

import torch
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import logging
import os
import json
from typing import Dict, List

from train import Trainer
from config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Evaluator:
    """
    Model evaluator with comprehensive metrics and visualizations
    """
    
    def __init__(self, trainer: Trainer):
        self.trainer = trainer
        self.device = trainer.device
        self.model = trainer.model
    
    def evaluate(self, data_loader) -> Dict:
        """
        Evaluate model on dataset
        
        Returns:
            Dictionary of metrics
        """
        self.model.eval()
        
        all_predictions = []
        all_targets = []
        
        with torch.no_grad():
            for batch in data_loader:
                features = batch['features'].to(self.device)
                adjacency = batch['adjacency'].to(self.device)
                targets = batch['target'].to(self.device)
                
                # Reshape
                batch_size, T, F = features.shape
                features = features.unsqueeze(2)
                
                # Predict
                predictions = self.model(features, adjacency)
                
                all_predictions.extend(predictions.squeeze().cpu().numpy())
                all_targets.extend(targets.cpu().numpy())
        
        predictions = np.array(all_predictions)
        targets = np.array(all_targets)
        
        # Compute metrics
        mse = mean_squared_error(targets, predictions)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(targets, predictions)
        r2 = r2_score(targets, predictions)
        
        # Mean Absolute Percentage Error
        mape = np.mean(np.abs((targets - predictions) / (targets + 1e-8))) * 100
        
        metrics = {
            'mse': float(mse),
            'rmse': float(rmse),
            'mae': float(mae),
            'r2': float(r2),
            'mape': float(mape)
        }
        
        logger.info("Evaluation Metrics:")
        logger.info(f"  - RMSE: {rmse:.4f}")
        logger.info(f"  - MAE: {mae:.4f}")
        logger.info(f"  - R²: {r2:.4f}")
        logger.info(f"  - MAPE: {mape:.2f}%")
        
        return metrics, predictions, targets
    
    def plot_predictions(self, predictions: np.ndarray, targets: np.ndarray, save_path: str):
        """Plot predictions vs targets"""
        plt.figure(figsize=(10, 6))
        
        plt.scatter(targets, predictions, alpha=0.5)
        plt.plot([targets.min(), targets.max()], [targets.min(), targets.max()], 'r--', lw=2)
        
        plt.xlabel('True Yield (kg)')
        plt.ylabel('Predicted Yield (kg)')
        plt.title('Yield Predictions vs Ground Truth')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"✓ Predictions plot saved: {save_path}")
    
    def plot_training_history(self, save_path: str):
        """Plot training history"""
        history = self.trainer.history
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
        
        # Loss plot
        ax1.plot(history['train_loss'], label='Train Loss')
        ax1.plot(history['val_loss'], label='Val Loss')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Loss (MSE)')
        ax1.set_title('Training and Validation Loss')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # MAE plot
        ax2.plot(history['train_mae'], label='Train MAE')
        ax2.plot(history['val_mae'], label='Val MAE')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('MAE')
        ax2.set_title('Training and Validation MAE')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"✓ Training history plot saved: {save_path}")
    
    def plot_residuals(self, predictions: np.ndarray, targets: np.ndarray, save_path: str):
        """Plot residuals"""
        residuals = targets - predictions
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
        
        # Residuals vs predictions
        ax1.scatter(predictions, residuals, alpha=0.5)
        ax1.axhline(y=0, color='r', linestyle='--', lw=2)
        ax1.set_xlabel('Predicted Yield (kg)')
        ax1.set_ylabel('Residuals (kg)')
        ax1.set_title('Residual Plot')
        ax1.grid(True, alpha=0.3)
        
        # Residuals histogram
        ax2.hist(residuals, bins=30, edgecolor='black', alpha=0.7)
        ax2.set_xlabel('Residuals (kg)')
        ax2.set_ylabel('Frequency')
        ax2.set_title('Residuals Distribution')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"✓ Residuals plot saved: {save_path}")


def main():
    """Main evaluation function"""
    config = get_config()
    
    logger.info("=" * 60)
    logger.info("ST-GNN Model Evaluation")
    logger.info("=" * 60)
    
    # Create trainer and load best model
    trainer = Trainer(config)
    
    try:
        trainer.load_checkpoint('best_model.pt')
    except FileNotFoundError:
        logger.error("✗ No trained model found. Please run train.py first.")
        return
    
    # Load validation data (you'll need to recreate this)
    # For now, this is a placeholder
    logger.warning("⚠ Evaluation requires validation data loader")
    logger.info("Please modify this script to load your validation data")
    
    # Create evaluator
    evaluator = Evaluator(trainer)
    
    # Plot training history
    history_plot_path = os.path.join(config['paths']['results'], 'training_history.png')
    evaluator.plot_training_history(history_plot_path)
    
    logger.info("\n✓ Evaluation complete!")


if __name__ == "__main__":
    main()
