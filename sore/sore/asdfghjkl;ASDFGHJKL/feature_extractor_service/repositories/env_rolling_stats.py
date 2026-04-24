import aioredis
import json
from typing import List, Optional
import numpy as np

class EnvRollingStatsRepository:
    def __init__(self, redis_url: str = 'redis://localhost:6379'):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.lua_script = """
        local key = KEYS[1]
        local timestamp = ARGV[1]
        local value = ARGV[2]
        local max_age = ARGV[3]
        redis.call('ZADD', key, timestamp, value)
        redis.call('ZREMRANGEBYSCORE', key, '-inf', timestamp - max_age)
        return redis.call('ZRANGE', key, 0, -1)
        """

    async def connect(self):
        self.redis = aioredis.from_url(self.redis_url)
        self.script_sha = await self.redis.script_load(self.lua_script)

    async def update_rolling(self, city: str, field: str, value: float, timestamp: float, window_seconds: int = 1800) -> List[float]:
        key = f'env_rolling:{city}:{field}'
        result = await self.redis.evalsha(self.script_sha, 1, key, timestamp, value, window_seconds)
        return [float(v) for v in result]

    async def get_city_monthly_stats(self, city: str) -> Optional[dict]:
        key = f'env_stats:{city}:aqi'
        data = await self.redis.get(key)
        return json.loads(data) if data else None

    async def set_city_monthly_stats(self, city: str, mean: float, std: float):
        key = f'env_stats:{city}:aqi'
        data = {'mean': mean, 'std': std}
        await self.redis.set(key, json.dumps(data))