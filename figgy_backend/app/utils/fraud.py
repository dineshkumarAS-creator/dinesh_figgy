"""
figgy_backend/app/utils/fraud.py
==================================
Fraud Scoring Engine — Figgy GigShield Parametric Insurance.

Rule-based, additive scoring system that evaluates each claim before payout.
No ML required: every flag is fully explainable to regulators and workers.

Usage
-----
    from app.utils.fraud import score_fraud_risk, apply_fraud_decision

    result  = score_fraud_risk(claim_doc, worker_doc)
    # → { risk_level, score, flags, action, breakdown }

    applied = apply_fraud_decision(claim_id, result)
    # → bool (True = decision persisted)

Score bands
-----------
    0  – 29  → low    → instant_payout
    30 – 59  → medium → soft_verify   (1-hr hold, live location ping)
    60 – 100 → high   → manual_review (admin queue, 24-48 hr SLA)

Flag catalogue
--------------
    high_delivery_rate_during_disruption  (+35)
    high_gps_movement                     (+30)
    inflated_loss_estimate                (+25)
    gps_spoofing_detected                 (+40)  ← dominant; can push straight to high
    missing_gps_data                      (+15)  ← soft penalty; not treated as high

Edge-case policy
----------------
    Missing GPS logs  → +15 pts (medium-leaning) — NOT instant high
    Zero time window  → treated as 1 hr to avoid division-by-zero
    Missing worker avg_daily_earnings → defaults to ₹600 (Chennai median)
"""

import logging
import math
from datetime import datetime, timezone
from typing import Optional

from app.models import db_handler, ClaimStatus

logger = logging.getLogger("FIGGY_FRAUD")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Score → risk band boundaries
_BAND_LOW_MAX    = 29
_BAND_MEDIUM_MAX = 59

# Flag point values
_PTS_HIGH_DELIVERY_RATE = 35
_PTS_HIGH_GPS_MOVEMENT  = 30
_PTS_INFLATED_LOSS      = 25
_PTS_GPS_SPOOFING       = 40
_PTS_MISSING_GPS        = 15   # soft penalty — missing data ≠ proven fraud

# Thresholds
_MAX_DELIVERY_RATE      = 4.0    # orders / hr during disruption
_MAX_GPS_DISTANCE_KM    = 15.0   # km movement during claimed disruption
_LOSS_MULTIPLIER        = 1.3    # max_realistic_loss = avg_hourly × hours × 1.3
_GPS_MAX_SPEED_KMPH     = 120.0  # beyond this = impossible for delivery bike
_DEFAULT_AVG_EARNINGS   = 600    # INR/day — Chennai delivery partner median
_WORKING_HOURS_PER_DAY  = 8      # divisor for avg_hourly calculation


# ---------------------------------------------------------------------------
# Internal — GPS continuity check
# ---------------------------------------------------------------------------

def _check_gps_continuity(gps_logs: list[dict]) -> bool:
    """
    Detect GPS teleportation between consecutive log entries.

    Parameters
    ----------
    gps_logs : list of dicts, each containing:
        { "lat": float, "lon": float, "timestamp": str (ISO-8601) }

    Returns
    -------
    True  — GPS movement is physically plausible (no spoofing detected)
    False — at least one consecutive pair implies speed > 120 km/hr

    Notes
    -----
    Uses the Haversine formula for accurate great-circle distance.
    Pairs with identical timestamps are skipped (divide-by-zero guard).
    """
    if not gps_logs or len(gps_logs) < 2:
        return True   # not enough points to detect spoofing

    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0  # Earth radius in km
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi  = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _parse_ts(ts: str) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    for i in range(len(gps_logs) - 1):
        p1, p2 = gps_logs[i], gps_logs[i + 1]
        try:
            lat1, lon1 = float(p1["lat"]), float(p1["lon"])
            lat2, lon2 = float(p2["lat"]), float(p2["lon"])
        except (KeyError, TypeError, ValueError):
            continue   # malformed point — skip pair

        t1 = _parse_ts(p1.get("timestamp", ""))
        t2 = _parse_ts(p2.get("timestamp", ""))

        if t1 is None or t2 is None:
            continue   # can't compute speed without timestamps

        dt_hours = abs((t2 - t1).total_seconds()) / 3600.0
        if dt_hours == 0:
            continue   # same timestamp → skip

        dist_km = _haversine_km(lat1, lon1, lat2, lon2)
        speed_kmph = dist_km / dt_hours

        if speed_kmph > _GPS_MAX_SPEED_KMPH:
            logger.debug(
                f"[FRAUD] GPS teleport detected: {speed_kmph:.1f} km/hr "
                f"between ({lat1},{lon1}) and ({lat2},{lon2})."
            )
            return False   # spoofing confirmed

    return True   # all pairs are physically plausible


