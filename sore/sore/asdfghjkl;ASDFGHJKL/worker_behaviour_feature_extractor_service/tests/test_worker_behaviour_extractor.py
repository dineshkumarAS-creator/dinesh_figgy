import pytest
from unittest.mock import AsyncMock
from ..extractors.worker_behaviour_extractor import WorkerBehaviourFeatureExtractor, BehaviourContext
from ..repositories.worker_session_repository import WorkerSessionState

@pytest.mark.asyncio
async def test_gps_displacement():
    repo = AsyncMock()
    osrm = AsyncMock()
    extractor = WorkerBehaviourFeatureExtractor(repo, osrm)

    context = BehaviourContext(last_position=(28.0, 77.0))
    event = {
        'worker_id': 'w1',
        'minute_bucket': 1000,
        'avg_smoothed_lat': 28.01,
        'avg_smoothed_lon': 77.01,
        'max_speed_ms': 5.0,
        'stationary_pct': 0.0,
        'sum_delivery_attempts': 1,
        'majority_app_state': 'foreground',
        'avg_data_quality_score': 1.0
    }

    features = extractor.extract(event, context)
    assert features.gps_displacement_m > 0

@pytest.mark.asyncio
async def test_session_reset():
    repo = AsyncMock()
    osrm = AsyncMock()
    extractor = WorkerBehaviourFeatureExtractor(repo, osrm)

    context = BehaviourContext(session_state=WorkerSessionState(last_window_time=900))  # 100 sec gap
    event = {
        'worker_id': 'w1',
        'minute_bucket': 1000,
        'avg_smoothed_lat': 28.0,
        'avg_smoothed_lon': 77.0,
        'max_speed_ms': 5.0,
        'stationary_pct': 0.0,
        'sum_delivery_attempts': 1,
        'majority_app_state': 'foreground',
        'avg_data_quality_score': 1.0
    }

    features = extractor.extract(event, context)
    assert features.behaviour_feature_quality < 1.0  # Penalized

@pytest.mark.asyncio
async def test_motion_continuity():
    repo = AsyncMock()
    osrm = AsyncMock()
    extractor = WorkerBehaviourFeatureExtractor(repo, osrm)

    context = BehaviourContext(rolling_speeds=[10.0, 10.0, 10.0])
    event = {
        'worker_id': 'w1',
        'minute_bucket': 1000,
        'avg_smoothed_lat': 28.0,
        'avg_smoothed_lon': 77.0,
        'max_speed_ms': 5.0,  # 18 kmh
        'stationary_pct': 0.0,
        'sum_delivery_attempts': 1,
        'majority_app_state': 'foreground',
        'avg_data_quality_score': 1.0
    }

    # Mock displacement
    context.last_position = (28.0, 77.0)

    features = extractor.extract(event, context)
    assert 0 <= features.motion_continuity_score <= 1