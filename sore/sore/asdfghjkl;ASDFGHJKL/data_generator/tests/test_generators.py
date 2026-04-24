import unittest
import pandas as pd
import numpy as np
from genuine_worker_generator import GenuineWorkerGenerator
from fraud_worker_generator import FraudWorkerGenerator
from sequence_builder import SequenceBuilder
from dataset_builder import DatasetBuilder

class TestDataGenerators(unittest.TestCase):
    def setUp(self):
        self.config_path = 'data_generation_config.yaml'
        self.genuine_gen = GenuineWorkerGenerator(self.config_path)
        self.fraud_gen = FraudWorkerGenerator(self.config_path)
        self.sequence_builder = SequenceBuilder(self.config_path)
        self.dataset_builder = DatasetBuilder(self.config_path)

    def test_genuine_worker_generation(self):
        """Test genuine worker session generation."""
        session = self.genuine_gen.generate_session('normal', 'Delhi', 'standard')

        self.assertIsInstance(session, pd.DataFrame)
        self.assertGreater(len(session), 0)
        self.assertIn('is_fraud', session.columns)
        self.assertTrue(all(session['is_fraud'] == False))
        self.assertIn('worker_id', session.columns)

    def test_fraud_worker_generation(self):
        """Test fraud worker session generation."""
        session = self.fraud_gen.generate_session('gps_spoof', 'Mumbai', 'premium')

        self.assertIsInstance(session, pd.DataFrame)
        self.assertGreater(len(session), 0)
        self.assertIn('is_fraud', session.columns)
        self.assertTrue(all(session['is_fraud'] == True))
        self.assertIn('fraud_probability', session.columns)

    def test_sequence_building(self):
        """Test sequence building for LSTM."""
        # Create test data
        test_data = pd.DataFrame({
            'worker_id': ['w1'] * 100,
            'minute_bucket': range(100),
            'city': ['Delhi'] * 100,
            'worker_tier': ['standard'] * 100,
            'gps_displacement_m': np.random.randn(100),
            'motion_continuity_score': np.random.rand(100),
            'is_fraud': [False] * 100
        })

        sequences, labels = self.sequence_builder.build_sequences(test_data, sequence_length=10)

        self.assertEqual(sequences.shape[0], labels.shape[0])
        self.assertEqual(sequences.shape[1], 10)  # sequence length
        self.assertEqual(sequences.shape[2], 2)  # number of features

    def test_isolation_forest_features(self):
        """Test Isolation Forest feature extraction."""
        test_data = pd.DataFrame({
            'worker_id': ['w1'] * 50 + ['w2'] * 50,
            'minute_bucket': list(range(50)) + list(range(50)),
            'gps_displacement_m': np.random.randn(100),
            'motion_continuity_score': np.random.rand(100),
            'road_match_score': np.random.rand(100),
            'app_foreground_ratio': np.random.rand(100),
            'actual_earnings_inr': np.random.rand(100) * 100,
            'income_loss_ratio': np.random.rand(100),
            'speed_anomaly_count': np.random.poisson(0.1, 100),
            'is_fraud': [False] * 100
        })

        features = self.sequence_builder.build_isolation_forest_features(test_data)

        self.assertEqual(features.shape[0], 2)  # 2 workers
        self.assertEqual(features.shape[1], 10)  # 10 features

    def test_gbm_features(self):
        """Test GBM feature extraction."""
        test_data = pd.DataFrame({
            'worker_id': ['w1'] * 50 + ['w2'] * 50,
            'minute_bucket': list(range(50)) + list(range(50)),
            'gps_displacement_m': np.random.randn(100),
            'motion_continuity_score': np.random.rand(100),
            'road_match_score': np.random.rand(100),
            'app_foreground_ratio': np.random.rand(100),
            'actual_earnings_inr': np.random.rand(100) * 100,
            'income_loss_ratio': np.random.rand(100),
            'speed_anomaly_count': np.random.poisson(0.1, 100),
            'composite_disruption_index': np.random.rand(100),
            'is_fraud': [False] * 50 + [True] * 50
        })

        features, labels = self.sequence_builder.build_gbm_features(test_data)

        self.assertEqual(features.shape[0], 2)  # 2 workers
        self.assertEqual(labels.shape[0], 2)
        self.assertEqual(features.shape[1], 10)  # 10 features

    def test_dataset_generation(self):
        """Test full dataset generation."""
        datasets = self.dataset_builder.generate_dataset(n_genuine=10, n_fraud=5)

        self.assertIn('lstm', datasets)
        self.assertIn('isolation_forest', datasets)
        self.assertIn('gbm', datasets)

        # Check LSTM data
        self.assertIn('sequences', datasets['lstm'])
        self.assertIn('labels', datasets['lstm'])

        # Check Isolation Forest data
        self.assertIn('features', datasets['isolation_forest'])

        # Check GBM data
        self.assertIn('features', datasets['gbm'])
        self.assertIn('labels', datasets['gbm'])

if __name__ == '__main__':
    unittest.main()