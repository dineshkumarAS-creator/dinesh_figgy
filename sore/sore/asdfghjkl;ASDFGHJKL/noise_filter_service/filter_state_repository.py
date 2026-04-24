import aioredis
import json
from typing import Optional
from .filters.kalman_gps import GPSKalmanFilter
from .filters.kalman_imu import IMUKalmanFilter
from .filters.weather_smoother import WeatherSmoother

class WorkerFilterState:
    def __init__(self, gps_filter: Optional[GPSKalmanFilter] = None, imu_filter: Optional[IMUKalmanFilter] = None):
        self.gps_filter = gps_filter
        self.imu_filter = imu_filter

    def to_dict(self) -> dict:
        return {
            'gps': self.gps_filter.to_dict() if self.gps_filter else None,
            'imu': self.imu_filter.to_dict() if self.imu_filter else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'WorkerFilterState':
        gps = GPSKalmanFilter.from_dict(data['gps']) if data.get('gps') else None
        imu = IMUKalmanFilter.from_dict(data['imu']) if data.get('imu') else None
        return cls(gps_filter=gps, imu_filter=imu)

class FilterStateRepository:
    def __init__(self, redis_url: str = 'redis://localhost:6379'):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        self.redis = aioredis.from_url(self.redis_url)

    async def disconnect(self):
        if self.redis:
            await self.redis.close()

    async def get_worker_state(self, worker_id: str) -> Optional[WorkerFilterState]:
        if not self.redis:
            await self.connect()
        key = f'filter_state:{worker_id}'
        data = await self.redis.get(key)
        if data:
            return WorkerFilterState.from_dict(json.loads(data))
        return None

    async def set_worker_state(self, worker_id: str, state: WorkerFilterState, ttl_seconds: int = 1800):
        if not self.redis:
            await self.connect()
        key = f'filter_state:{worker_id}'
        data = json.dumps(state.to_dict())
        await self.redis.set(key, data, ex=ttl_seconds)

    async def get_weather_smoother(self, city: str) -> Optional[WeatherSmoother]:
        if not self.redis:
            await self.connect()
        key = f'weather_smooth:{city}'
        data = await self.redis.get(key)
        if data:
            return WeatherSmoother.from_dict(json.loads(data))
        return None

    async def set_weather_smoother(self, city: str, smoother: WeatherSmoother, ttl_seconds: int = 1800):
        if not self.redis:
            await self.connect()
        key = f'weather_smooth:{city}'
        data = json.dumps(smoother.to_dict())
        await self.redis.set(key, data, ex=ttl_seconds)

    async def evict_inactive(self, max_age_seconds: int = 1800):
        # This would require scanning keys, but for simplicity, rely on TTL
        pass