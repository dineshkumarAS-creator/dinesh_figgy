import numpy as np
import pandas as pd
from faker import Faker
from typing import List, Dict
import yaml

fake = Faker()

class GenuineWorkerGenerator:
    def __init__(self, config_path: str):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

    def generate_session(self, archetype: str, city: str, worker_tier: str) -> pd.DataFrame:
        duration = np.random.randint(30, 121)  # 30-120 min
        start_time = np.random.randint(0, 1440)  # Minute of day

        rows = []
        for i in range(duration):
            minute_bucket = start_time + i
            row = self._generate_minute(archetype, city, worker_tier, minute_bucket, i)
            rows.append(row)

        return pd.DataFrame(rows)

    def _generate_minute(self, archetype: str, city: str, worker_tier: str, minute_bucket: int, seq_idx: int) -> Dict:
        # Base features
        worker_id = fake.uuid4()
        rainfall = np.random.exponential(5) if 'rain' in archetype else 0
        aqi = np.random.normal(100, 20)
        disruption = min(rainfall / 40 + aqi / 400, 1.0)
        event_severity = 0.0

        # GPS
        displacement = np.random.lognormal(4, 0.5)  # ~50m
        cumulative = displacement * (seq_idx + 1)
        speed = np.random.lognormal(2, 0.3)  # ~7 kmh

        # Behaviour
        motion_continuity = np.random.uniform(0.7, 0.95)
        road_match = np.random.uniform(0.75, 0.98)
        app_ratio = np.random.uniform(0.8, 1.0)
        anomalies = 0

        # Income
        expected = 100.0
        actual = expected * (1 - disruption * np.random.uniform(0.8, 1.2))
        loss_ratio = (expected - actual) / expected
        plausibility = 1 - abs(loss_ratio - disruption)

        return {
            'worker_id': worker_id,
            'minute_bucket': minute_bucket,
            'city': city,
            'worker_tier': worker_tier,
            'rainfall_mm_per_hr': rainfall,
            'aqi_index_current': aqi,
            'composite_disruption_index': disruption,
            'event_severity_score': event_severity,
            'gps_displacement_m': displacement,
            'cumulative_displacement_m': cumulative,
            'active_zone_minutes': seq_idx,
            'delivery_attempt_count': np.random.poisson(0.5),
            'motion_continuity_score': motion_continuity,
            'road_match_score': road_match,
            'app_foreground_ratio': app_ratio,
            'speed_anomaly_count': anomalies,
            'expected_earnings_inr': expected,
            'actual_earnings_inr': actual,
            'income_loss_ratio': loss_ratio,
            'loss_plausibility_score': plausibility,
            'delivery_rate_vs_baseline': 1.0,
            'earnings_consistency_score': 1.0,
            'overall_feature_quality': 1.0,
            'is_fraud': False,
            'fraud_probability': 0.0
        }