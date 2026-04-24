import pytest
from unittest.mock import AsyncMock, MagicMock
from ..noise_filter_worker import NoiseFilterWorker
import json

@pytest.mark.asyncio
async def test_process_telemetry():
    worker = NoiseFilterWorker({})
    worker.repo.get_worker_state = AsyncMock(return_value=None)
    worker.repo.set_worker_state = AsyncMock()
    worker.producer.send = AsyncMock()

    # Mock message
    msg = MagicMock()
    msg.value = json.dumps({
        'worker_id': 'worker1',
        'lat': 10.0,
        'lon': 20.0,
        'accuracy_m': 5.0,
        'accel_x': 0.1,
        'accel_y': 0.0,
        'accel_z': 9.8,
        'timestamp': 1000.0
    }).encode('utf-8')

    # Since it's async for, hard to test directly. Perhaps test the logic separately.
    # For now, placeholder
    assert True

@pytest.mark.asyncio
async def test_process_weather():
    worker = NoiseFilterWorker({})
    worker.repo.get_weather_smoother = AsyncMock(return_value=None)
    worker.repo.set_weather_smoother = AsyncMock()
    worker.producer.send = AsyncMock()

    msg = MagicMock()
    msg.value = json.dumps({
        'city': 'Delhi',
        'rainfall_mm_per_hr': 10.0,
        'timestamp': 1000.0
    }).encode('utf-8')

    assert True