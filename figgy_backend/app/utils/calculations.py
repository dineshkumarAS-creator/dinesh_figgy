"""
figgy_backend/app/utils/calculations.py
=========================================
Payout Math Engine — Figgy GigShield Parametric Insurance.

All monetary calculations for the claim payout pipeline live here.
Pure functions — no DB access, no side effects, fully unit-testable.

Module-level constants
----------------------
    COVERAGE_RATIO   : float = 0.66   — 66 % of income loss is covered
    TIER_CAPS        : dict          — INR cap per plan tier
    ELITE_SURGE_BONUS: int   = 100   — extra INR for Elite during extreme events
    ELITE_SURGE_MAX  : int   = 850   — hard ceiling for Elite + surge combined

Business rationale
------------------
- 66 % ratio: meaningful relief without incentivising fake disruptions
- Tier caps: higher premium → higher cap; protects company from unlimited exposure
- Elite surge bonus: rewards premium members during the worst events (rain > 70 mm/hr
  or AQI > 500) without breaking the financial model (capped at ₹850 total)

Example usage
-------------
    from app.utils.calculations import build_payout_summary

    worker  = {"avg_daily_earnings": 800, "daily_hours": 8, "tier": "Elite"}
    claim   = {"actual_earnings": 120, "time_window_hours": 3}
    weather = {"rain_mm_hr": 75, "aqi": 180}

    summary = build_payout_summary(worker, claim, weather)
    # {
    #   "expected_earnings" : 300,
    #   "actual_earnings"   : 120,
    #   "income_loss"       : 180,
    #   "raw_payout"        : 118,   # floor(180 × 0.66)
    #   "eligible_payout"   : 218,   # 118 + 100 surge = 218 < 850 ✓
    #   "tier"              : "Elite",
    #   "tier_cap"          : 750,
    #   "tier_cap_applied"  : False,  # raw < cap before surge
    #   "surge_bonus_applied": True,
    #   "coverage_pct"      : 66,
    #   "is_extreme"        : True,
    # }
"""

import logging
from typing import Optional

logger = logging.getLogger("FIGGY_CALC")

# ---------------------------------------------------------------------------
# Module-level constants  (single source of truth — import these, don't
# hard-code 0.66 / 300 / 500 / 750 anywhere else in the codebase)
# ---------------------------------------------------------------------------

COVERAGE_RATIO    : float = 0.66    # 66 % of income loss is paid out

TIER_CAPS         : dict[str, int] = {
    "Lite":  300,   # ₹300  cap — entry plan
    "Smart": 500,   # ₹500  cap — mid plan
    "Elite": 750,   # ₹750  cap — premium plan (+ surge possible)
}

ELITE_SURGE_BONUS : int = 100       # extra ₹100 for Elite on extreme events
ELITE_SURGE_MAX   : int = 850       # absolute hard ceiling for Elite + surge

DEFAULT_DAILY_HOURS       : int = 8
DEFAULT_AVG_DAILY_EARNINGS: int = 600   # Chennai delivery partner median (INR)

# Extreme disruption thresholds (triggers Elite surge bonus)
_EXTREME_RAIN_MM_HR : float = 70.0
_EXTREME_AQI        : int   = 500


# ---------------------------------------------------------------------------
# 1. calculate_expected_earnings
# ---------------------------------------------------------------------------

