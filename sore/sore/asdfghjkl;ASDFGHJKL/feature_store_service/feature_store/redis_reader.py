import aioredis
import json
from typing import List, Optional
from ..schemas.feature_vector import FeatureVector

class RedisFeatureStoreReader:
    def __init__(self, redis_url: str = 'redis://localhost:6379'):
        self.redis_url = redis_url
        self.redis: aioredis.Redis = None

    async def connect(self):
        self.redis = aioredis.from_url(self.redis_url)

    async def get_latest(self, worker_id: str) -> Optional[FeatureVector]:
        key = f'features:latest:{worker_id}'
        data = await self.redis.get(key)
        if data:
            return FeatureVector.model_validate_json(data)
        return None

    async def get_window(self, worker_id: str, start_epoch: int, end_epoch: int) -> List[Optional[FeatureVector]]:
        keys = [f'features:{worker_id}:{epoch}' for epoch in range(start_epoch, end_epoch + 1, 60)]
        values = await self.redis.mget(keys)
        result = []
        for v in values:
            if v:
                result.append(FeatureVector.model_validate_json(v))
            else:
                result.append(None)
        return result