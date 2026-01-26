"""
PyTorch Dataset classes for ST-GNN training
"""

import torch
from torch.utils.data import Dataset
import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CropYieldDataset(Dataset):
    """
    PyTorch Dataset for crop yield prediction with ST-GNN
    
    Features:
    - Sensor time series (soil moisture, pH, temperature, humidity)
    - Disease scores from YOLOv8
    - Spatial graph structure (sensor locations)
    - Temporal sequences
    """
    
    def __init__(self,
                 data: Dict[str, np.ndarray],
                 adjacency_matrix: Optional[np.ndarray] = None,
                 yield_targets: Optional[np.ndarray] = None):
        """
        Initialize dataset
        
        Args:
            data: Dictionary with sensor_features, disease_features, timestamps, sensor_ids
            adjacency_matrix: (N_sensors, N_sensors) spatial adjacency matrix
            yield_targets: (N,) array of yield values (optional, for training)
        """
        self.sensor_features = torch.FloatTensor(data['sensor_features'])  # (N, T, F_sensor)
        self.disease_features = torch.FloatTensor(data['disease_features'])  # (N, T, F_disease)
        self.timestamps = data['timestamps']
        self.sensor_ids = data['sensor_ids']
        
        # Combine sensor and disease features
        self.features = torch.cat([self.sensor_features, self.disease_features], dim=-1)  # (N, T, F_total)
        
        self.N, self.T, self.F = self.features.shape
        
        # Adjacency matrix (if not provided, create identity - no spatial connections)
        if adjacency_matrix is not None:
            self.adjacency = torch.FloatTensor(adjacency_matrix)
        else:
            # Create identity matrix (each sensor only connected to itself)
            unique_sensors = np.unique(self.sensor_ids)
            n_sensors = len(unique_sensors)
            self.adjacency = torch.eye(n_sensors)
            logger.warning("⚠ No adjacency matrix provided, using identity matrix")
        
        # Yield targets (if provided)
        if yield_targets is not None:
            self.targets = torch.FloatTensor(yield_targets)
            self.has_targets = True
        else:
            self.targets = None
            self.has_targets = False
        
        logger.info(f"✓ CropYieldDataset initialized:")
        logger.info(f"  - Samples: {self.N}")
        logger.info(f"  - Time steps: {self.T}")
        logger.info(f"  - Features: {self.F}")
        logger.info(f"  - Has targets: {self.has_targets}")
    
    def __len__(self) -> int:
        return self.N
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        """
        Get a single sample
        
        Returns:
            Dictionary with:
                - features: (T, F) time series features
                - adjacency: (N_sensors, N_sensors) adjacency matrix
                - target: yield value (if available)
        """
        sample = {
            'features': self.features[idx],  # (T, F)
            'adjacency': self.adjacency,  # (N_sensors, N_sensors)
        }
        
        if self.has_targets:
            sample['target'] = self.targets[idx]
        
        return sample


class SpatialGraphBuilder:
    """
    Builds spatial adjacency matrix from sensor locations
    """
    
    @staticmethod
    def build_knn_graph(sensor_locations: Dict[str, tuple], k: int = 3) -> np.ndarray:
        """
        Build k-nearest neighbors graph from sensor locations
        
        Args:
            sensor_locations: Dict mapping sensor_id to (lat, lon) coordinates
            k: Number of nearest neighbors
        
        Returns:
            (N, N) adjacency matrix
        """
        sensor_ids = list(sensor_locations.keys())
        n_sensors = len(sensor_ids)
        
        # Convert to array
        coords = np.array([sensor_locations[sid] for sid in sensor_ids])
        
        # Compute pairwise distances
        distances = np.zeros((n_sensors, n_sensors))
        for i in range(n_sensors):
            for j in range(n_sensors):
                if i != j:
                    # Haversine distance (approximate for small areas)
                    lat1, lon1 = coords[i]
                    lat2, lon2 = coords[j]
                    distances[i, j] = np.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)
        
        # Build k-NN adjacency
        adjacency = np.zeros((n_sensors, n_sensors))
        for i in range(n_sensors):
            # Find k nearest neighbors
            nearest = np.argsort(distances[i])[:k+1]  # +1 to exclude self
            for j in nearest:
                if i != j:
                    adjacency[i, j] = 1.0
                    adjacency[j, i] = 1.0  # Symmetric
        
        # Add self-loops
        adjacency += np.eye(n_sensors)
        
        logger.info(f"✓ Built {k}-NN spatial graph with {n_sensors} nodes")
        
        return adjacency
    
    @staticmethod
    def build_distance_graph(sensor_locations: Dict[str, tuple], 
                            threshold: float = 0.1) -> np.ndarray:
        """
        Build distance-based graph (connect sensors within threshold distance)
        
        Args:
            sensor_locations: Dict mapping sensor_id to (lat, lon) coordinates
            threshold: Distance threshold for connections
        
        Returns:
            (N, N) adjacency matrix
        """
        sensor_ids = list(sensor_locations.keys())
        n_sensors = len(sensor_ids)
        
        coords = np.array([sensor_locations[sid] for sid in sensor_ids])
        
        # Compute pairwise distances
        adjacency = np.zeros((n_sensors, n_sensors))
        for i in range(n_sensors):
            for j in range(i+1, n_sensors):
                lat1, lon1 = coords[i]
                lat2, lon2 = coords[j]
                dist = np.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)
                
                if dist < threshold:
                    adjacency[i, j] = 1.0
                    adjacency[j, i] = 1.0
        
        # Add self-loops
        adjacency += np.eye(n_sensors)
        
        logger.info(f"✓ Built distance-based graph with {n_sensors} nodes")
        logger.info(f"  - Threshold: {threshold}")
        logger.info(f"  - Avg connections per node: {adjacency.sum(axis=1).mean():.1f}")
        
        return adjacency


if __name__ == "__main__":
    # Test dataset creation
    logging.basicConfig(level=logging.INFO)
    
    # Create dummy data
    N, T, F_sensor, F_disease = 100, 7, 4, 2
    
    dummy_data = {
        'sensor_features': np.random.randn(N, T, F_sensor),
        'disease_features': np.random.randn(N, T, F_disease),
        'timestamps': np.array([[f"2025-01-{d:02d}" for d in range(1, T+1)] for _ in range(N)]),
        'sensor_ids': np.array([f"sensor_{i%5}" for i in range(N)])
    }
    
    # Create dummy adjacency matrix
    n_sensors = 5
    adjacency = np.eye(n_sensors)
    adjacency[0, 1] = adjacency[1, 0] = 1.0
    adjacency[1, 2] = adjacency[2, 1] = 1.0
    
    # Create dummy targets
    targets = np.random.rand(N) * 100  # Yield in kg
    
    # Create dataset
    dataset = CropYieldDataset(dummy_data, adjacency, targets)
    
    print(f"\n✓ Dataset test successful!")
    print(f"  - Dataset size: {len(dataset)}")
    print(f"  - Feature shape: {dataset.features.shape}")
    
    # Test getting a sample
    sample = dataset[0]
    print(f"  - Sample keys: {sample.keys()}")
    print(f"  - Sample feature shape: {sample['features'].shape}")