# ---------------------------------------------------------------------------
# Public — score_fraud_risk
# ---------------------------------------------------------------------------

def score_fraud_risk(claim: dict, worker: dict) -> dict:
    """
    Evaluate fraud risk for a claim.

    Parameters
    ----------
    claim  : dict — claim document (from db_handler or auto-created)
    worker : dict — worker document from db_handler

    Returns
    -------
    dict with keys:
        risk_level : "low" | "medium" | "high"
        score      : int 0–100
        flags      : list[str] — triggered flag names
        action     : "instant_payout" | "soft_verify" | "manual_review"
        breakdown  : dict — per-flag score contribution for auditability
    """
    score       = 0
    flags       = []
    breakdown   = {}

    # ── Safe field extraction ────────────────────────────────────────────────
    avg_daily        = worker.get("avg_daily_earnings", _DEFAULT_AVG_EARNINGS) or _DEFAULT_AVG_EARNINGS
    avg_hourly       = avg_daily / _WORKING_HOURS_PER_DAY

    delivery_count   = claim.get("delivery_count", 0) or 0
    gps_distance_km  = claim.get("gps_distance_km", None)
    estimated_loss   = claim.get("estimated_loss", 0) or 0
    gps_logs         = claim.get("gps_logs", None)

    # time_window_hours: guard against 0 / missing
    raw_hours = claim.get("time_window_hours", 0)
    time_window_hours = float(raw_hours) if raw_hours and float(raw_hours) > 0 else 1.0

    # ── FLAG 1: High delivery rate during claimed disruption (+35) ───────────
    delivery_rate = delivery_count / time_window_hours
    if delivery_rate > _MAX_DELIVERY_RATE:
        score += _PTS_HIGH_DELIVERY_RATE
        flags.append("high_delivery_rate_during_disruption")
        breakdown["high_delivery_rate_during_disruption"] = {
            "points":        _PTS_HIGH_DELIVERY_RATE,
            "delivery_rate": round(delivery_rate, 2),
            "threshold":     _MAX_DELIVERY_RATE,
        }
        logger.debug(
            f"[FRAUD] FLAG1 triggered: delivery_rate={delivery_rate:.2f} "
            f"> {_MAX_DELIVERY_RATE} orders/hr (+{_PTS_HIGH_DELIVERY_RATE})"
        )

    # ── FLAG 2: Excessive GPS movement (+30) ────────────────────────────────
    if gps_distance_km is None:
        # Missing GPS data — soft penalty instead of hard flag
        score += _PTS_MISSING_GPS
        flags.append("missing_gps_data")
        breakdown["missing_gps_data"] = {
            "points": _PTS_MISSING_GPS,
            "reason": "gps_distance_km not provided; soft penalty applied",
        }
        logger.debug(f"[FRAUD] GPS distance missing — soft penalty +{_PTS_MISSING_GPS}")
    elif float(gps_distance_km) > _MAX_GPS_DISTANCE_KM:
        pts = _PTS_HIGH_GPS_MOVEMENT
        score += pts
        flags.append("high_gps_movement")
        breakdown["high_gps_movement"] = {
            "points":           pts,
            "gps_distance_km":  round(float(gps_distance_km), 2),
            "threshold_km":     _MAX_GPS_DISTANCE_KM,
        }
        logger.debug(
            f"[FRAUD] FLAG2 triggered: gps_distance={gps_distance_km} km "
            f"> {_MAX_GPS_DISTANCE_KM} km (+{pts})"
        )

    # ── FLAG 3: Inflated loss claim (+25) ────────────────────────────────────
    max_realistic_loss = avg_hourly * time_window_hours * _LOSS_MULTIPLIER
    if estimated_loss > max_realistic_loss:
        score += _PTS_INFLATED_LOSS
        flags.append("inflated_loss_estimate")
        breakdown["inflated_loss_estimate"] = {
            "points":            _PTS_INFLATED_LOSS,
            "estimated_loss":    estimated_loss,
            "max_realistic":     round(max_realistic_loss, 2),
            "avg_hourly":        round(avg_hourly, 2),
            "time_window_hours": time_window_hours,
        }
        logger.debug(
            f"[FRAUD] FLAG3 triggered: estimated_loss=₹{estimated_loss} "
            f"> max_realistic=₹{max_realistic_loss:.2f} (+{_PTS_INFLATED_LOSS})"
        )

    # ── FLAG 4: GPS spoofing — teleportation (+40, dominant) ─────────────────
    if gps_logs is not None:
        if not _check_gps_continuity(gps_logs):
            score += _PTS_GPS_SPOOFING
            flags.append("gps_spoofing_detected")
            breakdown["gps_spoofing_detected"] = {
                "points": _PTS_GPS_SPOOFING,
                "reason": f"Consecutive GPS pair exceeded {_GPS_MAX_SPEED_KMPH} km/hr",
            }
            logger.warning(
                f"[FRAUD] FLAG4 GPS SPOOFING detected for claim "
                f"'{claim.get('claim_id', '?')}' (+{_PTS_GPS_SPOOFING})"
            )
    # else: gps_logs not provided — already handled by FLAG 2 missing GPS check

    # ── Cap score at 100 ─────────────────────────────────────────────────────
    score = min(score, 100)

    # ── Determine risk band ──────────────────────────────────────────────────
    if score <= _BAND_LOW_MAX:
        risk_level = "low"
        action     = "instant_payout"
    elif score <= _BAND_MEDIUM_MAX:
        risk_level = "medium"
        action     = "soft_verify"
    else:
        risk_level = "high"
        action     = "manual_review"

    result = {
        "risk_level": risk_level,
        "score":      score,
        "flags":      flags,
        "action":     action,
        "breakdown":  breakdown,
    }

    logger.info(
        f"[FRAUD] Claim '{claim.get('claim_id', '?')}' — "
        f"score={score}, risk={risk_level}, action={action}, flags={flags}"
    )
    return result


