import torch
import torch.nn as nn
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class ModelConfig:
    """Configuration for LSTM model."""
    hidden_size: int = 128
    num_layers: int = 2
    dropout: float = 0.3
    seq_len: int = 30
    n_features: int = 10
    batch_first: bool = True


class BahdanauAttention(nn.Module):
    """Bahdanau-style additive attention mechanism."""
    
    def __init__(self, hidden_size: int):
        super().__init__()
        self.hidden_size = hidden_size
        
        # Attention weights
        self.W_q = nn.Linear(hidden_size, hidden_size)
        self.W_k = nn.Linear(hidden_size, hidden_size)
        self.v = nn.Linear(hidden_size, 1)
        
    def forward(self, lstm_output: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            lstm_output: (batch_size, seq_len, hidden_size)
        Returns:
            context: (batch_size, hidden_size) - attended representation
            attention_weights: (batch_size, seq_len) - normalized attention weights
        """
        batch_size, seq_len, hidden_size = lstm_output.shape
        
        # Project query and key
        Q = self.W_q(lstm_output)  # (batch_size, seq_len, hidden_size)
        K = self.W_k(lstm_output)  # (batch_size, seq_len, hidden_size)
        
        # Compute attention scores
        scores = torch.tanh(Q + K)  # (batch_size, seq_len, hidden_size)
        scores = self.v(scores)  # (batch_size, seq_len, 1)
        scores = scores.squeeze(-1)  # (batch_size, seq_len)
        
        # Normalize with softmax
        attention_weights = torch.softmax(scores, dim=1)  # (batch_size, seq_len)
        
        # Apply attention to get context vector
        context = torch.bmm(
            attention_weights.unsqueeze(1),  # (batch_size, 1, seq_len)
            lstm_output  # (batch_size, seq_len, hidden_size)
        ).squeeze(1)  # (batch_size, hidden_size)
        
        return context, attention_weights


class FIGGYLSTMVerifier(nn.Module):
    """LSTM-based PoW verifier for detecting unnatural movement patterns."""
    
    def __init__(self, config: ModelConfig):
        super().__init__()
        self.config = config
        self.last_attention_weights = None
        
        # Input normalization: normalize each feature independently
        self.input_norm = nn.BatchNorm1d(config.n_features)
        
        # LSTM layers: 2 stacked LSTM layers
        self.lstm = nn.LSTM(
            input_size=config.n_features,
            hidden_size=config.hidden_size,
            num_layers=config.num_layers,
            dropout=config.dropout,
            batch_first=config.batch_first
        )
        
        # Attention mechanism
        self.attention = BahdanauAttention(config.hidden_size)
        
        # Fully connected head
        self.fc_head = nn.Sequential(
            nn.Linear(config.hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x: torch.Tensor, return_attention: bool = False) -> torch.Tensor:
        """
        Forward pass through the LSTM verifier.
        
        Args:
            x: Input tensor of shape (batch_size, seq_len, n_features)
            return_attention: If True, returns attention weights alongside predictions
            
        Returns:
            pow_confidence: (batch_size, 1) - probability of genuine activity [0, 1]
            (optional) attention_weights: (batch_size, seq_len) if return_attention=True
        """
        batch_size = x.shape[0]
        
        # Input normalization: reshape for batch norm (B*T, F)
        x_reshaped = x.reshape(-1, self.config.n_features)
        x_norm = self.input_norm(x_reshaped)
        x_norm = x_norm.reshape(batch_size, self.config.seq_len, self.config.n_features)
        
        # LSTM layers
        lstm_output, (h_n, c_n) = self.lstm(x_norm)
        # lstm_output: (batch_size, seq_len, hidden_size)
        
        # Attention mechanism
        context, attention_weights = self.attention(lstm_output)
        # context: (batch_size, hidden_size)
        # attention_weights: (batch_size, seq_len)
        
        # Save for explainability
        self.last_attention_weights = attention_weights.detach()
        
        # Classification head
        pow_confidence = self.fc_head(context)  # (batch_size, 1)
        
        if return_attention:
            return pow_confidence, attention_weights
        return pow_confidence
    
    def get_attention_weights(self) -> Optional[torch.Tensor]:
        """Retrieve attention weights from last forward pass."""
        return self.last_attention_weights
