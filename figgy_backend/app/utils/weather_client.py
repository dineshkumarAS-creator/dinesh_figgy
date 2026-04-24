"""
figgy_backend/app/utils/weather_client.py
==========================================
Lightweight weather client for Figgy GigShield parametric engine.

Provides a single public function:

    get_zone_conditions(zone_id: str) -> dict

which returns a flat conditions dict suitable for direct evaluation
against TRIGGER_THRESHOLDS.

Demo Mode
---------
Set DEMO_MODE=true in .env to skip the OpenWeatherMap API entirely and
return hardcoded conditions with rain_mm_hr=52 (triggers the RAIN threshold).
This lets the full parametric pipeline run without any API key.

Live Mode
---------
Set OPENWEATHER_API_KEY in .env.
Calls:
  • https://api.openweathermap.org/data/2.5/weather       (rain + temp)
  • https://api.openweathermap.org/data/2.5/air_pollution (AQI)

Zones supported: North, South, East, West, Central (Chennai hubs)
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger("FIGGY_WEATHER_CLIENT")

# ---------------------------------------------------------------------------
# Zone coordinates (Chennai delivery hubs)
# ---------------------------------------------------------------------------

ZONE_COORDS: dict[str, tuple[float, float]] = {
    "North":   (13.1300, 80.2800),   # Perambur / Kolathur
    "South":   (12.9165, 80.1425),   # Tambaram / Pallavaram
    "East":    (13.0475, 80.2575),   # Mylapore / Adyar
    "West":    (13.0500, 80.1950),   # Valasaravakkam / Porur
    "Central": (13.0827, 80.2707),   # T Nagar / Nungambakkam
}

# ---------------------------------------------------------------------------
# OWM AQI band → approximate Indian AQI conversion
# OWM uses a 1–5 scale; mapped to AQI-IN breakpoints.
# ---------------------------------------------------------------------------

_OWM_AQI_TO_IN: dict[int, int] = {1: 50, 2: 100, 3: 200, 4: 300, 5: 500}

# ---------------------------------------------------------------------------
# In-process cache:  zone_id → {"data": dict, "fetched_at": float (epoch)}
# ---------------------------------------------------------------------------

_CACHE: dict[str, dict] = {}
_CACHE_TTL_SECONDS = 600   # 10 minutes — matches APScheduler 15-min interval
_FLOOD_STREAK: dict[str, int] = {}

# ---------------------------------------------------------------------------
# Demo / mock data
# ---------------------------------------------------------------------------

_DEMO_CONDITIONS: dict[str, dict] = {
    "North": {
        "rain_mm_hr":    52.0,   # ← deliberately > 40 to fire RAIN threshold
        "temp_c":        34.5,
        "aqi":           180,
        "curfew_active": False,
    },
    "South": {
        "rain_mm_hr":    4.2,
        "temp_c":        33.1,
        "aqi":           95,
        "curfew_active": False,
    },
    "East": {
        "rain_mm_hr":    88.0,
        "temp_c":        32.0,
        "aqi":           110,
        "flood_alert":   True,
        "curfew_active": False,
    },
    "West": {
        "rain_mm_hr":    6.0,
        "temp_c":        34.0,
        "aqi":           130,
        "curfew_active": False,
    },
    "Central": {
        "rain_mm_hr":    9.5,
        "temp_c":        44.0,
        "aqi":           160,
        "curfew_active": False,
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_zone_conditions(zone_id: str) -> dict:
    """
    Return the current environmental conditions for *zone_id*.

    Parameters
    ----------
    zone_id : str
        One of the registered zone names: "North", "South", "East",
        "West", "Central" (case-sensitive).

    Returns
    -------
    dict with keys:
        zone_id        – str, echoed zone identifier
        rain_mm_hr     – float, rainfall in the last hour (mm)
        temp_c         – float, current air temperature (°C)
        aqi            – int, approximate AQI-IN index
        curfew_active  – bool, always False from weather API
        fetched_at     – str, ISO-8601 UTC timestamp
        source         – str, "demo" | "live" | "cache" | "fallback"

    Notes
    -----
    - If DEMO_MODE=true in environment, returns hardcoded demo data
      (North zone has rain_mm_hr=52 to trigger the RAIN threshold).
    - If no OPENWEATHER_API_KEY, falls back to demo data and logs a warning.
    - Results are cached in-process for 10 minutes.
    """
    demo_mode = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")
    api_key   = os.getenv("OPENWEATHER_API_KEY", "").strip()

    # ── Demo mode (env flag or no API key) ──────────────────────────────────
    if demo_mode or not api_key:
        if demo_mode:
            logger.info(f"[WEATHER_CLIENT] DEMO_MODE — returning hardcoded conditions for zone '{zone_id}'.")
        else:
            logger.warning(
                f"[WEATHER_CLIENT] OPENWEATHER_API_KEY not set — "
                f"falling back to demo data for zone '{zone_id}'."
            )
        return _build_result(zone_id, _DEMO_CONDITIONS.get(zone_id, _DEMO_CONDITIONS["North"]), "demo")

    # ── Cache hit ────────────────────────────────────────────────────────────
    cached = _CACHE.get(zone_id)
    if cached and (time.monotonic() - cached["fetched_at"]) < _CACHE_TTL_SECONDS:
        logger.debug(f"[WEATHER_CLIENT] Cache hit for zone '{zone_id}'.")
        return {**cached["data"], "source": "cache"}

    # ── Live OWM fetch ───────────────────────────────────────────────────────
    if zone_id not in ZONE_COORDS:
        logger.error(
            f"[WEATHER_CLIENT] Unknown zone '{zone_id}'. "
            f"Valid zones: {list(ZONE_COORDS.keys())}. Returning fallback."
        )
        return _build_result(zone_id, _DEMO_CONDITIONS.get(zone_id, _DEMO_CONDITIONS["North"]), "fallback")

    try:
        raw = _fetch_live(zone_id, api_key)
        _CACHE[zone_id] = {"data": raw, "fetched_at": time.monotonic()}
        return raw

    except Exception as exc:
        logger.error(f"[WEATHER_CLIENT] Live fetch failed for zone '{zone_id}': {exc}. Returning fallback.")
        return _build_result(zone_id, _DEMO_CONDITIONS.get(zone_id, _DEMO_CONDITIONS["North"]), "fallback")


def invalidate_cache(zone_id: Optional[str] = None) -> None:
    """Clear the in-process cache for one zone or all zones."""
    if zone_id:
        _CACHE.pop(zone_id, None)
        _FLOOD_STREAK.pop(zone_id, None)
    else:
        _CACHE.clear()
        _FLOOD_STREAK.clear()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_live(zone_id: str, api_key: str) -> dict:
    """Call OWM Current Weather + Air Pollution APIs and return a conditions dict."""
    lat, lon = ZONE_COORDS[zone_id]

    # --- Step 1: Current weather (rain + temp) --------------------------------
    w_resp = requests.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
        timeout=8,
    )
    w_resp.raise_for_status()
    w_data = w_resp.json()

    rain_mm_hr: float = float(w_data.get("rain", {}).get("1h", 0.0))
    temp_c: float     = float(w_data["main"]["temp"])

    # --- Step 2: Air pollution (AQI) -----------------------------------------
    a_resp = requests.get(
        "https://api.openweathermap.org/data/2.5/air_pollution",
        params={"lat": lat, "lon": lon, "appid": api_key},
        timeout=8,
    )
    a_resp.raise_for_status()
    a_data = a_resp.json()

    owm_aqi_band: int = a_data["list"][0]["main"]["aqi"]   # 1–5
    aqi: int          = _OWM_AQI_TO_IN.get(owm_aqi_band, 50)

    raw_conditions = {
        "rain_mm_hr":    round(rain_mm_hr, 2),
        "temp_c":        round(temp_c, 1),
        "aqi":           aqi,
        "curfew_active": False,   # Curfew is not available from weather API
    }

    logger.info(
        f"[WEATHER_CLIENT] Live data for zone '{zone_id}': "
        f"rain={rain_mm_hr} mm/hr, temp={temp_c}°C, aqi={aqi}"
    )

    return _build_result(zone_id, raw_conditions, "live")


def _build_result(zone_id: str, raw: dict, source: str) -> dict:
    """Attach zone_id, fetched_at, and source to the raw conditions dict."""
    rain_mm_hr = float(raw.get("rain_mm_hr", 0.0))

    # Flood proxy: rain > 80 mm/hr for 3+ consecutive fresh readings.
    if "flood_alert" in raw:
        flood_alert = bool(raw.get("flood_alert"))
    else:
        _FLOOD_STREAK[zone_id] = (_FLOOD_STREAK.get(zone_id, 0) + 1) if rain_mm_hr > 80 else 0
        flood_alert = _FLOOD_STREAK[zone_id] >= 3

    return {
        "zone_id":       zone_id,
        "rain_mm_hr":    rain_mm_hr,
        "temp_c":        raw.get("temp_c", 0.0),
        "aqi":           raw.get("aqi", 0),
        "flood_alert":   flood_alert,
        "curfew_active": raw.get("curfew_active", False),
        "fetched_at":    datetime.now(timezone.utc).isoformat(),
        "source":        source,
    }
