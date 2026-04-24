"""
Layer 4 Inference Orchestrator

Collects scores from ML models (LSTM, Isolation Forest, GBM) and parametric trigger,
fuses them into a composite claim score, and routes to Layer 5 for payout processing.
"""

__version__ = "1.0.0"
