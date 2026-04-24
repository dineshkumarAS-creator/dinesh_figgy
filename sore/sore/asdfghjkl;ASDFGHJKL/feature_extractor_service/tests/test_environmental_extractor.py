import pytest
from datetime import datetime
from ..extractors.environmental_extractor import EnvironmentalFeatureExtractor, FeatureContext
from ..repositories.env_rolling_stats import EnvRollingStatsRepository
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_rainfall_intensity_class():
    repo = AsyncMock()
    extractor = EnvironmentalFeatureExtractor(repo)

    context = FeatureContext()
    event = {
        'worker_id': 'w1',
        'weather_city': 'Delhi',
        'minute_bucket': 1000,
        'latest_rainfall_mm_per_hr': 10.0,
        'latest_aqi_index': 100.0,
        'active_events': [],
        'weather_data_quality_score': 1.0,
        'aqi_data_quality_score': 1.0
    }

    features = extractor.extract(event, context)
    assert features.rainfall_intensity_class == "moderate"

@pytest.mark.asyncio
async def test_rainfall_trend():
    repo = AsyncMock()
    extractor = EnvironmentalFeatureExtractor(repo)

    context = FeatureContext(rainfall_30min_mean=5.0)
    event = {
        'worker_id': 'w1',
        'weather_city': 'Delhi',
        'minute_bucket': 1000,
        'latest_rainfall_mm_per_hr': 25.0,  # > mean*2 and >20
        'latest_aqi_index': 100.0,
        'active_events': [],
        'weather_data_quality_score': 1.0,
        'aqi_data_quality_score': 1.0
    }

    features = extractor.extract(event, context)
    assert features.rainfall_30min_trend == "spike"

@pytest.mark.asyncio
async def test_aqi_standardization():
    repo = AsyncMock()
    extractor = EnvironmentalFeatureExtractor(repo)

    context = FeatureContext(aqi_city_mean=100.0, aqi_city_std=20.0)
    event = {
        'worker_id': 'w1',
        'aqi_city': 'Delhi',
        'minute_bucket': 1000,
        'latest_rainfall_mm_per_hr': 0.0,
        'latest_aqi_index': 120.0,
        'active_events': [],
        'weather_data_quality_score': 1.0,
        'aqi_data_quality_score': 1.0
    }

    features = extractor.extract(event, context)
    assert features.aqi_stdz == 1.0  # (120-100)/20

@pytest.mark.asyncio
async def test_event_severity():
    repo = AsyncMock()
    extractor = EnvironmentalFeatureExtractor(repo)

    context = FeatureContext()
    event = {
        'worker_id': 'w1',
        'weather_city': 'Delhi',
        'minute_bucket': 1000,
        'latest_rainfall_mm_per_hr': 0.0,
        'latest_aqi_index': 100.0,
        'active_events': [
            {'event_type': 'curfew', 'coverage_pct': 1.0, 'source': 'govt'},
            {'event_type': 'protest', 'coverage_pct': 0.5, 'source': 'news'}
        ],
        'weather_data_quality_score': 1.0,
        'aqi_data_quality_score': 1.0
    }

    features = extractor.extract(event, context)
    assert features.event_severity_score == 1.0  # max of curfew
    assert features.event_type_active == ['curfew', 'protest']
    assert features.event_count_active == 2

@pytest.mark.asyncio
async def test_composite_disruption():
    repo = AsyncMock()
    extractor = EnvironmentalFeatureExtractor(repo)

    context = FeatureContext()
    event = {
        'worker_id': 'w1',
        'weather_city': 'Delhi',
        'minute_bucket': 1000,
        'latest_rainfall_mm_per_hr': 20.0,  # score 0.5
        'latest_aqi_index': 200.0,  # score 0.5
        'active_events': [{'event_type': 'curfew', 'coverage_pct': 1.0, 'source': 'govt'}],  # score 1.0
        'weather_data_quality_score': 1.0,
        'aqi_data_quality_score': 1.0
    }

    features = extractor.extract(event, context)
    expected = 0.4 * 0.5 + 0.35 * 0.5 + 0.25 * 1.0
    assert features.composite_disruption_index == pytest.approx(expected)

@pytest.mark.asyncio
async def test_env_quality():
    repo = AsyncMock()
    extractor = EnvironmentalFeatureExtractor(repo)

    context = FeatureContext()
    event = {
        'worker_id': 'w1',
        'weather_city': 'Delhi',
        'minute_bucket': 1000,
        'latest_rainfall_mm_per_hr': 0.0,
        'latest_aqi_index': 100.0,
        'active_events': [],
        'weather_data_quality_score': 0.8,
        'aqi_data_quality_score': 0.9
    }

    features = extractor.extract(event, context)
    assert features.env_feature_quality == 0.85