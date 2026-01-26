"""
Spatio-Temporal Graph Neural Network for Crop Yield Prediction

Architecture:
1. Spatial: Graph Convolutional Network (GCN) for sensor relationships
2. Temporal: Temporal Convolutional Network (TCN) or GRU for time series
3. Fusion: Combine spatial and temporal features
4. Prediction: Yield regression head
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class GraphConvLayer(nn.Module):
    """
    Graph Convolutional Layer
    
    Implements: H' = σ(D^(-1/2) A D^(-1/2) H W)
    where A is adjacency matrix, D is degree matrix, H is node features
    """
    
    def __init__(self, in_features: int, out_features: int, bias: bool = True):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        
        self.weight = nn.Parameter(torch.FloatTensor(in_features, out_features))
        if bias:
            self.bias = nn.Parameter(torch.FloatTensor(out_features))
        else:
            self.register_parameter('bias', None)
        
        self.reset_parameters()
    
    def reset_parameters(self):
        nn.init.xavier_uniform_(self.weight)
        if self.bias is not None:
            nn.init.zeros_(self.bias)
    
    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            x: Node features (batch_size, num_nodes, in_features)
            adj: Adjacency matrix (num_nodes, num_nodes)
        
        Returns:
            Updated node features (batch_size, num_nodes, out_features)
        """
        # Normalize adjacency matrix
        adj = adj + torch.eye(adj.size(0), device=adj.device)  # Add self-loops
        degree = adj.sum(dim=1)
        degree_inv_sqrt = torch.pow(degree, -0.5)
        degree_inv_sqrt[torch.isinf(degree_inv_sqrt)] = 0.0
        
        # D^(-1/2) A D^(-1/2)
        adj_normalized = degree_inv_sqrt.unsqueeze(1) * adj * degree_inv_sqrt.unsqueeze(0)
        
        # H W
        support = torch.matmul(x, self.weight)
        
        # A H W
        output = torch.matmul(adj_normalized, support)
        
        if self.bias is not None:
            output = output + self.bias
        
        return output


class TemporalConvLayer(nn.Module):
    """
    Temporal Convolutional Layer with causal convolution
    """
    
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3, dilation: int = 1):
        super().__init__()
        self.padding = (kernel_size - 1) * dilation
        
        self.conv = nn.Conv1d(
            in_channels,
            out_channels,
            kernel_size,
            padding=self.padding,
            dilation=dilation
        )
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.2)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            x: (batch_size, in_channels, seq_len)
        
        Returns:
            (batch_size, out_channels, seq_len)
        """
        x = self.conv(x)
        # Remove future information (causal)
        if self.padding > 0:
            x = x[:, :, :-self.padding]
        x = self.relu(x)
        x = self.dropout(x)
        return x


class TemporalConvNet(nn.Module):
    """
    Temporal Convolutional Network (TCN) with multiple layers
    """
    
    def __init__(self, num_inputs: int, num_channels: list, kernel_size: int = 3):
        super().__init__()
        layers = []
        num_levels = len(num_channels)
        
        for i in range(num_levels):
            dilation = 2 ** i
            in_channels = num_inputs if i == 0 else num_channels[i-1]
            out_channels = num_channels[i]
            
            layers.append(TemporalConvLayer(
                in_channels,
                out_channels,
                kernel_size,
                dilation
            ))
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            x: (batch_size, num_inputs, seq_len)
        
        Returns:
            (batch_size, num_channels[-1], seq_len)
        """
        return self.network(x)


