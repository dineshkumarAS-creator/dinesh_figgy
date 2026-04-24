import aioredis
from ..schemas.feature_vector import FeatureVector
from prometheus_client import Counter

feature_count = Counter('feature_vectors_written', 'Number of feature vectors written')

class RedisFeatureStoreWriter:
    def __init__(self, redis_url: str = 'redis://localhost:6379'):
        self.redis_url = redis_url
        self.redis: aioredis.Redis = None

    async def connect(self):
        self.redis = aioredis.from_url(self.redis_url)

    async def write(self, feature_vector: FeatureVector):
        key = f'features:{feature_vector.worker_id}:{feature_vector.minute_bucket}'
        latest_key = f'features:latest:{feature_vector.worker_id}'
        value = feature_vector.model_dump_json()

        async with self.redis.pipeline() as pipe:
            pipe.set(key, value, ex=7200)  # 2h
            pipe.set(latest_key, value, ex=1800)  # 30min
            await pipe.execute()

        feature_count.inc()