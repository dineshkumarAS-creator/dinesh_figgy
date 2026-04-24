import aioredis
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from typing import Optional
import json
import time

class CityLookup:
    def __init__(self, redis_url: str = 'redis://localhost:6379', user_agent: str = 'figgy_app'):
        self.redis_url = redis_url
        self.geolocator = Nominatim(user_agent=user_agent)
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        self.redis = aioredis.from_url(self.redis_url)

    async def lookup_city(self, lat: float, lon: float) -> Optional[str]:
        cache_key = f'city:{lat:.4f}:{lon:.4f}'
        cached = await self.redis.get(cache_key)
        if cached:
            return cached.decode('utf-8')

        try:
            location = self.geolocator.reverse((lat, lon), timeout=5)
            if location and 'address' in location.raw:
                city = location.raw['address'].get('city') or location.raw['address'].get('town') or location.raw['address'].get('village')
                if city:
                    await self.redis.set(cache_key, city, ex=86400)  # 24h TTL
                    return city
        except GeocoderTimedOut:
            pass

        # Fallback to hardcoded nearest city
        return self._fallback_city(lat, lon)

    def _fallback_city(self, lat: float, lon: float) -> str:
        # Hardcoded India cities with bbox
        cities = {
            'Delhi': (28.4, 28.9, 76.8, 77.4),
            'Mumbai': (18.9, 19.3, 72.7, 73.0),
            # Add more as needed
        }
        for city, (lat_min, lat_max, lon_min, lon_max) in cities.items():
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                return city
        return 'Unknown'