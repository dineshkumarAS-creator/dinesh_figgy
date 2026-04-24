"""
figgy_backend/app/config/thresholds.py
========================================
Parametric Trigger Thresholds — Figgy GigShield.

Single source of truth for all environmental trigger conditions.
Used by:
  - app/utils/weather_client.py  (evaluate conditions)
  - app/utils/scheduler.py       (decide which threshold fired)
  - app/routes/weather.py        (annotate live zone response for Flutter)
  - app/routes/claims.py         (auto_trigger route validation)
"""

# ---------------------------------------------------------------------------
# TRIGGER_THRESHOLDS
# ---------------------------------------------------------------------------
# Each key is the canonical trigger_type string used throughout the codebase.
#
# Fields:
#   field    — key in the conditions dict returned by get_zone_conditions()
#   operator — comparison operator as string: ">", ">=", "==", "<"
#   value    — threshold value; breach is detected when field <operator> value
#   label    — human-readable label shown to gig workers & admin UI
#   unit     — display unit for the Flutter frontend
#   limit    — payout cap / limit (₹) for this trigger type (optional)
# ---------------------------------------------------------------------------

TRIGGER_THRESHOLDS: dict[str, dict] = {
    "RAIN": {
        "field":    "rain_mm_hr",
        "operator": ">",
        "value":    40,
        "label":    "Rainfall Threshold",
        "unit":     "mm/hr",
        "limit":    50,           # ₹50 per-trigger payout cap for demo
    },
    "AQI": {
        "field":    "aqi",
        "operator": ">",
        "value":    400,
        "label":    "Pollution Level",
        "unit":     "AQI",
        "limit":    400,
    },
    "CURFEW": {
        "field":    "curfew_active",
        "operator": "==",
        "value":    True,
        "label":    "Curfew Status",
        "unit":     "boolean",
        # no "limit" key — curfew is boolean; payout capped by tier
    },
    "HEAT": {
        "field":    "temp_c",
        "operator": ">",
        "value":    42,
        "label":    "Extreme Heat",
        "unit":     "°C",
        "limit":    300,
    },
    "FLOOD": {
        "field":    "flood_alert",
        "operator": "==",
        "value":    True,
        "label":    "Flood Alert",
        "unit":     "boolean",
        "limit":    400,
    },
}


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def evaluate_threshold(trigger_type: str, detected_value) -> bool:
    """
    Returns True if detected_value crosses the threshold for trigger_type.

    Parameters
    ----------
    trigger_type  : str   — e.g. "RAIN", "AQI", "CURFEW"
    detected_value: any   — the live reading from get_zone_conditions()

    Returns
    -------
    bool — True if the threshold is breached, False otherwise.
    """
    cfg = TRIGGER_THRESHOLDS.get(trigger_type)
    if cfg is None or detected_value is None:
        return False

    op  = cfg["operator"]
    val = cfg["value"]

    if op == ">":
        return detected_value > val
    if op == ">=":
        return detected_value >= val
    if op == "<":
        return detected_value < val
    if op == "<=":
        return detected_value <= val
    if op == "==":
        return detected_value == val
    if op == "!=":
        return detected_value != val

    return False


def get_triggered_thresholds(conditions: dict) -> list[dict]:
    """
    Evaluate all TRIGGER_THRESHOLDS against a conditions dict.

    Parameters
    ----------
    conditions : dict — output of get_zone_conditions()

    Returns
    -------
    list of dicts, one per breached threshold:
      {trigger_type, field, detected_value, threshold_value, label, unit, limit}
    """
    triggered = []
    for trigger_type, cfg in TRIGGER_THRESHOLDS.items():
        field = cfg["field"]
        detected_value = conditions.get(field)

        if evaluate_threshold(trigger_type, detected_value):
            triggered.append({
                "trigger_type":    trigger_type,
                "field":           field,
                "detected_value":  detected_value,
                "threshold_value": cfg["value"],
                "label":           cfg["label"],
                "unit":            cfg["unit"],
                "limit":           cfg.get("limit"),
            })

    return triggered
