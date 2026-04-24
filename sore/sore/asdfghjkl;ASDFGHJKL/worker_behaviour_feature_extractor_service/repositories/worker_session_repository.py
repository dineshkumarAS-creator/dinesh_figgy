import aioredis
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class WorkerSessionState:
    session_start: Optional[int] = None
    last_window_time: Optional[int] = None
    cumulative_displacement_m: float = 0.0
    zone_minutes_map: Dict[str, int] = None

    def __post_init__(self):
        if self.zone_minutes_map is None:
            self.zone_minutes_map = {}

class WorkerSessionRepository:
    def __init__(self, redis_url: str = 'redis://localhost:6379'):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        self.redis = aioredis.from_url(self.redis_url)

    async def get_session_state(self, worker_id: str) -> WorkerSessionState:
        key = f'worker_session:{worker_id}'
        data = await self.redis.get(key)
        if data:
            d = json.loads(data)
            return WorkerSessionState(**d)
        return WorkerSessionState()

    async def set_session_state(self, worker_id: str, state: WorkerSessionState):
        key = f'worker_session:{worker_id}'
        data = json.dumps(asdict(state))
        await self.redis.set(key, data, ex=900)  # 15 min

    async def get_last_position(self, worker_id: str) -> Optional[Tuple[float, float]]:
        key = f'worker_pos:{worker_id}'
        data = await self.redis.get(key)
        if data:
            return tuple(json.loads(data))
        return None

    async def set_last_position(self, worker_id: str, lat: float, lon: float):
        key = f'worker_pos:{worker_id}'
        data = json.dumps([lat, lon])
        await self.redis.set(key, data, ex=900)

    async def get_rolling_speeds(self, worker_id: str) -> list[float]:
        key = f'worker_speed:{worker_id}'
        members = await self.redis.zrange(key, 0, -1, withscores=True)
        # Assume scores are timestamps, members are speeds
        speeds = [float(m.decode('utf-8')) for m, s in members]
        return speeds

    async def add_speed(self, worker_id: str, speed: float, timestamp: int):
        key = f'worker_speed:{worker_id}'
        await self.redis.zadd(key, {str(speed): timestamp})
        await self.redis.zremrangebyrank(key, 0, -11)  # Keep last 10
        await self.redis.expire(key, 900)

    async def get_app_states(self, worker_id: str) -> list[str]:
        key = f'worker_app_state:{worker_id}'
        members = await self.redis.zrange(key, 0, -1)
        states = [m.decode('utf-8') for m in members]
        return states

    async def add_app_state(self, worker_id: str, state: str, timestamp: int):
        key = f'worker_app_state:{worker_id}'
        await self.redis.zadd(key, {state: timestamp})
        await self.redis.zremrangebyrank(key, 0, -11)  # Keep last 10
        await self.redis.expire(key, 900)