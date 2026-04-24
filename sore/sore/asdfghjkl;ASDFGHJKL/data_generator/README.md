# FIGGY Synthetic Data Generator

This package generates synthetic training data for FIGGY's three ML models: LSTM PoW Verifier, Isolation Forest anomaly detector, and GBM fraud classifier.

## Overview

The data generator creates realistic worker sessions with environmental, behavioral, and income features. It simulates both genuine workers and various fraud archetypes to train robust ML models.

## Components

### Generators
- **GenuineWorkerGenerator**: Creates authentic worker sessions with realistic feature distributions
- **FraudWorkerGenerator**: Generates fraudulent sessions with different attack patterns:
  - GPS spoofing (unrealistic distances/speeds)
  - App manipulation (low foreground ratios)
  - Income inflation (overstated earnings)

### Sequence Builder
- **SequenceBuilder**: Transforms raw sessions into model-specific datasets:
  - LSTM: Time-series sequences of feature vectors
  - Isolation Forest: Session-level aggregated features
  - GBM: Session-level classification features

### Dataset Builder
- **DatasetBuilder**: Orchestrates full dataset generation and saving

### Visualization
- **DataVisualizer**: Creates plots for data analysis and validation

## Usage

```python
from dataset_builder import DatasetBuilder

# Generate training data
builder = DatasetBuilder('data_generation_config.yaml')
datasets = builder.generate_dataset(n_genuine=10000, n_fraud=5000)

# Save to disk
builder.save_dataset(datasets, 'generated_data/train/')

# Visualize
from visualise import DataVisualizer
viz = DataVisualizer('generated_data/train/')
viz.plot_lstm_distributions(datasets)
```

## Configuration

The `data_generation_config.yaml` file controls:
- Archetype distributions
- Feature parameters
- Fraud patterns
- Dataset sizes
- Output directories

## Features Generated

### Environmental
- Rainfall (mm/hr)
- AQI index
- Composite disruption index

### Behavioral
- GPS displacement
- Motion continuity score
- Road match score
- App foreground ratio
- Speed anomalies

### Income
- Expected/actual earnings
- Income loss ratio
- Loss plausibility score

## Testing

Run tests with:
```bash
python -m pytest tests/
```

## Dependencies

See `requirements.txt` for full list. Key packages:
- numpy, pandas: Data processing
- scipy: Statistical distributions
- faker: Synthetic worker IDs
- matplotlib, seaborn: Visualization
- scikit-learn: Feature processing