def calculate_expected_earnings(
    worker: dict,
    time_window_hours: float,
) -> int:
    """
    Estimate how much the worker should have earned during the disruption
    window had no disruption occurred.

    Formula
    -------
        avg_hourly = avg_daily_earnings / daily_hours
        expected   = round(avg_hourly × time_window_hours)

    Parameters
    ----------
    worker            : dict — worker document; uses avg_daily_earnings, daily_hours
    time_window_hours : float — duration of the disruption window in hours

    Returns
    -------
    int — expected INR earnings (always ≥ 0)

    Example
    -------
        worker = {"avg_daily_earnings": 800, "daily_hours": 10}
        calculate_expected_earnings(worker, 3)
        # → round(80.0 × 3) = 240
    """
    avg_daily  = float(worker.get("avg_daily_earnings") or DEFAULT_AVG_DAILY_EARNINGS)
    daily_hrs  = float(worker.get("daily_hours")        or DEFAULT_DAILY_HOURS)

    if daily_hrs <= 0:
        logger.warning("[CALC] daily_hours ≤ 0 — defaulting to 8 hrs.")
        daily_hrs = DEFAULT_DAILY_HOURS

    if time_window_hours <= 0:
        logger.warning("[CALC] time_window_hours ≤ 0 — returning 0.")
        return 0

    avg_hourly = avg_daily / daily_hrs
    expected   = round(avg_hourly * time_window_hours)

    logger.debug(
        f"[CALC] expected_earnings: avg_hourly=₹{avg_hourly:.2f} × "
        f"{time_window_hours}h = ₹{expected}"
    )
    return max(0, expected)


# ---------------------------------------------------------------------------
# 2. calculate_income_loss
# ---------------------------------------------------------------------------

def calculate_income_loss(
    expected_earnings: int,
    actual_earnings: int,
) -> int:
    """
    Difference between what the worker should have earned and what they
    actually earned during the disruption window.

    The result is floored at 0 — we never record a negative loss
    (edge case: worker somehow earned more than average during the event).

    Parameters
    ----------
    expected_earnings : int — from calculate_expected_earnings()
    actual_earnings   : int — self-reported or platform-provided earnings

    Returns
    -------
    int — income loss in INR (≥ 0)

    Example
    -------
        calculate_income_loss(300, 80)   # → 220
        calculate_income_loss(300, 350)  # → 0  (no loss)
    """
    loss = int(expected_earnings) - int(actual_earnings)
    clamped = max(0, loss)

    logger.debug(
        f"[CALC] income_loss: expected=₹{expected_earnings} − "
        f"actual=₹{actual_earnings} = ₹{clamped}"
    )
    return clamped


# ---------------------------------------------------------------------------
# 3. is_extreme_disruption
# ---------------------------------------------------------------------------

def is_extreme_disruption(weather_data: dict) -> bool:
    """
    Return True if the weather event qualifies as 'extreme' for the purpose
    of the Elite surge bonus.

    Extreme conditions (any one sufficient):
        rain_mm_hr > 70    (above 'heavy' threshold of 60 mm/hr)
        aqi        > 500   (beyond 'Very Poor' AQI band)

    Parameters
    ----------
    weather_data : dict — zone weather dict from WeatherService.get_zone_weather()
                          or any dict with rain_mm_hr / aqi keys

    Returns
    -------
    bool

    Example
    -------
        is_extreme_disruption({"rain_mm_hr": 75, "aqi": 180})  # → True
        is_extreme_disruption({"rain_mm_hr": 50, "aqi": 480})  # → False
    """
    rain = float(weather_data.get("rain_mm_hr", 0) or 0)
    aqi  = int(  weather_data.get("aqi",        0) or 0)

    extreme = rain > _EXTREME_RAIN_MM_HR or aqi > _EXTREME_AQI

    logger.debug(
        f"[CALC] is_extreme: rain={rain} mm/hr, aqi={aqi} → {extreme}"
    )
    return extreme


# ---------------------------------------------------------------------------
# 4. calculate_eligible_payout
# ---------------------------------------------------------------------------

