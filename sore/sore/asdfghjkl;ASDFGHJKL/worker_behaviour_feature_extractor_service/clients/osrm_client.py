import httpx
import aioredis
import json
from typing import Optional, Tuple
import asyncio

class OsrmClient:
    def __init__(self, osrm_host: str, redis_url: str = 'redis://localhost:6379'):
        self.osrm_host = osrm_host
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.client = httpx.AsyncClient(timeout=2.0)

    async def connect(self):
        self.redis = aioredis.from_url(self.redis_url)

    async def match_road(self, coords: list[Tuple[float, float]]) -> float:
        # coords: list of (lon, lat)
        if len(coords) < 2:
            return -1.0

        # Check cache
        rounded_coords = [(round(lon, 3), round(lat, 3)) for lon, lat in coords[-1:]]  # Last point for cache
        cache_key = f"osrm_cache:{rounded_coords[0][0]}:{rounded_coords[0][1]}"
        cached = await self.redis.get(cache_key)
        if cached:
            return float(cached)

        # Build coords string
        coords_str = ';'.join(f'{lon},{lat}' for lon, lat in coords)

        url = f"http://{self.osrm_host}/match/v1/driving/{coords_str}"
        try:
            resp = await self.client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if 'matchings' and data['matchings']:
                    confidence = data['matchings'][0]['confidence']
                    await self.redis.set(cache_key, str(confidence), ex=3600)
                    return confidence
        except Exception:
            pass

        # Unavailable
        return -1.0

    async def close(self):
        await self.client.aclose()
        await self.redis.close()