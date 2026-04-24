import aioredis
import json
from typing import List

class RollingWindowRepository:
    def __init__(self, redis_url: str = 'redis://localhost:6379'):
        self.redis_url = redis_url
        self.redis: aioredis.Redis = None

    async def connect(self):
        self.redis = aioredis.from_url(self.redis_url)

    async def add_to_window(self, key: str, value: dict, timestamp: float, max_age: int, max_count: int):
        member = json.dumps(value)
        await self.redis.zadd(key, {member: timestamp})
        await self.redis.zremrangebyscore(key, '-inf', timestamp - max_age)
        await self.redis.zremrangebyrank(key, 0, -max_count-1)

    async def get_window_values(self, key: str, filter_func=None) -> List[float]:
        members = await self.redis.zrange(key, 0, -1)
        values = []
        for m in members:
            data = json.loads(m)
            if filter_func is None or filter_func(data):
                values.append(data.get('value', 0))
        return values