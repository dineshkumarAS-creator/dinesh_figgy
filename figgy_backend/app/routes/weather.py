"""
figgy_backend/app/routes/weather.py
=====================================
GET /api/weather/zone/<zone_id>

Returns real-time weather conditions for a single delivery zone, PLUS
the evaluated status of all parametric thresholds defined in
app/config/thresholds.py.

Used by:
  - radar_screen.dart — live weather metrics, disruption banners
  - Flutter insurance_screen.dart — show which thresholds are active
  - Admin dashboard — zone health monitoring

Valid zones: North, South, East, West, Central
"""

import logging
import os
from datetime import datetime, timezone

from flask import Blueprint, jsonify

from app.utils.weather_client import get_zone_conditions, ZONE_COORDS
from app.config.thresholds import TRIGGER_THRESHOLDS, evaluate_threshold

logger = logging.getLogger("FIGGY_WEATHER_ROUTE")

weather_bp = Blueprint("weather", __name__, url_prefix="/api/weather")

VALID_ZONES = set(ZONE_COORDS.keys())   # {"North", "South", "East", "West", "Central"}

# Human-readable disruption labels for the Flutter frontend
_DISRUPTION_LABELS: dict[str, str] = {
    "RAIN":   "Heavy Rainfall",
    "AQI":    "Dangerous Air Quality",
    "CURFEW": "Active Curfew",
    "HEAT":   "Extreme Heat",
}


# ---------------------------------------------------------------------------
# GET /api/weather/zone/<zone_id>
# ---------------------------------------------------------------------------

@weather_bp.route("/zone/<zone_id>", methods=["GET"])
def get_zone_weather(zone_id: str):
    """
    GET /api/weather/zone/<zone_id>

    Returns:
    {
        zone           : str,
        rain_mm_hr     : float,
        temp_c         : float,
        aqi            : int,
        curfew_active  : bool,
        source         : str,           // "live" | "demo" | "cache" | "fallback"
        last_updated   : str,           // ISO-8601 UTC
        disruption_triggered : bool,    // true if ANY threshold breached
        thresholds     : {              // status of every configured threshold
            RAIN   : { triggered, label, detected_value, threshold_value, unit, limit },
            AQI    : { ... },
            CURFEW : { ... }
        },
        active_triggers : [             // list of breached trigger_type strings
            "RAIN", ...
        ]
    }

    Demo mode
    ---------
    Set DEMO_MODE=true in .env. North zone will have rain_mm_hr=52 which
    crosses the RAIN threshold (> 40 mm/hr).
    """
    # Normalise: "north" → "North"
    zone_key = zone_id.strip().capitalize()

    if zone_key not in VALID_ZONES:
        return jsonify({
            "error":       f"Unknown zone '{zone_id}'",
            "valid_zones": sorted(VALID_ZONES),
        }), 400

    try:
        conditions = get_zone_conditions(zone_key)

        # ── Evaluate every threshold ─────────────────────────────────────────
        thresholds_status: dict[str, dict] = {}
        active_triggers:   list[str]       = []

        for trigger_type, cfg in TRIGGER_THRESHOLDS.items():
            field          = cfg["field"]
            detected_value = conditions.get(field)
            is_triggered   = evaluate_threshold(trigger_type, detected_value)

            thresholds_status[trigger_type] = {
                "triggered":       is_triggered,
                "label":           cfg["label"],
                "detected_value":  detected_value,
                "threshold_value": cfg["value"],
                "operator":        cfg["operator"],
                "unit":            cfg["unit"],
                "limit":           cfg.get("limit"),
            }

            if is_triggered:
                active_triggers.append(trigger_type)

        disruption_triggered = len(active_triggers) > 0

        # ── Build response ───────────────────────────────────────────────────
        response = {
            "zone":                 conditions["zone_id"],
            "rain_mm_hr":           conditions["rain_mm_hr"],
            "temp_c":               conditions["temp_c"],
            "aqi":                  conditions["aqi"],
            "curfew_active":        conditions["curfew_active"],
            "source":               conditions.get("source", "unknown"),
            "last_updated":         conditions.get("fetched_at",
                                        datetime.now(timezone.utc).isoformat()),
            "disruption_triggered": disruption_triggered,
            "thresholds":           thresholds_status,
            "active_triggers":      active_triggers,
            # Convenience field for simple Flutter checks
            "disruption_label":     _DISRUPTION_LABELS.get(active_triggers[0])
                                    if active_triggers else None,
            # Demo mode flag so Flutter can display a banner
            "demo_mode":            os.getenv("DEMO_MODE", "false").lower()
                                    in ("true", "1", "yes"),
        }

        logger.info(
            f"[WEATHER_ROUTE] zone={zone_key} | "
            f"rain={response['rain_mm_hr']} mm/hr, "
            f"aqi={response['aqi']}, "
            f"curfew={response['curfew_active']}, "
            f"active_triggers={active_triggers}"
        )

        return jsonify(response), 200

    except Exception as exc:
        logger.error(f"[WEATHER_ROUTE] Error for zone '{zone_key}': {exc}", exc_info=True)
        return jsonify({
            "error": "Failed to fetch weather data",
            "zone":  zone_key,
        }), 500