def calculate_eligible_payout(
    income_loss: int,
    tier: str,
    is_extreme: bool = False,
) -> dict:
    """
    Apply the 66 % coverage ratio, tier cap, and optional Elite surge bonus
    to produce the final eligible payout.

    Parameters
    ----------
    income_loss : int  — from calculate_income_loss()
    tier        : str  — "Lite" | "Smart" | "Elite"
    is_extreme  : bool — True if is_extreme_disruption() returned True

    Returns
    -------
    dict with keys:
        raw_payout         – int, floor(income_loss × COVERAGE_RATIO)
        tier_cap           – int, INR cap for the tier
        tier_cap_applied   – bool, True if raw_payout was clamped by tier cap
        surge_bonus_applied– bool, True if Elite surge bonus was added
        eligible_payout    – int, final INR amount to disburse (≥ 0)

    Example
    -------
        calculate_eligible_payout(500, "Elite", is_extreme=True)
        # raw = round(500 × 0.66) = 330
        # cap = 750  → not capped
        # surge → 330 + 100 = 430  (<= 850)
        # → { raw_payout: 330, tier_cap: 750, tier_cap_applied: False,
        #     surge_bonus_applied: True, eligible_payout: 430 }
    """
    raw_payout = round(income_loss * COVERAGE_RATIO)
    cap        = TIER_CAPS.get(tier, TIER_CAPS["Lite"])   # safe default

    capped_payout    = min(raw_payout, cap)
    tier_cap_applied = capped_payout < raw_payout

    # Elite surge bonus
    surge_applied = False
    final_payout  = capped_payout

    if tier == "Elite" and is_extreme:
        surged        = capped_payout + ELITE_SURGE_BONUS
        final_payout  = min(surged, ELITE_SURGE_MAX)
        surge_applied = True
        logger.debug(
            f"[CALC] Elite surge: {capped_payout} + {ELITE_SURGE_BONUS} "
            f"= {surged} (capped at {ELITE_SURGE_MAX}) → ₹{final_payout}"
        )

    final_payout = max(0, final_payout)

    logger.debug(
        f"[CALC] payout: income_loss=₹{income_loss} × {COVERAGE_RATIO} "
        f"= raw ₹{raw_payout} → capped ₹{capped_payout} "
        f"{'(cap hit)' if tier_cap_applied else ''} → final ₹{final_payout}"
    )

    return {
        "raw_payout":          raw_payout,
        "tier_cap":            cap,
        "tier_cap_applied":    tier_cap_applied,
        "surge_bonus_applied": surge_applied,
        "eligible_payout":     final_payout,
    }


# ---------------------------------------------------------------------------
# 5. build_payout_summary
# ---------------------------------------------------------------------------

def build_payout_summary(
    worker: dict,
    claim: dict,
    weather_data: Optional[dict] = None,
) -> dict:
    """
    Build the complete payout calculation summary for a claim.

    Chains all four calculation functions in order:
        1. calculate_expected_earnings()
        2. calculate_income_loss()
        3. is_extreme_disruption()
        4. calculate_eligible_payout()

    Parameters
    ----------
    worker       : dict — worker document (avg_daily_earnings, daily_hours, tier)
    claim        : dict — claim document (actual_earnings, time_window_hours)
    weather_data : dict | None — zone weather dict; if None, surge not applied

    Returns
    -------
    dict with keys:
        expected_earnings   – int, what worker should have earned
        actual_earnings     – int, what worker actually earned
        income_loss         – int, the difference
        raw_payout          – int, income_loss × coverage ratio (pre-cap)
        eligible_payout     – int, final payout after cap and surge
        tier                – str, worker's plan tier
        tier_cap            – int, INR cap in effect
        tier_cap_applied    – bool
        surge_bonus_applied – bool
        coverage_pct        – int (always 66)
        is_extreme          – bool

    Example
    -------
        worker  = {"avg_daily_earnings": 800, "daily_hours": 8, "tier": "Elite"}
        claim   = {"actual_earnings": 120, "time_window_hours": 3}
        weather = {"rain_mm_hr": 75, "aqi": 180}

        summary = build_payout_summary(worker, claim, weather)
        # expected_earnings  = 300  (100/hr × 3hr)
        # actual_earnings    = 120
        # income_loss        = 180
        # raw_payout         = 118  (round(180 × 0.66))
        # tier_cap_applied   = False (118 < 750)
        # surge_bonus_applied= True  (Elite + rain 75 > 70)
        # eligible_payout    = 218  (118 + 100 surge)
    """
    tier             = worker.get("tier", "Lite")
    time_window      = float(claim.get("time_window_hours", 0) or 0)
    actual_earnings  = int(claim.get("actual_earnings", 0) or 0)
    _weather         = weather_data or {}

    # Step 1 — expected earnings
    expected = calculate_expected_earnings(worker, time_window)

    # Step 2 — income loss
    loss = calculate_income_loss(expected, actual_earnings)

    # Step 3 — extreme event?
    extreme = is_extreme_disruption(_weather)

    # Step 4 — eligible payout
    payout_info = calculate_eligible_payout(loss, tier, is_extreme=extreme)

    summary = {
        "expected_earnings":    expected,
        "actual_earnings":      actual_earnings,
        "income_loss":          loss,
        "raw_payout":           payout_info["raw_payout"],
        "eligible_payout":      payout_info["eligible_payout"],
        "tier":                 tier,
        "tier_cap":             payout_info["tier_cap"],
        "tier_cap_applied":     payout_info["tier_cap_applied"],
        "surge_bonus_applied":  payout_info["surge_bonus_applied"],
        "coverage_pct":         int(COVERAGE_RATIO * 100),   # always 66
        "is_extreme":           extreme,
    }

    logger.info(
        f"[CALC] Payout summary — "
        f"loss=₹{loss}, eligible=₹{payout_info['eligible_payout']}, "
        f"tier={tier}, cap_hit={payout_info['tier_cap_applied']}, "
        f"surge={payout_info['surge_bonus_applied']}, extreme={extreme}"
    )
    return summary


