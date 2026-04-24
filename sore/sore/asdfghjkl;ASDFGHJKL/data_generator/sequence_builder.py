import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
import yaml

class SequenceBuilder:
    def __init__(self, config_path: str):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

    def build_sequences(self, df: pd.DataFrame, sequence_length: int = 60) -> Tuple[np.ndarray, np.ndarray]:
        """
        Build sequences for LSTM training.
        Returns: (sequences, labels)
        """
        # Sort by worker_id and minute_bucket
        df = df.sort_values(['worker_id', 'minute_bucket'])

        # Group by worker
        sequences = []
        labels = []

        for worker_id, group in df.groupby('worker_id'):
            if len(group) < sequence_length:
                continue  # Skip short sessions

            # Extract features
            feature_cols = [col for col in df.columns if col not in ['worker_id', 'minute_bucket', 'city', 'worker_tier', 'is_fraud', 'fraud_probability']]
            features = group[feature_cols].values

            # Build sliding windows
            for i in range(len(features) - sequence_length + 1):
                seq = features[i:i+sequence_length]
                label = group['is_fraud'].iloc[i+sequence_length-1]  # Label at end of sequence

                sequences.append(seq)
                labels.append(label)

        return np.array(sequences), np.array(labels)

    def build_isolation_forest_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Extract features for Isolation Forest (point-in-time anomalies).
        """
        # Use session-level aggregations
        session_features = []

        for worker_id, group in df.groupby('worker_id'):
            # Aggregate features
            agg = {
                'mean_displacement': group['gps_displacement_m'].mean(),
                'std_displacement': group['gps_displacement_m'].std(),
                'max_speed': group['gps_displacement_m'].max(),
                'mean_motion_continuity': group['motion_continuity_score'].mean(),
                'mean_road_match': group['road_match_score'].mean(),
                'mean_app_ratio': group['app_foreground_ratio'].mean(),
                'total_earnings': group['actual_earnings_inr'].sum(),
                'mean_loss_ratio': group['income_loss_ratio'].mean(),
                'anomaly_count': group['speed_anomaly_count'].sum(),
                'session_length': len(group)
            }
            session_features.append(list(agg.values()))

        return np.array(session_features)

    def build_gbm_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract features for GBM classifier (session-level classification).
        """
        features = []
        labels = []

        for worker_id, group in df.groupby('worker_id'):
            # Session-level features
            feat = [
                group['gps_displacement_m'].mean(),
                group['gps_displacement_m'].std(),
                group['motion_continuity_score'].mean(),
                group['road_match_score'].mean(),
                group['app_foreground_ratio'].mean(),
                group['actual_earnings_inr'].sum(),
                group['income_loss_ratio'].mean(),
                group['speed_anomaly_count'].sum(),
                len(group),  # session length
                group['composite_disruption_index'].mean()
            ]
            features.append(feat)
            labels.append(group['is_fraud'].iloc[0])

        return np.array(features), np.array(labels)