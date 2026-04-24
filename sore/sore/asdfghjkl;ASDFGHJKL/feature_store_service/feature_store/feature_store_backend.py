from abc import ABC, abstractmethod
from typing import List
from ..schemas.feature_vector import FeatureVector

class FeatureStoreBackend(ABC):
    @abstractmethod
    async def write_batch(self, feature_vectors: List[FeatureVector]):
        pass

    @abstractmethod
    async def batch_flush(self):
        pass