# ---------------------------------------------------------------------------
# 6. calculate_payout  ← PRIMARY entry point for the parametric payout engine
# ---------------------------------------------------------------------------

# Surge multiplier table (Elite + RAIN only)
#   detected_value > 60 and <= 70 mm/hr → ×1.10
#   detected_value > 70 mm/hr           → ×1.20
_SURGE_BAND_LOW  : float = 60.0   # minimum to qualify for surge
_SURGE_BAND_HIGH : float = 70.0   # above this → higher multiplier
_SURGE_MULT_LOW  : float = 1.10
_SURGE_MULT_HIGH : float = 1.20
_ELITE_SURGE_CAP : int   = 750    # hard ceiling for Elite after surge

# Tier caps (mirrors TIER_CAPS but keyed lowercase for claim docs)
_TIER_CAPS_LOWER: dict[str, int] = {
    "lite":  300,
    "smart": 500,
    "elite": 750,
}


def calculate_payout(claim: dict, worker: dict) -> dict:
    """
    Primary payout calculation for Figgy GigShield parametric claims.

    Follows the exact product spec:
      1. EXPECTED_EARNINGS = (avg_daily_earnings / daily_hours) × window_hours
         where window_hours = (end_time - start_time).total_seconds() / 3600
      2. ACTUAL_EARNINGS   = claim.telemetry.delivery_count × per_delivery_rate
      3. INCOME_LOSS       = max(0, expected - actual)
      4. TIER CAP          = 300 (Lite) / 500 (Smart) / 750 (Elite)
      5. ELIGIBLE_PAYOUT   = min(INCOME_LOSS, tier_cap)
      6. SURGE BONUS       = Elite + RAIN + detected_value > 60:
                             ×1.10 if detected_value ≤ 70, else ×1.20
                             capped at ₹750 absolute maximum

    Parameters
    ----------
    claim  : dict — claim document, must contain:
                    start_time         str  ISO-8601 UTC
                    end_time           str  ISO-8601 UTC
                    trigger_type       str  "RAIN" | "AQI" | "CURFEW" | …
                    detected_value     num  live sensor reading
                    telemetry          dict { delivery_count, ... }  (optional)

    worker : dict — worker document, must contain:
                    avg_daily_earnings  num   INR per full shift
                    daily_hours         num   hours per full shift
                    per_delivery_rate   num   INR per completed delivery
                    tier                str   "Lite" | "Smart" | "Elite"
                                              (case-insensitive)

    Returns
    -------
    dict with keys:
        expected_earnings  : float
        actual_earnings    : float
        income_loss        : float
        tier_cap           : int
        surge_bonus_applied: bool
        surge_multiplier   : float   (1.0 when no surge)
        eligible_payout    : float
        breakdown_label    : str     e.g. "₹350 loss · capped at ₹300 (Lite tier)"

    Raises
    ------
    ValueError if start_time / end_time are missing or unparseable.
    """
    from datetime import datetime, timezone

    # ── 0. Worker defaults ──────────────────────────────────────────────────
    avg_daily        = float(worker.get("avg_daily_earnings") or DEFAULT_AVG_DAILY_EARNINGS)
    daily_hrs        = float(worker.get("daily_hours")        or DEFAULT_DAILY_HOURS)
    per_delivery_rate= float(worker.get("per_delivery_rate",  50))   # ₹50 default
    tier_raw         = str(worker.get("tier", "Lite")).strip()
    tier_key         = tier_raw.lower()                               # normalise
    tier_cap         = _TIER_CAPS_LOWER.get(tier_key, 300)

    # ── 1. Disruption window (hours) ────────────────────────────────────────
    start_str = claim.get("start_time", "")
    end_str   = claim.get("end_time",   "")

    try:
        start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end_dt   = datetime.fromisoformat(end_str.replace("Z",   "+00:00"))
        window_hours = max(0.0, (end_dt - start_dt).total_seconds() / 3600)
    except (ValueError, AttributeError) as exc:
        # Fallback: try claim.time_window_hours if timestamps are absent
        fallback = claim.get("time_window_hours")
        if fallback is not None:
            window_hours = float(fallback)
            logger.warning(
                f"[CALC] Could not parse timestamps ({exc}); "
                f"using time_window_hours={window_hours}"
            )
        else:
            raise ValueError(
                f"calculate_payout: cannot determine disruption window. "
                f"start_time='{start_str}', end_time='{end_str}'"
            ) from exc

    if daily_hrs <= 0:
        daily_hrs = DEFAULT_DAILY_HOURS

    # ── 2. Expected earnings ────────────────────────────────────────────────
    avg_hourly        = avg_daily / daily_hrs
    expected_earnings = avg_hourly * window_hours

    # ── 3. Actual earnings (from telemetry) ─────────────────────────────────
    telemetry       = claim.get("telemetry") or {}
    delivery_count  = int(telemetry.get("delivery_count", 0) or 0)
    actual_earnings = delivery_count * per_delivery_rate

    # ── 4. Income loss ──────────────────────────────────────────────────────
    income_loss = max(0.0, expected_earnings - actual_earnings)

    # ── 5. Base eligible payout (capped at tier cap) ────────────────────────
    eligible_payout = min(income_loss, float(tier_cap))

    # ── 6. Surge bonus  (Elite + RAIN + detected_value > 60) ────────────────
    trigger_type  = str(claim.get("trigger_type", "")).upper()
    detected      = float(claim.get("detected_value", 0) or 0)

    surge_applied     = False
    surge_multiplier  = 1.0

    if tier_key == "elite" and trigger_type == "RAIN" and detected > _SURGE_BAND_LOW:
        surge_multiplier = (
            _SURGE_MULT_HIGH if detected > _SURGE_BAND_HIGH else _SURGE_MULT_LOW
        )
        eligible_payout   = min(eligible_payout * surge_multiplier, float(_ELITE_SURGE_CAP))
        surge_applied     = True
        logger.info(
            f"[CALC] Elite surge applied: ×{surge_multiplier} "
            f"(rain={detected} mm/hr) → ₹{eligible_payout:.0f}"
        )

    # Round to nearest rupee for display
    eligible_payout = round(eligible_payout, 2)

    # ── 7. Human-readable breakdown label ───────────────────────────────────
    capped = income_loss > tier_cap
    parts  = [f"₹{income_loss:.0f} loss"]
    if capped:
        parts.append(f"capped at ₹{tier_cap} ({tier_raw} tier)")
    if surge_applied:
        parts.append(f"×{surge_multiplier} rain surge → ₹{eligible_payout:.0f}")
    breakdown_label = " · ".join(parts)

    result = {
        "expected_earnings":   round(expected_earnings, 2),
        "actual_earnings":     round(actual_earnings,   2),
        "income_loss":         round(income_loss,       2),
        "tier_cap":            tier_cap,
        "surge_bonus_applied": surge_applied,
        "surge_multiplier":    surge_multiplier,
        "eligible_payout":     eligible_payout,
        "breakdown_label":     breakdown_label,
    }

    logger.info(
        f"[CALC] calculate_payout → loss=₹{income_loss:.0f}, "
        f"eligible=₹{eligible_payout:.0f}, tier={tier_raw}, "
        f"surge={surge_applied} (×{surge_multiplier})"
    )
    return result


