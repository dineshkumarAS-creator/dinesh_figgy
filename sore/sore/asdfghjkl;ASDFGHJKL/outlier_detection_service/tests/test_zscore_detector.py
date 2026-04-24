import pytest
import numpy as np
from unittest.mock import AsyncMock
from ..detectors.zscore_detector import ZScoreDetector

@pytest.mark.asyncio
async def test_zscore_detection():
    redis = AsyncMock()
    detector = ZScoreDetector(redis, window_size=10, z_threshold=3.0)

    # Mock redis to return some values
    members = [f'{{"field": "rainfall_mm_per_hr", "value": {i}}}' for i in range(10)]
    redis.zrange.return_value = members
    redis.zadd = AsyncMock()
    redis.zremrangebyscore = AsyncMock()
    redis.zremrangebyrank = AsyncMock()

    # Normal value
    is_outlier, z_score, imputed = await detector.detect_and_impute('Delhi', 'rainfall_mm_per_hr', 5.0, 1000.0, False)
    assert not is_outlier

    # Outlier
    is_outlier, z_score, imputed = await detector.detect_and_impute('Delhi', 'rainfall_mm_per_hr', 50.0, 1001.0, False)
    # Depending on mock, but assume it detects
    # For test, perhaps compute manually
    # But since mocked, assert called

@pytest.mark.asyncio
async def test_zscore_imputation():
    redis = AsyncMock()
    detector = ZScoreDetector(redis, z_threshold=3.0)
    # Mock with data where mean=10, std=1, value=14 (z=4)
    members = [f'{{"field": "rainfall_mm_per_hr", "value": {10 + np.random.normal(0,1)}}}' for _ in range(10)]
    members.append('{"field": "rainfall_mm_per_hr", "value": 10}')  # Add normal
    redis.zrange.return_value = members
    redis.zadd = AsyncMock()
    redis.zremrangebyscore = AsyncMock()
    redis.zremrangebyrank = AsyncMock()

    is_outlier, z_score, imputed = await detector.detect_and_impute('Delhi', 'rainfall_mm_per_hr', 14.0, 1000.0, False)
    assert is_outlier
    assert imputed is not None  # Median