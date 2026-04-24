import aioredis
import json
from typing import Optional
from ..services.worker_profile_service import WorkerProfileService, WorkerProfile

class WorkerProfileRepository:
    def __init__(self, redis_url: str, profile_service: WorkerProfileService):
        self.redis_url = redis_url
        self.profile_service = profile_service
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        self.redis = aioredis.from_url(self.redis_url)

    async def get_profile(self, worker_id: str) -> Optional[WorkerProfile]:
        key = f'worker_profile:{worker_id}'
        cached = await self.redis.get(key)
        if cached:
            data = json.loads(cached)
            return WorkerProfile(**data)

        # Fetch from service
        profile = await self.profile_service.get_profile(worker_id)
        if profile:
            data = json.dumps({
                'worker_tier': profile.worker_tier,
                'base_hourly_rate_inr': profile.base_hourly_rate_inr,
                'historical_avg_deliveries_per_hr': profile.historical_avg_deliveries_per_hr,
                'historical_avg_earnings_per_hr': profile.historical_avg_earnings_per_hr,
                'enrollment_date': profile.enrollment_date
            })
            await self.redis.set(key, data, ex=3600)  # 1 hour
        return profile