# ---------------------------------------------------------------------------
# 7. estimate_payout_preview
#    Lightweight estimate for the Flutter parametric screen BEFORE claim filed.
#    Does NOT need telemetry — assumes actual_earnings = 0 (worst case).
# ---------------------------------------------------------------------------

def estimate_payout_preview(
    worker: dict,
    disruption_hours: float,
    trigger_type: str  = "RAIN",
    detected_value: float = 0.0,
) -> dict:
    """
    Estimate the maximum payout a worker could receive for an ongoing disruption.

    Used by GET /api/claim/calculate_preview/<worker_id> — called by Flutter
    before a claim is filed to show "you may receive up to ₹X".

    Assumptions
    -----------
    - actual_earnings = 0  (worst-case: worker stops working completely)
    - delivery_count  = 0

    Parameters
    ----------
    worker           : dict  — worker document
    disruption_hours : float — hours of disruption so far (from Flutter slider)
    trigger_type     : str   — "RAIN" | "AQI" | "CURFEW" (uppercase)
    detected_value   : float — live sensor reading (mm/hr for RAIN, AQI index, etc.)

    Returns
    -------
    Same dict shape as calculate_payout() + extra key:
        "is_preview" : True   — signals this is an estimate, not a filed claim
    """
    # Build a synthetic claim doc so we can reuse calculate_payout()
    from datetime import datetime, timedelta, timezone

    now   = datetime.now(timezone.utc)
    start = (now - timedelta(hours=disruption_hours)).isoformat()
    end   = now.isoformat()

    synthetic_claim = {
        "start_time":     start,
        "end_time":       end,
        "trigger_type":   trigger_type.upper(),
        "detected_value": detected_value,
        "telemetry":      {"delivery_count": 0},   # worst-case
    }

    preview = calculate_payout(synthetic_claim, worker)
    preview["is_preview"]       = True
    preview["disruption_hours"] = round(disruption_hours, 2)
    preview["trigger_type"]     = trigger_type.upper()
    preview["detected_value"]   = detected_value

    return preview


