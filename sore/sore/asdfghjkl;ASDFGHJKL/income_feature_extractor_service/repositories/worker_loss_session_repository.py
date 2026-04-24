import aioredis
from typing import Optional

class WorkerLossSessionRepository:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        self.redis = aioredis.from_url(self.redis_url)

    async def get_cumulative_loss(self, worker_id: str) -> float:
        key = f'worker_loss_session:{worker_id}'
        loss = await self.redis.get(key)
        return float(loss) if loss else 0.0

    async def set_cumulative_loss(self, worker_id: str, loss: float):
        key = f'worker_loss_session:{worker_id}'
        await self.redis.set(key, str(loss), ex=28800)  # 8 hours

    async def reset_session(self, worker_id: str):
        key = f'worker_loss_session:{worker_id}'
        await self.redis.delete(key)