import numpy as np
import pandas as pd
from typing import Dict, List
import yaml
from genuine_worker_generator import GenuineWorkerGenerator
from fraud_worker_generator import FraudWorkerGenerator
from sequence_builder import SequenceBuilder
import pickle
import os

class DatasetBuilder:
    def __init__(self, config_path: str):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.genuine_gen = GenuineWorkerGenerator(config_path)
        self.fraud_gen = FraudWorkerGenerator(config_path)
        self.sequence_builder = SequenceBuilder(config_path)

    def generate_dataset(self, n_genuine: int = 1000, n_fraud: int = 500) -> Dict:
        """
        Generate complete training dataset for all three models.
        """
        print(f"Generating {n_genuine} genuine and {n_fraud} fraud sessions...")

        # Generate genuine data
        genuine_data = []
        archetypes = ['normal', 'rain_worker', 'high_aqi']
        cities = ['Delhi', 'Mumbai', 'Bangalore', 'Chennai']
        tiers = ['standard', 'premium']

        for _ in range(n_genuine):
            archetype = np.random.choice(archetypes)
            city = np.random.choice(cities)
            tier = np.random.choice(tiers)
            session = self.genuine_gen.generate_session(archetype, city, tier)
            genuine_data.append(session)

        # Generate fraud data
        fraud_data = []
        fraud_types = ['gps_spoof', 'app_manipulation', 'income_inflation']

        for _ in range(n_fraud):
            fraud_type = np.random.choice(fraud_types)
            city = np.random.choice(cities)
            tier = np.random.choice(tiers)
            session = self.fraud_gen.generate_session(fraud_type, city, tier)
            fraud_data.append(session)

        # Combine all data
        all_data = pd.concat(genuine_data + fraud_data, ignore_index=True)

        # Build datasets for each model
        datasets = {}

        # LSTM sequences
        print("Building LSTM sequences...")
        lstm_sequences, lstm_labels = self.sequence_builder.build_sequences(all_data)
        datasets['lstm'] = {
            'sequences': lstm_sequences,
            'labels': lstm_labels
        }

        # Isolation Forest features
        print("Building Isolation Forest features...")
        if_features = self.sequence_builder.build_isolation_forest_features(all_data)
        datasets['isolation_forest'] = {
            'features': if_features
        }

        # GBM features
        print("Building GBM features...")
        gbm_features, gbm_labels = self.sequence_builder.build_gbm_features(all_data)
        datasets['gbm'] = {
            'features': gbm_features,
            'labels': gbm_labels
        }

        return datasets

    def save_dataset(self, datasets: Dict, output_dir: str):
        """
        Save datasets to disk.
        """
        os.makedirs(output_dir, exist_ok=True)

        for model_name, data in datasets.items():
            path = os.path.join(output_dir, f'{model_name}_dataset.pkl')
            with open(path, 'wb') as f:
                pickle.dump(data, f)
            print(f"Saved {model_name} dataset to {path}")

        # Also save raw data
        raw_path = os.path.join(output_dir, 'raw_sessions.pkl')
        # Note: We'd need to reconstruct raw data, but for now just save structure
        print(f"Dataset saved to {output_dir}")

if __name__ == "__main__":
    import os
    os.chdir(r"c:\Users\sridh\OneDrive\Desktop\asdfghjkl;ASDFGHJKL\data_generator")
    builder = DatasetBuilder('data_generation_config.yaml')
    datasets = builder.generate_dataset(100, 50)  # Small test run
    builder.save_dataset(datasets, 'generated_data/')