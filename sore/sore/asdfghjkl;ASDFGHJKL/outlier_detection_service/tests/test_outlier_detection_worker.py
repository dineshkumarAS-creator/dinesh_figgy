import pytest
from unittest.mock import AsyncMock, MagicMock
from ..outlier_detection_worker import OutlierDetectionWorker
import json

@pytest.mark.asyncio
async def test_process_telemetry():
    worker = OutlierDetectionWorker({})
    worker.iqr_detector.detect = AsyncMock(return_value=(False, ""))
    worker.producer.send = AsyncMock()

    data = {
        'worker_id': 'worker1',
        'timestamp': 1000.0,
        'estimated_speed_ms': 5.0
    }

    cleaned = await worker.process_telemetry(data)
    assert not cleaned.is_outlier
    assert cleaned.data_quality_score == 1.0

@pytest.mark.asyncio
async def test_process_weather_outlier():
    worker = OutlierDetectionWorker({})
    worker.zscore_detector.detect_and_impute = AsyncMock(return_value=(True, 4.5, 10.0))
    worker.producer.send = AsyncMock()

    data = {
        'city': 'Delhi',
        'timestamp': 1000.0,
        'rainfall_mm_per_hr': 50.0,
        'is_government_verified': False
    }

    cleaned = await worker.process_weather(data)
    assert cleaned.is_outlier
    assert cleaned.outlier_method == "zscore"
    assert cleaned.imputed
    assert cleaned.imputed_value == 10.0
    assert cleaned.data_quality_score == 0.8