from dataset_builder import DatasetBuilder
import os

# Generate medium-scale dataset for quick validation
builder = DatasetBuilder('data_generation_config.yaml')
print("🔨 Generating medium-scale training dataset (1000 genuine + 500 fraud)...")
datasets = builder.generate_dataset(n_genuine=1000, n_fraud=500)

# Save datasets
print("💾 Saving datasets...")
os.makedirs('generated_data/train/', exist_ok=True)
os.makedirs('generated_data/test/', exist_ok=True)

builder.save_dataset(datasets, 'generated_data/train/')

print("\n✅ Dataset generation complete!")
print(f"Total sessions: 1,500 (1,000 genuine + 500 fraud)")

# Show dataset statistics
import numpy as np
print("\n📊 Dataset Statistics:")
print(f"  GBM Dataset: {datasets['gbm']['features'].shape[0]} sessions × {datasets['gbm']['features'].shape[1]} features")
print(f"  Isolation Forest: {datasets['isolation_forest']['features'].shape[0]} sessions × {datasets['isolation_forest']['features'].shape[1]} features")
print(f"  Fraud rate: {np.mean(datasets['gbm']['labels']):.1%}")
