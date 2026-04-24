from dataset_builder import DatasetBuilder
import os

# Generate full-scale dataset
builder = DatasetBuilder('data_generation_config.yaml')
print("🔨 Generating full training dataset...")
datasets = builder.generate_dataset(n_genuine=10000, n_fraud=5000)

# Save datasets
print("💾 Saving datasets...")
builder.save_dataset(datasets, 'generated_data/train/')
builder.save_dataset(datasets, 'generated_data/test/')

print("\n✅ Dataset generation complete!")
print(f"Total sessions: 15,000 (10,000 genuine + 5,000 fraud)")