# ---------------------------------------------------------------------------
# 7. predict_income_loss — Disruption Radar auto-protection
# ---------------------------------------------------------------------------

def predict_income_loss(worker_id: str, zone_id: str, risk_score: float) -> dict:
    """
    Predict income loss for a worker in a zone and optionally trigger an auto-claim.
    
    Steps:
    1. Fetch worker's historical avg hourly earnings for current hour + day
       (MVP: use mock_generator.py, deterministic by worker_id)
    2. Fetch actual earnings today from worker record (mock: 0)
    3. expected_inr = avg_hourly * hours_worked_today (min 1 hour floor)
    4. loss_inr = max(0, expected_inr - actual_inr)
    5. If loss_inr >= INCOME_LOSS_THRESHOLD AND risk_score >= RISK_SCORE_THRESHOLD:
       -> Trigger auto-claim
    6. Return prediction dict with loss and claim status
    
    Parameters
    ----------
    worker_id : str — worker UUID
    zone_id : str — zone ID (A, B, C, D)
    risk_score : float — 0–100 from DisruptionScorer
    
    Returns
    -------
    dict — {
        "expected_inr": float,
        "actual_inr": float,
        "loss_inr": float,
        "claim_triggered": bool,
        "claim_id": str | None
    }
    """
    from app.models import db_handler
    from config import Config
    
    # 1. Fetch worker (mock for MVP)
    worker = None
    try:
        worker = db_handler.get_worker(worker_id)
    except Exception:
        pass
    
    if not worker:
        # Mock worker for MVP
        worker = {
            "worker_id": worker_id,
            "avg_daily_earnings": DEFAULT_AVG_DAILY_EARNINGS,
            "daily_hours": DEFAULT_DAILY_HOURS,
            "zone": zone_id,
            "tier": "Smart"
        }
    
    # 2. Get actual earnings today (mock: 0 for MVP)
    actual_inr = 0.0
    
    # 3. Calculate expected earnings (min 1 hour)
    avg_daily = float(worker.get("avg_daily_earnings", DEFAULT_AVG_DAILY_EARNINGS))
    daily_hrs = float(worker.get("daily_hours", DEFAULT_DAILY_HOURS))
    avg_hourly = avg_daily / daily_hrs if daily_hrs > 0 else 0
    hours_worked = max(1.0, 1.0)  # MVP: assume 1 hour min
    expected_inr = avg_hourly * hours_worked
    
    # 4. Calculate loss
    loss_inr = max(0.0, expected_inr - actual_inr)
    
    # 5. Check thresholds and trigger auto-claim if needed
    claim_triggered = False
    claim_id = None
    
    income_threshold = getattr(Config, 'INCOME_LOSS_THRESHOLD', 200)
    risk_threshold = getattr(Config, 'RISK_SCORE_THRESHOLD', 60)
    
    if loss_inr >= income_threshold and risk_score >= risk_threshold:
        try:
            # Generate claim_id
            claim_id_val = _generate_claim_id()
            
            # Create auto-claim document
            claim_doc = {
                "claim_id": claim_id_val,
                "worker_id": worker_id,
                "claim_type": "auto",
                "claim_source": "disruption_radar",
                "disruption_type": zone_id,
                "zone": zone_id,
                "start_time": datetime.utcnow().isoformat() + "Z",
                "end_time": datetime.utcnow().isoformat() + "Z",
                "time_window_hours": 1.0,
                "estimated_loss": int(loss_inr),
                "actual_earnings": int(actual_inr),
                "income_loss": int(loss_inr),
                "eligible_payout": None,
                "tier": worker.get("tier", "Smart"),
                "proof_urls": [],
                "description": f"Auto-claim triggered by Disruption Radar (risk_score={risk_score:.1f})",
                "status": "approved",  # Auto-approved for MVP
                "payout_status": "pending",
                "fraud_risk": None,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "resolved_at": None
            }
            
            # Save claim
            db_handler.save_claim(claim_doc)
            claim_id = claim_id_val
            claim_triggered = True
            logger.info(f"[RADAR] Auto-claim {claim_id} triggered for worker {worker_id} (loss=₹{loss_inr:.0f}, risk={risk_score:.1f})")
        except Exception as e:
            logger.error(f"[RADAR] Error triggering auto-claim for {worker_id}: {e}")
    
    return {
        "expected_inr": round(expected_inr, 2),
        "actual_inr": round(actual_inr, 2),
        "loss_inr": round(loss_inr, 2),
        "claim_triggered": claim_triggered,
        "claim_id": claim_id
    }


def _generate_claim_id() -> str:
    """Generate a unique claim ID in format FIG-XXXXXXXX."""
    import random
    import string
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"FIG-{random_part}"
