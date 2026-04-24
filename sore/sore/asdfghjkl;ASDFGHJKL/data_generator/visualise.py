import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from typing import Dict
import pickle
import os

class DataVisualizer:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir

    def load_datasets(self) -> Dict:
        datasets = {}
        for filename in os.listdir(self.data_dir):
            if filename.endswith('_dataset.pkl'):
                model_name = filename.replace('_dataset.pkl', '')
                with open(os.path.join(self.data_dir, filename), 'rb') as f:
                    datasets[model_name] = pickle.load(f)
        return datasets

    def plot_lstm_distributions(self, datasets: Dict):
        """Plot feature distributions for LSTM data."""
        if 'lstm' not in datasets:
            return

        sequences = datasets['lstm']['sequences']
        labels = datasets['lstm']['labels']

        # Flatten sequences for plotting
        genuine_seqs = sequences[labels == 0]
        fraud_seqs = sequences[labels == 1]

        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle('LSTM Feature Distributions: Genuine vs Fraud')

        features_to_plot = [0, 1, 5, 10, 15, 20]  # Sample feature indices

        for i, feat_idx in enumerate(features_to_plot):
            ax = axes[i//3, i%3]

            genuine_vals = genuine_seqs[:, :, feat_idx].flatten()
            fraud_vals = fraud_seqs[:, :, feat_idx].flatten()

            ax.hist(genuine_vals, alpha=0.7, label='Genuine', bins=50, density=True)
            ax.hist(fraud_vals, alpha=0.7, label='Fraud', bins=50, density=True)
            ax.set_title(f'Feature {feat_idx}')
            ax.legend()

        plt.tight_layout()
        plt.savefig(os.path.join(self.data_dir, 'lstm_distributions.png'))
        plt.show()

    def plot_isolation_forest_features(self, datasets: Dict):
        """Plot feature correlations for Isolation Forest."""
        if 'isolation_forest' not in datasets:
            return

        features = datasets['isolation_forest']['features']

        plt.figure(figsize=(12, 10))
        sns.heatmap(np.corrcoef(features.T), annot=False, cmap='coolwarm')
        plt.title('Isolation Forest Feature Correlations')
        plt.savefig(os.path.join(self.data_dir, 'isolation_forest_correlations.png'))
        plt.show()

    def plot_gbm_feature_importance(self, datasets: Dict):
        """Plot GBM feature distributions."""
        if 'gbm' not in datasets:
            return

        features = datasets['gbm']['features']
        labels = datasets['gbm']['labels']

        genuine_features = features[labels == 0]
        fraud_features = features[labels == 1]

        fig, axes = plt.subplots(3, 3, figsize=(15, 12))
        fig.suptitle('GBM Feature Distributions: Genuine vs Fraud')

        feature_names = [
            'Mean Displacement', 'Std Displacement', 'Mean Motion Continuity',
            'Mean Road Match', 'Mean App Ratio', 'Total Earnings',
            'Mean Loss Ratio', 'Anomaly Count', 'Session Length'
        ]

        for i in range(min(9, features.shape[1])):
            ax = axes[i//3, i%3]

            ax.hist(genuine_features[:, i], alpha=0.7, label='Genuine', bins=30, density=True)
            ax.hist(fraud_features[:, i], alpha=0.7, label='Fraud', bins=30, density=True)
            ax.set_title(feature_names[i])
            ax.legend()

        plt.tight_layout()
        plt.savefig(os.path.join(self.data_dir, 'gbm_distributions.png'))
        plt.show()

    def plot_class_balance(self, datasets: Dict):
        """Plot class balance across datasets."""
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))

        # LSTM
        if 'lstm' in datasets:
            labels = datasets['lstm']['labels']
            axes[0].bar(['Genuine', 'Fraud'], [np.sum(labels == 0), np.sum(labels == 1)])
            axes[0].set_title('LSTM Sequence Labels')

        # GBM
        if 'gbm' in datasets:
            labels = datasets['gbm']['labels']
            axes[1].bar(['Genuine', 'Fraud'], [np.sum(labels == 0), np.sum(labels == 1)])
            axes[1].set_title('GBM Session Labels')

        # Isolation Forest doesn't have explicit labels
        axes[2].text(0.5, 0.5, 'Isolation Forest:\nUnsupervised', ha='center', va='center', transform=axes[2].transAxes)
        axes[2].set_title('Isolation Forest')

        plt.tight_layout()
        plt.savefig(os.path.join(self.data_dir, 'class_balance.png'))
        plt.show()

if __name__ == "__main__":
    visualizer = DataVisualizer('generated_data/')
    datasets = visualizer.load_datasets()

    visualizer.plot_lstm_distributions(datasets)
    visualizer.plot_isolation_forest_features(datasets)
    visualizer.plot_gbm_feature_importance(datasets)
    visualizer.plot_class_balance(datasets)