class STGNN(nn.Module):
    """
    Spatio-Temporal Graph Neural Network
    
    Combines:
    - Graph convolution for spatial relationships between sensors
    - Temporal convolution for time series modeling
    - Fusion layer for combining spatial and temporal features
    - Regression head for yield prediction
    """
    
    def __init__(self,
                 num_features: int,
                 num_nodes: int,
                 hidden_dim: int = 64,
                 num_gcn_layers: int = 2,
                 tcn_channels: list = [64, 64, 64],
                 kernel_size: int = 3,
                 dropout: float = 0.2):
        """
        Initialize ST-GNN
        
        Args:
            num_features: Number of input features per node per timestep
            num_nodes: Number of sensor nodes in the graph
            hidden_dim: Hidden dimension size
            num_gcn_layers: Number of graph convolution layers
            tcn_channels: List of channel sizes for TCN layers
            kernel_size: Kernel size for temporal convolution
            dropout: Dropout rate
        """
        super().__init__()
        
        self.num_features = num_features
        self.num_nodes = num_nodes
        self.hidden_dim = hidden_dim
        
        # Spatial: Graph Convolutional Layers
        self.gcn_layers = nn.ModuleList()
        gcn_in = num_features
        for i in range(num_gcn_layers):
            gcn_out = hidden_dim if i == num_gcn_layers - 1 else hidden_dim // 2
            self.gcn_layers.append(GraphConvLayer(gcn_in, gcn_out))
            gcn_in = gcn_out
        
        self.gcn_activation = nn.ReLU()
        self.gcn_dropout = nn.Dropout(dropout)
        
        # Temporal: Temporal Convolutional Network
        self.tcn = TemporalConvNet(
            num_inputs=hidden_dim,
            num_channels=tcn_channels,
            kernel_size=kernel_size
        )
        
        # Fusion layer
        self.fusion = nn.Sequential(
            nn.Linear(tcn_channels[-1], hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
        # Prediction head
        self.predictor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1)  # Single yield value
        )
        
        logger.info(f"✓ ST-GNN initialized:")
        logger.info(f"  - Input features: {num_features}")
        logger.info(f"  - Hidden dim: {hidden_dim}")
        logger.info(f"  - GCN layers: {num_gcn_layers}")
        logger.info(f"  - TCN channels: {tcn_channels}")
    
    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            x: Node features (batch_size, seq_len, num_nodes, num_features)
            adj: Adjacency matrix (num_nodes, num_nodes)
        
        Returns:
            Yield predictions (batch_size, 1)
        """
        batch_size, seq_len, num_nodes, num_features = x.shape
        
        # Spatial processing: Apply GCN at each timestep
        spatial_features = []
        for t in range(seq_len):
            x_t = x[:, t, :, :]  # (batch_size, num_nodes, num_features)
            
            # Apply GCN layers
            h = x_t
            for gcn_layer in self.gcn_layers:
                h = gcn_layer(h, adj)
                h = self.gcn_activation(h)
                h = self.gcn_dropout(h)
            
            spatial_features.append(h)
        
        # Stack temporal dimension: (batch_size, seq_len, num_nodes, hidden_dim)
        spatial_features = torch.stack(spatial_features, dim=1)
        
        # Aggregate across nodes (mean pooling)
        # (batch_size, seq_len, hidden_dim)
        spatial_features = spatial_features.mean(dim=2)
        
        # Temporal processing: Apply TCN
        # TCN expects (batch_size, channels, seq_len)
        temporal_input = spatial_features.transpose(1, 2)  # (batch_size, hidden_dim, seq_len)
        temporal_features = self.tcn(temporal_input)  # (batch_size, tcn_channels[-1], seq_len)
        
        # Take last timestep
        temporal_features = temporal_features[:, :, -1]  # (batch_size, tcn_channels[-1])
        
        # Fusion
        fused = self.fusion(temporal_features)  # (batch_size, hidden_dim)
        
        # Prediction
        output = self.predictor(fused)  # (batch_size, 1)
        
        return output


class STGNNWithUncertainty(nn.Module):
    """
    ST-GNN with heteroscedastic uncertainty estimation
    
    Predicts both mean and variance for uncertainty quantification
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__()
        
        # Base ST-GNN
        self.stgnn = STGNN(*args, **kwargs)
        
        # Separate head for variance prediction
        hidden_dim = kwargs.get('hidden_dim', 64)
        dropout = kwargs.get('dropout', 0.2)
        
        self.variance_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
            nn.Softplus()  # Ensure positive variance
        )
        
        # Store fusion output for variance prediction
        self.fusion_output = None
        
        # Hook to capture fusion output
        def hook(module, input, output):
            self.fusion_output = output
        
        self.stgnn.fusion.register_forward_hook(hook)
    
    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass with uncertainty
        
        Args:
            x: Node features (batch_size, seq_len, num_nodes, num_features)
            adj: Adjacency matrix (num_nodes, num_nodes)
        
        Returns:
            (mean, variance) tuple
                - mean: (batch_size, 1) predicted yield
                - variance: (batch_size, 1) predicted uncertainty
        """
        # Get mean prediction
        mean = self.stgnn(x, adj)
        
        # Get variance prediction from fusion output
        variance = self.variance_head(self.fusion_output)
        
        return mean, variance


def create_model(config: dict) -> nn.Module:
    """
    Factory function to create ST-GNN model
    
    Args:
        config: Model configuration dictionary
    
    Returns:
        ST-GNN model
    """
    model_type = config.get('model_type', 'stgnn')
    
    if model_type == 'stgnn':
        model = STGNN(
            num_features=config['num_features'],
            num_nodes=config['num_nodes'],
            hidden_dim=config.get('hidden_dim', 64),
            num_gcn_layers=config.get('num_gcn_layers', 2),
            tcn_channels=config.get('tcn_channels', [64, 64, 64]),
            kernel_size=config.get('kernel_size', 3),
            dropout=config.get('dropout', 0.2)
        )
    elif model_type == 'stgnn_uncertainty':
        model = STGNNWithUncertainty(
            num_features=config['num_features'],
            num_nodes=config['num_nodes'],
            hidden_dim=config.get('hidden_dim', 64),
            num_gcn_layers=config.get('num_gcn_layers', 2),
            tcn_channels=config.get('tcn_channels', [64, 64, 64]),
            kernel_size=config.get('kernel_size', 3),
            dropout=config.get('dropout', 0.2)
        )
    else:
        raise ValueError(f"Unknown model type: {model_type}")
    
    return model


if __name__ == "__main__":
    # Test model
    logging.basicConfig(level=logging.INFO)
    
    # Model config
    config = {
        'model_type': 'stgnn',
        'num_features': 6,  # 4 sensor + 2 disease features
        'num_nodes': 5,     # 5 sensors
        'hidden_dim': 64,
        'num_gcn_layers': 2,
        'tcn_channels': [64, 64, 64],
        'kernel_size': 3,
        'dropout': 0.2
    }
    
    # Create model
    model = create_model(config)
    
    # Test forward pass
    batch_size = 8
    seq_len = 7
    num_nodes = 5
    num_features = 6
    
    x = torch.randn(batch_size, seq_len, num_nodes, num_features)
    adj = torch.eye(num_nodes)
    
    output = model(x, adj)
    
    print(f"\n✓ Model test successful!")
    print(f"  - Input shape: {x.shape}")
    print(f"  - Output shape: {output.shape}")
    print(f"  - Model parameters: {sum(p.numel() for p in model.parameters()):,}")
