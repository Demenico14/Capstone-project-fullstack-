"""
Configuration for ST-GNN training
"""

import os
from typing import Dict, Any

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))

# Model configuration
MODEL_CONFIG = {
    'model_type': 'stgnn',  # 'stgnn' or 'stgnn_uncertainty'
    'num_features': 6,      # 4 sensor + 2 disease features
    'num_nodes': 5,         # Number of sensor nodes (update based on your setup)
    'hidden_dim': 64,
    'num_gcn_layers': 2,
    'tcn_channels': [64, 64, 64],
    'kernel_size': 3,
    'dropout': 0.2
}

# Training configuration
TRAIN_CONFIG = {
    'batch_size': 32,
    'num_epochs': 100,
    'learning_rate': 0.001,
    'weight_decay': 1e-5,
    'early_stopping_patience': 10,
    'lr_scheduler': 'cosine',  # 'cosine' or 'step'
    'gradient_clip': 1.0
}

# Data configuration
DATA_CONFIG = {
    'window_size': 3,       # Reduced from 7 to 3 days for sparse data
    'stride': 1,            # Days
    'train_split': 0.8,
    'val_split': 0.1,
    'test_split': 0.1,
    'num_workers': 4
}

# MongoDB configuration
MONGODB_CONFIG = {
    'uri': os.getenv('MONGODB_URI', 'mongodb://192.168.4.2:27017/'),
    'database': os.getenv('MONGODB_DATABASE', 'cropiot')
}

PATHS = {
    'models': os.path.join(CONFIG_DIR, 'models', 'checkpoints'),
    'scalers': os.path.join(CONFIG_DIR, 'models', 'scalers.pkl'),
    'logs': os.path.join(CONFIG_DIR, 'logs'),
    'results': os.path.join(CONFIG_DIR, 'results')
}

# Create directories
for key, path in PATHS.items():
    if key == 'scalers':
        # For file paths, create the parent directory only
        os.makedirs(os.path.dirname(path), exist_ok=True)
    else:
        # For directory paths, create the directory
        os.makedirs(path, exist_ok=True)

def get_config() -> Dict[str, Any]:
    """Get complete configuration"""
    return {
        'model': MODEL_CONFIG,
        'train': TRAIN_CONFIG,
        'data': DATA_CONFIG,
        'mongodb': MONGODB_CONFIG,
        'paths': PATHS
    }
