import aioredis
import json
from typing import Dict, Any, Optional

class WindowStateRepository:
    def __init__(self, redis_url: str = 'redis://localhost:6379'):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        self.redis = aioredis.from_url(self.redis_url)

    async def add_to_window(self, worker_id: str, minute_bucket: int, event_type: str, data: Dict[str, Any]):
        key = f'window:{worker_id}:{minute_bucket}'
        field = f'{event_type}:{len(await self.redis.hkeys(key))}'  # Unique field
        await self.redis.hset(key, field, json.dumps(data))
        await self.redis.expire(key, 300)  # 5 min TTL

    async def get_and_delete_window(self, worker_id: str, minute_bucket: int) -> Dict[str, Any]:
        key = f'window:{worker_id}:{minute_bucket}'
        data = await self.redis.hgetall(key)
        await self.redis.delete(key)
        return {k.decode('utf-8'): json.loads(v.decode('utf-8')) for k, v in data.items()}

    async def get_ntp_offset(self, worker_id: str) -> Optional[float]:
        key = f'ntp_offset:{worker_id}'
        offset = await self.redis.get(key)
        return float(offset) if offset else None

    async def set_ntp_offset(self, worker_id: str, offset: float):
        key = f'ntp_offset:{worker_id}'
        await self.redis.set(key, str(offset))