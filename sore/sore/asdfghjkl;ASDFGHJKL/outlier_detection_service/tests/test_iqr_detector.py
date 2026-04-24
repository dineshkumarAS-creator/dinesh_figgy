import pytest
from unittest.mock import AsyncMock
from ..detectors.iqr_detector import IQRDetector

@pytest.mark.asyncio
async def test_iqr_detection():
    redis = AsyncMock()
    detector = IQRDetector(redis, window_size=10)

    # Mock data
    members = [f'{{"type": "smoothed", "value": {i}}}' for i in range(1, 11)]  # 1 to 10
    redis.zrange.return_value = members
    redis.zadd = AsyncMock()
    redis.zremrangebyscore = AsyncMock()
    redis.zremrangebyrank = AsyncMock()

    # Normal value
    is_outlier, reason = await detector.detect('worker1', 5.0, None, 1000.0)
    assert not is_outlier

    # Outlier
    is_outlier, reason = await detector.detect('worker1', 50.0, None, 1001.0)
    assert is_outlier
    assert reason == "iqr_breach"

@pytest.mark.asyncio
async def test_physical_limit():
    redis = AsyncMock()
    detector = IQRDetector(redis)

    # Mock
    redis.zrange.return_value = []
    redis.zadd = AsyncMock()
    redis.zremrangebyscore = AsyncMock()
    redis.zremrangebyrank = AsyncMock()

    # Physical outlier
    is_outlier, reason = await detector.detect('worker1', 25.0, None, 1000.0)  # 25 m/s > 22.22
    assert is_outlier
    assert reason == "physical_impossible"