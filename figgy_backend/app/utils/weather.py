"""
figgy_backend/app/utils/weather.py
====================================
WeatherService — Figgy GigShield Parametric Trigger Engine.

Fetches real-time weather (rainfall, temperature) and air quality (AQI)
for Figgy's five Chennai delivery zones using the OpenWeatherMap free tier.

Endpoints used:
  - Current Weather : https://api.openweathermap.org/data/2.5/weather
  - Air Pollution   : https://api.openweathermap.org/data/2.5/air_pollution

Zone Coordinates (Chennai):
  North   : 13.1300, 80.2800  (Perambur / Kolathur)
  South   : 12.9165, 80.1425  (Tambaram / Pallavaram)
  East    : 13.0475, 80.2575  (Mylapore / Adyar)
  West    : 13.0500, 80.1950  (Valasaravakkam / Porur)
  Central : 13.0827, 80.2707  (T Nagar / Nungambakkam)

Parametric Thresholds:
  rain_mm_hr > 40  → triggers Smart/Elite plans
  rain_mm_hr > 60  → triggers Lite plan as well
  temp_c     > 42  → triggers Smart/Elite plans
  aqi        > 400 → triggers Smart/Elite plans

Usage:
  from app.utils.weather import WeatherService
  svc = WeatherService()
  one  = svc.get_zone_weather("North")   # single zone dict
  all_ = svc.check_all_zones()           # list of zone dicts

MOCK MODE:
  If OPENWEATHER_API_KEY is absent from the environment, all calls return
  realistic Chennai mock data. "North" is seeded with 52 mm/hr rain to let
  the full parametric-trigger pipeline run in demo mode.

Caching:
  Each zone result is cached in-process for 10 minutes to avoid hammering
  the API quota during repeated scheduler runs.
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger("FIGGY_WEATHER")

# ---------------------------------------------------------------------------
# Zone registry — lat/lon for OWM coordinate-based calls
# ---------------------------------------------------------------------------

ZONE_COORDS: dict[str, tuple[float, float]] = {
    "North":   (13.1300, 80.2800),   # Perambur / Kolathur
    "South":   (12.9165, 80.1425),   # Tambaram / Pallavaram
    "East":    (13.0475, 80.2575),   # Mylapore / Adyar
    "West":    (13.0500, 80.1950),   # Valasaravakkam / Porur
    "Central": (13.0827, 80.2707),   # T Nagar / Nungambakkam
}

# ---------------------------------------------------------------------------
# Parametric thresholds
# ---------------------------------------------------------------------------

THRESHOLD_RAIN_SMART_ELITE = 40.0   # mm/hr — Smart & Elite plan trigger
THRESHOLD_RAIN_LITE        = 60.0   # mm/hr — Lite plan trigger
THRESHOLD_TEMP             = 42.0   # °C    — Smart & Elite plan trigger
THRESHOLD_AQI              = 400    # index — Smart & Elite plan trigger

# ---------------------------------------------------------------------------
# OWM AQI band → approximate AQI-IN conversion
# OWM uses a 1–5 scale; this maps to indicative AQI-IN breakpoints.
# ---------------------------------------------------------------------------

_OWM_AQI_TO_IN = {1: 50, 2: 100, 3: 200, 4: 300, 5: 500}

# ---------------------------------------------------------------------------
# Mock data — used when OPENWEATHER_API_KEY is absent
# "North" is seeded with heavy rain so the full pipeline exercises triggers.
# ---------------------------------------------------------------------------

_MOCK_DATA: dict[str, dict] = {
    "North": {
        "rain_mm_hr": 52.0,
        "temp_c":     34.5,
        "aqi":        180,
    },
    "South": {
        "rain_mm_hr": 4.2,
        "temp_c":     33.1,
        "aqi":        95,
    },
    "East": {
        "rain_mm_hr": 18.7,
        "temp_c":     33.8,
        "aqi":        110,
    },
    "West": {
        "rain_mm_hr": 6.0,
        "temp_c":     34.0,
        "aqi":        130,
    },
    "Central": {
        "rain_mm_hr": 9.5,
        "temp_c":     35.2,
        "aqi":        160,
    },
}

# Cache TTL in seconds (10 minutes)
_CACHE_TTL_SECONDS = 600


# ---------------------------------------------------------------------------
# WeatherService
# ---------------------------------------------------------------------------

class WeatherService:
    """
    Fetches weather + AQI for Figgy's five Chennai delivery zones and
    evaluates parametric trigger conditions.

    Thread-safety: the in-process dict cache is not locked; suitable for
    single-threaded Flask dev server and APScheduler (single job instance).
    For multi-threaded production, wrap cache access in a threading.Lock.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key: str = api_key or os.getenv("OPENWEATHER_API_KEY", "")
        self._mock_mode: bool = not bool(self._api_key)
        # Cache: zone_name → {"data": dict, "fetched_at": float (epoch)}
        self._cache: dict[str, dict] = {}

        if self._mock_mode:
            logger.warning(
                "[WEATHER] OPENWEATHER_API_KEY not set — running in MOCK MODE. "
                "North zone is seeded with 52 mm/hr rain for demo."
            )

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def get_zone_weather(self, zone_name: str) -> dict:
        """
        Return a weather dict for the named zone.

        Parameters
        ----------
        zone_name : str
            One of: "North", "South", "East", "West", "Central" (case-sensitive).

        Returns
        -------
        dict with keys:
            zone              – str, echoed zone name
            rain_mm_hr        – float, rainfall in the last hour (mm)
            temp_c            – float, temperature in Celsius
            aqi               – int, approximate AQI-IN index
            disruption_triggered – bool, True if any threshold is crossed
            trigger_type      – str or None  (e.g. "rain_heavy", "heat", "aqi")
            fetched_at        – ISO-8601 UTC timestamp of data origin
            raw_data          – dict, the full OWM API response (or mock marker)
        """
        if zone_name not in ZONE_COORDS:
            logger.error(
                f"[WEATHER] Unknown zone '{zone_name}'. "
                f"Valid zones: {list(ZONE_COORDS.keys())}"
            )
            return self._safe_defaults(zone_name)

        # Check cache
        cached = self._cache.get(zone_name)
        if cached and (time.monotonic() - cached["fetched_at"]) < _CACHE_TTL_SECONDS:
            logger.debug(f"[WEATHER] Cache hit for zone '{zone_name}'.")
            return cached["data"]

        # Fetch (real or mock)
        if self._mock_mode:
            result = self._fetch_mock(zone_name)
        else:
            result = self._fetch_live(zone_name)

        # Store in cache
        self._cache[zone_name] = {
            "data": result,
            "fetched_at": time.monotonic(),
        }
        return result

    def check_all_zones(self) -> list[dict]:
        """
        Return a list of weather dicts for all five Chennai zones.

        Returns
        -------
        list[dict]  — one entry per zone, in definition order.
        """
        results = []
        for zone_name in ZONE_COORDS:
            results.append(self.get_zone_weather(zone_name))
        return results

    def invalidate_cache(self, zone_name: Optional[str] = None) -> None:
        """
        Evict cached data.

        Parameters
        ----------
        zone_name : str or None
            If provided, evicts only that zone. If None, clears all zones.
        """
        if zone_name:
            self._cache.pop(zone_name, None)
            logger.debug(f"[WEATHER] Cache cleared for zone '{zone_name}'.")
        else:
            self._cache.clear()
            logger.debug("[WEATHER] Entire weather cache cleared.")

    # -----------------------------------------------------------------------
    # Internal: live fetch
    # -----------------------------------------------------------------------

    def _fetch_live(self, zone_name: str) -> dict:
        """Call OWM Current Weather + Air Pollution APIs for a zone."""
        lat, lon = ZONE_COORDS[zone_name]
        raw: dict = {}

        try:
            # --- Step 1: Current weather (rain + temp) ----------------------
            w_resp = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat":   lat,
                    "lon":   lon,
                    "appid": self._api_key,
                    "units": "metric",   # Celsius
                },
                timeout=8,
            )
            w_resp.raise_for_status()
            w_data = w_resp.json()
            raw["weather"] = w_data

            rain_mm_hr: float = w_data.get("rain", {}).get("1h", 0.0)
            temp_c: float     = w_data["main"]["temp"]

            # --- Step 2: Air pollution (AQI) ---------------------------------
            a_resp = requests.get(
                "https://api.openweathermap.org/data/2.5/air_pollution",
                params={
                    "lat":   lat,
                    "lon":   lon,
                    "appid": self._api_key,
                },
                timeout=8,
            )
            a_resp.raise_for_status()
            a_data = a_resp.json()
            raw["air_pollution"] = a_data

            owm_aqi_band: int = a_data["list"][0]["main"]["aqi"]   # 1–5
            aqi: int          = _OWM_AQI_TO_IN.get(owm_aqi_band, 50)

            return self._build_result(
                zone_name,
                round(rain_mm_hr, 2),
                round(temp_c, 1),
                aqi,
                raw,
            )

        except requests.exceptions.Timeout:
            logger.error(f"[WEATHER] Timeout fetching data for zone '{zone_name}'.")
            return self._safe_defaults(zone_name)

        except requests.exceptions.HTTPError as exc:
            logger.error(
                f"[WEATHER] HTTP error for zone '{zone_name}': "
                f"{exc.response.status_code} {exc.response.text[:200]}"
            )
            return self._safe_defaults(zone_name)

        except Exception as exc:
            logger.error(
                f"[WEATHER] Unexpected error for zone '{zone_name}': {exc}",
                exc_info=True,
            )
            return self._safe_defaults(zone_name)

    # -----------------------------------------------------------------------
    # Internal: mock fetch
    # -----------------------------------------------------------------------

    def _fetch_mock(self, zone_name: str) -> dict:
        """Return deterministic mock weather data for demo/testing."""
        mock = _MOCK_DATA[zone_name]
        logger.debug(
            f"[WEATHER] MOCK — zone '{zone_name}': "
            f"rain={mock['rain_mm_hr']} mm/hr, "
            f"temp={mock['temp_c']}°C, aqi={mock['aqi']}"
        )
        return self._build_result(
            zone_name,
            mock["rain_mm_hr"],
            mock["temp_c"],
            mock["aqi"],
            raw={"source": "mock", "zone": zone_name},
        )

    # -----------------------------------------------------------------------
    # Internal: helpers
    # -----------------------------------------------------------------------

    def _build_result(
        self,
        zone_name: str,
        rain_mm_hr: float,
        temp_c: float,
        aqi: int,
        raw: dict,
    ) -> dict:
        """Evaluate thresholds and return the standardised zone-weather dict."""
        trigger_type: Optional[str] = None

        if rain_mm_hr > THRESHOLD_RAIN_LITE:
            trigger_type = "rain_extreme"          # triggers all tiers (Lite + Smart + Elite)
        elif rain_mm_hr > THRESHOLD_RAIN_SMART_ELITE:
            trigger_type = "rain_heavy"            # triggers Smart & Elite only
        elif temp_c > THRESHOLD_TEMP:
            trigger_type = "heat"                  # triggers Smart & Elite only
        elif aqi > THRESHOLD_AQI:
            trigger_type = "aqi"                   # triggers Smart & Elite only

        disruption_triggered = trigger_type is not None

        result = {
            "zone":                 zone_name,
            "rain_mm_hr":           rain_mm_hr,
            "temp_c":               temp_c,
            "aqi":                  aqi,
            "disruption_triggered": disruption_triggered,
            "trigger_type":         trigger_type,
            "fetched_at":           datetime.now(timezone.utc).isoformat(),
            "raw_data":             raw,
        }

        if disruption_triggered:
            logger.info(
                f"[WEATHER] ⚡ TRIGGER in zone '{zone_name}': {trigger_type} | "
                f"rain={rain_mm_hr} mm/hr, temp={temp_c}°C, aqi={aqi}"
            )
        else:
            logger.debug(
                f"[WEATHER] Zone '{zone_name}' — no trigger | "
                f"rain={rain_mm_hr} mm/hr, temp={temp_c}°C, aqi={aqi}"
            )

        return result

    def _safe_defaults(self, zone_name: str) -> dict:
        """
        Return a safe zero-weather dict when the API call fails.
        No thresholds are crossed so no spurious triggers fire.
        """
        logger.warning(
            f"[WEATHER] Returning safe defaults for zone '{zone_name}' "
            "due to fetch failure."
        )
        return {
            "zone":                 zone_name,
            "rain_mm_hr":           0.0,
            "temp_c":               0.0,
            "aqi":                  0,
            "disruption_triggered": False,
            "trigger_type":         None,
            "fetched_at":           datetime.now(timezone.utc).isoformat(),
            "raw_data":             {"error": "fetch_failed"},
        }
