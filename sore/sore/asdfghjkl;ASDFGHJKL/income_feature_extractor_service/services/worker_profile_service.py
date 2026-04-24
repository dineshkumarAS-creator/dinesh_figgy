from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass

@dataclass
class WorkerProfile:
    worker_tier: str
    base_hourly_rate_inr: float
    historical_avg_deliveries_per_hr: float
    historical_avg_earnings_per_hr: float
    enrollment_date: str

class WorkerProfileService(ABC):
    @abstractmethod
    async def get_profile(self, worker_id: str) -> Optional[WorkerProfile]:
        pass

class FakeWorkerProfileService(WorkerProfileService):
    async def get_profile(self, worker_id: str) -> Optional[WorkerProfile]:
        # Mock data
        return WorkerProfile(
            worker_tier='silver',
            base_hourly_rate_inr=150.0,
            historical_avg_deliveries_per_hr=10.0,
            historical_avg_earnings_per_hr=120.0,
            enrollment_date='2023-01-01'
        )