# ---------------------------------------------------------------------------
# Public — apply_fraud_decision
# ---------------------------------------------------------------------------

def apply_fraud_decision(claim_id: str, fraud_result: dict) -> bool:
    """
    Persist the fraud scoring decision and transition the claim status.

    Decision matrix
    ---------------
        low    → status="approved"      — eligible_payout calculated, payout queued
        medium → status="verifying"     — 1-hr soft verify hold, live location ping
        high   → status="manual_review" — admin queue, worker notified of 24-48 hr SLA

    Parameters
    ----------
    claim_id     : str  — e.g. "FIG-8821"
    fraud_result : dict — output of score_fraud_risk()

    Returns
    -------
    bool — True if the decision was persisted successfully, False otherwise
    """
    claim = db_handler.get_claim(claim_id)
    if not claim:
        logger.error(f"[FRAUD] apply_fraud_decision: claim '{claim_id}' not found.")
        return False

    risk_level = fraud_result.get("risk_level", "high")
    score      = fraud_result.get("score", 100)
    flags      = fraud_result.get("flags", [])
    action     = fraud_result.get("action", "manual_review")

    common_fields = {
        "fraud_risk":      risk_level,
        "fraud_score":     score,
        "fraud_flags":     flags,
        "fraud_action":    action,
        "fraud_breakdown": fraud_result.get("breakdown", {}),
    }

    # ── LOW risk → approve and calculate payout ──────────────────────────────
    if risk_level == "low":
        worker_id = claim.get("worker_id", "")
        workers   = db_handler.get_all_workers()
        worker    = next((w for w in workers if w.get("worker_id") == worker_id), {})

        income_loss  = claim.get("income_loss") or claim.get("estimated_loss", 0)
        tier         = worker.get("tier", claim.get("tier", "Smart"))
        tier_max     = _get_tier_max(tier)
        eligible_payout = min(int(income_loss * 0.66), tier_max)

        extra = {
            **common_fields,
            "income_loss":     income_loss,
            "eligible_payout": eligible_payout,
            "payout_status":   "pending",
            "pow_gps_ok":      len([f for f in flags if "gps" in f]) == 0,
            "pow_delivery_ok": "high_delivery_rate_during_disruption" not in flags,
        }

        ok = db_handler.update_claim_status(claim_id, ClaimStatus.APPROVED.value, extra)
        if ok:
            logger.info(
                f"[FRAUD] ✅ Claim '{claim_id}' APPROVED — "
                f"eligible_payout=₹{eligible_payout} score={score}"
            )
            _notify_worker(claim, "approved", eligible_payout=eligible_payout)
        return ok

    # ── MEDIUM risk → soft verify hold ───────────────────────────────────────
    if risk_level == "medium":
        extra = {
            **common_fields,
            "pow_gps_ok":      None,
            "pow_delivery_ok": None,
            "payout_status":   "pending",
        }
        ok = db_handler.update_claim_status(claim_id, ClaimStatus.VERIFYING.value, extra)
        if ok:
            logger.info(
                f"[FRAUD] 🟡 Claim '{claim_id}' → VERIFYING (soft verify) "
                f"score={score} flags={flags}"
            )
            _notify_worker(claim, "soft_verify")
        return ok

    # ── HIGH risk → manual review queue ──────────────────────────────────────
    extra = {
        **common_fields,
        "rejection_reason": f"High fraud score ({score}/100). Flags: {', '.join(flags)}",
        "payout_status":    "on_hold",
    }
    ok = db_handler.update_claim_status(claim_id, ClaimStatus.MANUAL_REVIEW.value, extra)
    if ok:
        logger.warning(
            f"[FRAUD] 🔴 Claim '{claim_id}' → MANUAL_REVIEW "
            f"score={score} flags={flags}"
        )
        _notify_worker(claim, "manual_review")
    return ok


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_tier_max(tier: str) -> int:
    """Return INR tier max payout — matches claims.py TIER_MAX_PAYOUT."""
    _TIER_MAX = {"Lite": 200, "Smart": 400, "Elite": 600}
    return _TIER_MAX.get(tier, 200)


