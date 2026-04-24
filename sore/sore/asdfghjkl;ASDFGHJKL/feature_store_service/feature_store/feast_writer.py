import asyncio
from typing import List
import pandas as pd
from feast import FeatureStore
from ..schemas.feature_vector import FeatureVector
from .feature_store_backend import FeatureStoreBackend

class FeastFeatureStoreWriter(FeatureStoreBackend):
    def __init__(self, repo_path: str, use_hopsworks: bool = False):
        self.repo_path = repo_path
        self.use_hopsworks = use_hopsworks
        self.store = FeatureStore(repo_path) if not use_hopsworks else None
        self.batch_queue: asyncio.Queue = asyncio.Queue()
        self.flush_task = asyncio.create_task(self._batch_writer())

    async def write_batch(self, feature_vectors: List[FeatureVector]):
        for fv in feature_vectors:
            await self.batch_queue.put(fv)

    async def batch_flush(self):
        self.flush_task.cancel()
        await self._flush_batch()

    async def _batch_writer(self):
        while True:
            try:
                batch = []
                while len(batch) < 100:
                    fv = await asyncio.wait_for(self.batch_queue.get(), timeout=60.0)
                    batch.append(fv)
                await self._flush_batch(batch)
            except asyncio.TimeoutError:
                if batch:
                    await self._flush_batch(batch)

    async def _flush_batch(self, batch: List[FeatureVector] = None):
        if batch is None:
            batch = []
            while not self.batch_queue.empty():
                batch.append(self.batch_queue.get_nowait())

        if not batch:
            return

        # Convert to DataFrames
        env_df = pd.DataFrame([{
            'city': fv.city if hasattr(fv, 'city') else None,
            'event_at': pd.Timestamp.fromtimestamp(fv.minute_bucket),
            **{k: v for k, v in fv.model_dump().items() if k in ['rainfall_mm_per_hr', 'aqi_index_current', ...]}  # Environmental fields
        } for fv in batch if fv.env_complete])

        beh_df = pd.DataFrame([{
            'worker_id': fv.worker_id,
            'event_at': pd.Timestamp.fromtimestamp(fv.minute_bucket),
            **{k: v for k, v in fv.model_dump().items() if k in ['gps_displacement_m', ...]}  # Behaviour fields
        } for fv in batch if fv.behaviour_complete])

        inc_df = pd.DataFrame([{
            'worker_id': fv.worker_id,
            'event_at': pd.Timestamp.fromtimestamp(fv.minute_bucket),
            **{k: v for k, v in fv.model_dump().items() if k in ['expected_earnings_inr', ...]}  # Income fields
        } for fv in batch if fv.income_complete])

        if self.use_hopsworks:
            # Use Hopsworks SDK
            pass  # Assume fg.insert(df)
        else:
            # Feast
            if not env_df.empty:
                self.store.write_to_online_store('environmental_fv', env_df)
                # Offline write
            if not beh_df.empty:
                self.store.write_to_online_store('worker_behaviour_fv', beh_df)
            if not inc_df.empty:
                self.store.write_to_online_store('income_signals_fv', inc_df)