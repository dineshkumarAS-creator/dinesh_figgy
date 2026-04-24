import sys
import os

# Add the data_generator directory to path
sys.path.insert(0, r"c:\Users\sridh\OneDrive\Desktop\asdfghjkl;ASDFGHJKL\data_generator")

# Change to the directory
os.chdir(r"c:\Users\sridh\OneDrive\Desktop\asdfghjkl;ASDFGHJKL\data_generator")

# Import and run
from dataset_builder import DatasetBuilder

print("Starting dataset generation...")
builder = DatasetBuilder('data_generation_config.yaml')
datasets = builder.generate_dataset(100, 50)  # Small test run
builder.save_dataset(datasets, 'generated_data/')
print("Dataset generation complete!")