def _notify_worker(claim: dict, decision: str, eligible_payout: int = 0) -> None:
    """
    Stub: log the notification that would be sent to the worker.

    In production, replace with:
      - FCM push notification to the Flutter app
      - SMS via Twilio / MSG91
      - WhatsApp via Gupshup / Interakt

    Parameters
    ----------
    claim          : dict — claim document
    decision       : str  — "approved" | "soft_verify" | "manual_review"
    eligible_payout: int  — INR amount (only relevant for "approved")
    """
    worker_id = claim.get("worker_id", "?")
    claim_id  = claim.get("claim_id",  "?")

    messages = {
        "approved": (
            f"✅ [NOTIFY] Worker {worker_id} — Claim {claim_id} APPROVED. "
            f"₹{eligible_payout} will be credited to your UPI within 24 hrs."
        ),
        "soft_verify": (
            f"🟡 [NOTIFY] Worker {worker_id} — Claim {claim_id} needs a quick "
            "location confirmation. Open Figgy app to confirm."
        ),
        "manual_review": (
            f"🔴 [NOTIFY] Worker {worker_id} — Claim {claim_id} is under manual review. "
            "Our team will contact you within 24-48 hrs."
        ),
    }
    logger.info(messages.get(decision, f"[NOTIFY] Claim {claim_id} decision: {decision}"))


# ===========================================================================
# Proof-of-Work Engine
# ===========================================================================

