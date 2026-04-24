import numpy as np
from typing import Tuple, Optional
import aioredis
import json

class ZScoreDetector:
    def __init__(self, redis: aioredis.Redis, window_size: int = 100, z_threshold: float = 3.0):
        self.redis = redis
        self.window_size = window_size
        self.z_threshold = z_threshold

    async def detect_and_impute(self, city: str, field: str, value: float, timestamp: float, is_gov_verified: bool) -> Tuple[bool, Optional[float], Optional[float]]:
        key = f'outlier:weather:{city}'
        # Add to sorted set: member is json, score timestamp
        member = json.dumps({'field': field, 'value': value})
        await self.redis.zadd(key, {member: timestamp})
        # Evict old beyond 2 hours
        await self.redis.zremrangebyscore(key, '-inf', timestamp - 7200)
        # Keep only last window_size
        await self.redis.zremrangebyrank(key, 0, -self.window_size-1)

        # Get all members
        members = await self.redis.zrange(key, 0, -1)
        values = []
        for m in members:
            data = json.loads(m)
            if data['field'] == field:
                values.append(data['value'])

        if len(values) < 2:
            return False, None, None

        mean = np.mean(values)
        std = np.std(values)
        if std == 0:
            z_score = 0
        else:
            z_score = (value - mean) / std

        is_outlier = abs(z_score) > self.z_threshold

        imputed_value = None
        if is_outlier and not is_gov_verified:
            median = np.median(values)
            imputed_value = median

        return is_outlier, z_score, imputed_value