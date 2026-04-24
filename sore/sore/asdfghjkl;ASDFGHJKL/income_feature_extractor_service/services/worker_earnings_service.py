from abc import ABC, abstractmethod
from typing import Optional

class WorkerEarningsService(ABC):
    @abstractmethod
    async def get_earnings(self, worker_id: str, minute_bucket: int) -> Optional[float]:
        pass

class FakeWorkerEarningsService(WorkerEarningsService):
    async def get_earnings(self, worker_id: str, minute_bucket: int) -> Optional[float]:
        # Mock: return some earnings or -1
        return 100.0 if minute_bucket % 2 == 0 else -1.0