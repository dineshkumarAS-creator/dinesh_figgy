from dataclasses import dataclass
from typing import List, Optional
import numpy as np
from datetime import datetime
from ..schemas.environmental_features import EnvironmentalFeatures
from ..repositories.env_rolling_stats import EnvRollingStatsRepository

@dataclass
class FeatureContext:
    rainfall_30min_mean: Optional[float] = None
    aqi_city_mean: Optional[float] = None
    aqi_city_std: Optional[float] = None

class EnvironmentalFeatureExtractor:
    def __init__(self, repo: EnvRollingStatsRepository):
        self.repo = repo

    async def load_context(self, city: str, rainfall: float, timestamp: float) -> FeatureContext:
        # Update and get rolling rainfall
        rolling_rainfall = await self.repo.update_rolling(city, 'rainfall', rainfall, timestamp)
        rainfall_mean = np.mean(rolling_rainfall) if rolling_rainfall else None

        # Get AQI stats
        aqi_stats = await self.repo.get_city_monthly_stats(city)
        aqi_mean = aqi_stats['mean'] if aqi_stats else None
        aqi_std = aqi_stats['std'] if aqi_stats else None

        return FeatureContext(
            rainfall_30min_mean=rainfall_mean,
            aqi_city_mean=aqi_mean,
            aqi_city_std=aqi_std
        )

    def extract(self, aligned_event: dict, context: FeatureContext) -> EnvironmentalFeatures:
        worker_id = aligned_event['worker_id']
        city = aligned_event['weather_city'] or aligned_event['aqi_city'] or 'Unknown'
        minute_bucket = aligned_event['minute_bucket']

        # Rainfall features
        rainfall = aligned_event.get('latest_rainfall_mm_per_hr', 0.0)
        intensity_class = self._classify_rainfall_intensity(rainfall)
        trend = self._compute_rainfall_trend(rainfall, context.rainfall_30min_mean)

        # AQI features
        aqi = aligned_event.get('latest_aqi_index', 0.0)
        aqi_stdz = self._standardize_aqi(aqi, context.aqi_city_mean, context.aqi_city_std)
        aqi_category = self._categorize_aqi(aqi)

        # Event features
        active_events = aligned_event.get('active_events', [])
        severity_score, event_types, event_count = self._compute_event_severity(active_events)

        # Composite
        disruption_index = self._compute_disruption_index(rainfall, aqi, severity_score)

        # Quality
        weather_quality = aligned_event.get('weather_data_quality_score', 0.0)
        aqi_quality = aligned_event.get('aqi_data_quality_score', 0.0)
        env_quality = self._compute_env_quality(weather_quality, aqi_quality)

        return EnvironmentalFeatures(
            worker_id=worker_id,
            city=city,
            minute_bucket=minute_bucket,
            rainfall_mm_per_hr=rainfall,
            rainfall_intensity_class=intensity_class,
            rainfall_30min_trend=trend,
            aqi_index_current=aqi,
            aqi_stdz=aqi_stdz,
            aqi_category=aqi_category,
            event_severity_score=severity_score,
            event_type_active=event_types,
            event_count_active=event_count,
            composite_disruption_index=disruption_index,
            env_feature_quality=env_quality,
            feature_computed_at=datetime.utcnow()
        )

    def _classify_rainfall_intensity(self, rainfall: float) -> str:
        if rainfall == 0:
            return "none"
        elif rainfall <= 7.5:
            return "light"
        elif rainfall <= 15:
            return "moderate"
        elif rainfall <= 40:
            return "heavy"
        else:
            return "extreme"

    def _compute_rainfall_trend(self, current: float, mean: Optional[float]) -> str:
        if mean is None or mean == 0:
            return "stable"
        ratio = current / mean
        if current > mean * 2.0 and current > 20:
            return "spike"
        elif ratio > 1.2:
            return "increasing"
        elif ratio < 0.8:
            return "decreasing"
        else:
            return "stable"

    def _standardize_aqi(self, aqi: float, mean: Optional[float], std: Optional[float]) -> float:
        if mean is None or std is None or std == 0:
            return 0.0
        return (aqi - mean) / std

    def _categorize_aqi(self, aqi: float) -> str:
        if aqi <= 50:
            return "good"
        elif aqi <= 100:
            return "moderate"
        elif aqi <= 150:
            return "unhealthy_sensitive"
        elif aqi <= 200:
            return "unhealthy"
        elif aqi <= 300:
            return "very_unhealthy"
        else:
            return "hazardous"

    def _compute_event_severity(self, events: List[dict]) -> tuple[float, List[str], int]:
        if not events:
            return 0.0, [], 0

        scores = []
        types = []
        for event in events:
            base_score = {'curfew': 1.0, 'bandh': 0.9, 'strike': 0.7, 'protest': 0.4}.get(event['event_type'], 0.4)
            coverage = event.get('coverage_pct', 1.0)
            reliability = 1.0 if event.get('source') == 'govt' else 0.7
            score = base_score * coverage * reliability
            scores.append(score)
            types.append(event['event_type'])

        return max(scores), types, len(events)

    def _compute_disruption_index(self, rainfall: float, aqi: float, event_score: float) -> float:
        rainfall_score = min(rainfall / 40.0, 1.0)
        aqi_score = min(aqi / 400.0, 1.0)
        return 0.4 * rainfall_score + 0.35 * aqi_score + 0.25 * event_score

    def _compute_env_quality(self, weather_q: float, aqi_q: float) -> float:
        if weather_q < 0.3 or aqi_q < 0.3:
            return 0.0
        return 0.5 * weather_q + 0.5 * aqi_q