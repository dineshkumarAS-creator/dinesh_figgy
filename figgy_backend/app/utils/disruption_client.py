import asyncio
import time
from typing import Dict, List

class DisruptionClient:
    _cache: Dict[str, Dict] = {}
    _cache_expiry: Dict[str, float] = {}
    _cache_ttl = 300  # seconds

    @classmethod
    def _is_cache_valid(cls, zone_id: str) -> bool:
        return (
            zone_id in cls._cache and
            zone_id in cls._cache_expiry and
            time.time() < cls._cache_expiry[zone_id]
        )

    @classmethod
    def _set_cache(cls, zone_id: str, data: Dict):
        cls._cache[zone_id] = data
        cls._cache_expiry[zone_id] = time.time() + cls._cache_ttl

    @staticmethod
    async def fetch_weather(zone_id: str) -> dict:
        # TODO: Integrate OpenWeatherMap API
        try:
            # Simulate API call
            await asyncio.sleep(0.1)
            # Replace with real API integration
            return {"rain_mm": 2.5, "wind_kmh": 15.0, "condition": "rain"}
        except Exception:
            return {"rain_mm": 0, "wind_kmh": 0, "condition": "unknown"}

    @staticmethod
    async def fetch_govt_alerts(zone_id: str) -> List[dict]:
        # TODO: Integrate NDMA RSS feed or use mock for MVP
        try:
            await asyncio.sleep(0.1)
            # Replace with real API integration
            return [
                {"type": "flood", "severity": "high", "active": True},
                {"type": "curfew", "severity": "medium", "active": False},
            ]
        except Exception:
            return []

    @staticmethod
    async def fetch_news_signals(zone_id: str) -> dict:
        # TODO: Integrate news API or use mock for MVP
        try:
            await asyncio.sleep(0.1)
            # Replace with real API integration
            return {"keyword_hits": 2, "top_headline": "Protest blocks main road in zone"}
        except Exception:
            return {"keyword_hits": 0, "top_headline": ""}

    @staticmethod
    async def fetch_social_signals(zone_id: str) -> dict:
        # TODO: Integrate real social spike detector; mock for MVP
        try:
            await asyncio.sleep(0.1)
            # Replace with real API integration
            return {"spike_score": 0.7}
        except Exception:
            return {"spike_score": 0.0}

    @classmethod
    async def fetch_all(cls, zone_id: str) -> dict:
        if cls._is_cache_valid(zone_id):
            return cls._cache[zone_id]
        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    cls.fetch_weather(zone_id),
                    cls.fetch_govt_alerts(zone_id),
                    cls.fetch_news_signals(zone_id),
                    cls.fetch_social_signals(zone_id),
                ),
                timeout=3.0
            )
            data = {
                "fetch_weather": results[0],
                "fetch_govt_alerts": results[1],
                "fetch_news_signals": results[2],
                "fetch_social_signals": results[3],
            }
            cls._set_cache(zone_id, data)
            return data
        except Exception:
            # On failure, return all fallback values
            data = {
                "fetch_weather": await cls.fetch_weather(zone_id),
                "fetch_govt_alerts": await cls.fetch_govt_alerts(zone_id),
                "fetch_news_signals": await cls.fetch_news_signals(zone_id),
                "fetch_social_signals": await cls.fetch_social_signals(zone_id),
            }
            cls._set_cache(zone_id, data)
            return data
