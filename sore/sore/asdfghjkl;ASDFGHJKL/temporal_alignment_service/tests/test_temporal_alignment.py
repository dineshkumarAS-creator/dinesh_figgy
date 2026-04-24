import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from ..temporal_alignment_service import TemporalAlignmentService
import asyncio

@pytest.mark.asyncio
async def test_window_emit():
    service = TemporalAlignmentService({})
    service.repo.get_and_delete_window = AsyncMock(return_value={
        'telemetry_clean:0': {
            'worker_id': 'worker1',
            'timestamp_utc': 1000.0,
            'smoothed_lat': 10.0,
            'smoothed_lon': 20.0,
            'estimated_speed_ms': 5.0,
            'delivery_attempts': 1,
            'app_state': 'active',
            'is_stationary': False,
            'data_quality_score': 1.0
        }
    })
    service.city_lookup.lookup_city = AsyncMock(return_value='Delhi')
    service.producer.send = AsyncMock()

    await service._emit_window('worker1', 960)  # minute_bucket

    # Assert send called
    assert service.producer.send.called

@pytest.mark.asyncio
async def test_late_arrival():
    service = TemporalAlignmentService({})
    # Mock buffer with incomplete data
    service.repo.get_and_delete_window = AsyncMock(return_value={
        'telemetry_clean:0': {
            'worker_id': 'worker1',
            'timestamp_utc': 1000.0,
            'smoothed_lat': 10.0,
            'smoothed_lon': 20.0,
            'estimated_speed_ms': 5.0,
            'delivery_attempts': 1,
            'app_state': 'active',
            'is_stationary': False,
            'data_quality_score': 1.0
        },
        'telemetry_clean:1': {
            'worker_id': 'worker1',
            'timestamp_utc': 1010.0,
            'smoothed_lat': 10.1,
            'smoothed_lon': 20.1,
            'estimated_speed_ms': 6.0,
            'delivery_attempts': 0,
            'app_state': 'active',
            'is_stationary': True,
            'data_quality_score': 0.8
        }
    })
    service.city_lookup.lookup_city = AsyncMock(return_value='Delhi')
    service.producer.send = AsyncMock()

    await service._emit_window('worker1', 960)

    # Check window_complete = False since <3 ticks
    call_args = service.producer.send.call_args[0][1]
    data = json.loads(call_args)
    assert not data['window_complete']
    assert data['telemetry_count'] == 2