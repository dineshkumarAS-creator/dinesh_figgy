import numpy as np
from typing import Tuple, Optional
import aioredis
import json

class IQRDetector:
    def __init__(self, redis: aioredis.Redis, window_size: int = 50):
        self.redis = redis
        self.window_size = window_size

    async def detect(self, worker_id: str, smoothed_speed: float, delivery_speed_implied: Optional[float], timestamp: float) -> Tuple[bool, str]:
        key = f'outlier:speed:{worker_id}'
        # Add smoothed_speed
        member = json.dumps({'type': 'smoothed', 'value': smoothed_speed})
        await self.redis.zadd(key, {member: timestamp})
        if delivery_speed_implied is not None:
            member2 = json.dumps({'type': 'implied', 'value': delivery_speed_implied})
            await self.redis.zadd(key, {member2: timestamp})

        # Evict old beyond 1 hour
        await self.redis.zremrangebyscore(key, '-inf', timestamp - 3600)
        # Keep last window_size per type? But to simplify, keep last 100 total, but filter by type
        await self.redis.zremrangebyrank(key, 0, -100-1)  # Keep last 100

        # Get smoothed speeds
        members = await self.redis.zrange(key, 0, -1)
        smoothed_values = []
        for m in members:
            data = json.loads(m)
            if data['type'] == 'smoothed':
                smoothed_values.append(data['value'])

        if len(smoothed_values) < 10:  # Need some data
            return False, ""

        # IQR for smoothed_speed
        q1 = np.percentile(smoothed_values, 25)
        q3 = np.percentile(smoothed_values, 75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        is_iqr_outlier = not (lower <= smoothed_speed <= upper)

        # Physical check: speed > 80 km/h (22.22 m/s)
        is_physical_outlier = smoothed_speed > 22.22

        if is_physical_outlier:
            return True, "physical_impossible"
        elif is_iqr_outlier:
            return True, "iqr_breach"
        else:
            return False, ""