import pytest
from unittest.mock import AsyncMock
from ..feature_store.redis_writer import RedisFeatureStoreWriter
from ..schemas.feature_vector import FeatureVector
from datetime import datetime

@pytest.mark.asyncio
async def test_redis_write():
    writer = RedisFeatureStoreWriter()
    writer.redis = AsyncMock()

    fv = FeatureVector(
        worker_id='w1',
        minute_bucket=1000,
        feature_pipeline_version='1.0.0',
        computed_at=datetime.utcnow()
    )

    await writer.write(fv)

    # Assert pipeline executed
    writer.redis.pipeline.assert_called()