def score_claim(claim: dict, worker: dict, telemetry: dict) -> dict:
    """
    Evaluate a claim using the Proof-of-Work engine with three primary checks.
    
    Returns a worker-friendly structured dictionary intended for the
    Flutter frontend's Proof-of-Work status UI.
    """
    flags = []
    checks = []
    
    # ── Safe extraction ──────────────────────────────────────────────────────
    avg_earnings = float(worker.get("avg_daily_earnings", _DEFAULT_AVG_EARNINGS))
    avg_deliveries = float(worker.get("avg_daily_deliveries", 12.0))
    
    claimed_loss = float(claim.get("estimated_loss", claim.get("income_loss", 0)))
    delivery_count = float(telemetry.get("delivery_count", 0))
    gps_km = float(telemetry.get("gps_km_during_disruption", 0))

    # 1. CLAIMED_LOSS_CHECK
    label_1 = "Income loss looks reasonable"
    if claimed_loss > (avg_earnings * 2):
        flags.append("CLAIMED_LOSS_CHECK")
        checks.append({
            "name": "CLAIMED_LOSS_CHECK",
            "status": "FLAG",
            "reason": "Claimed loss exceeds 2× daily average",
            "worker_friendly_label": label_1
        })
    else:
        checks.append({
            "name": "CLAIMED_LOSS_CHECK",
            "status": "PASS",
            "reason": "Claimed loss is within expected variance",
            "worker_friendly_label": label_1
        })

    # 2. ACTIVITY_VELOCITY_CHECK
    label_2 = "Delivery activity during rain"
    if delivery_count > (avg_deliveries * 0.8):
        flags.append("ACTIVITY_VELOCITY_CHECK")
        checks.append({
            "name": "ACTIVITY_VELOCITY_CHECK",
            "status": "FLAG",
            "reason": "Delivery count unusually high during disruption — expected slowdown not observed",
            "worker_friendly_label": label_2
        })
    else:
        checks.append({
            "name": "ACTIVITY_VELOCITY_CHECK",
            "status": "PASS",
            "reason": "Activity matches typical disruption slowdown",
            "worker_friendly_label": label_2
        })

    # 3. GPS_DISTANCE_CHECK
    label_3 = "Your location during disruption"
    if gps_km > 15:
        flags.append("GPS_DISTANCE_CHECK")
        checks.append({
            "name": "GPS_DISTANCE_CHECK",
            "status": "FLAG",
            "reason": "GPS shows significant movement — inconsistent with reported blockage",
            "worker_friendly_label": label_3
        })
    else:
        checks.append({
            "name": "GPS_DISTANCE_CHECK",
            "status": "PASS",
            "reason": "Location data verifies disruption zone presence",
            "worker_friendly_label": label_3
        })

    # ── Risk Scoring ─────────────────────────────────────────────────────────
    if len(flags) == 0:
        risk_level = "LOW"
        confidence = "Activity matches real delivery patterns with high confidence"
        instant_payout = True
    elif len(flags) == 1:
        risk_level = "MEDIUM"
        confidence = "Some unusual activity detected; requires soft verification"
        instant_payout = False
    else:
        risk_level = "HIGH"
        confidence = "Significant anomalies detected; requires manual review"
        instant_payout = False

    # ── Activity Timeline (Mock generated based on status) ───────────────────
    timeline = []
    
    # Simple synthetic timeline for Flutter UI
    timeline.append({
        "time": "08:00 AM",
        "event": "Device Authenticated",
        "icon": "device"
    })
    if gps_km > 0:
        timeline.append({
            "time": "In Disruption Window",
            "event": f"Logged {gps_km:.1f} km movement",
            "icon": "location"
        })
    if delivery_count > 0:
        timeline.append({
            "time": "In Disruption Window",
            "event": f"Completed {int(delivery_count)} deliveries",
            "icon": "package"
        })
        
    timeline.append({
        "time": "Now",
        "event": "Proof-of-Work check complete",
        "icon": "shield"
    })

    return {
        "risk_level": risk_level,
        "checks": checks,
        "activity_timeline": timeline,
        "confidence_statement": confidence,
        "eligible_for_instant_payout": instant_payout
    }
