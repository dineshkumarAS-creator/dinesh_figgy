"""
figgy_backend/run.py
====================
Figgy GigShield — Application Entry Point.

Bootstraps the Flask app and wires up a standalone APScheduler
BackgroundScheduler that fires the parametric weather trigger every
15 minutes across all five Chennai delivery zones.

Scheduler vs Flask-APScheduler (already in __init__.py)
---------------------------------------------------------
Flask-APScheduler (scheduler.py / init_scheduler) coordinates with the
Flask app lifecycle and requires an app context. This standalone
BackgroundScheduler in run.py is the explicit entry-point scheduler that
runs check_weather_and_trigger() — the higher-level job that:
  1. Calls WeatherService per zone (with 10-min caching)
  2. Enforces tier eligibility (Lite is rain-only)
  3. Deduplicates — skips workers who already have a claim today
  4. Creates 'auto' claims and queues payout

Both schedulers are safe to run together because They poll to different
job IDs and the claim deduplication guard prevents duplicate payouts.
"""

import atexit
import logging
import os
import random
import string
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

from app import create_app
from app.models import db_handler, CLAIM_SCHEMA_TEMPLATE, memory_claims
from app.utils.fraud import score_fraud_risk, apply_fraud_decision
from app.utils.calculations import build_payout_summary

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("FIGGY_RUN")

# ---------------------------------------------------------------------------
# Flask app — created once at module level so the scheduler can reference it
# ---------------------------------------------------------------------------
app: Flask = create_app()

# ---------------------------------------------------------------------------
# Tier eligibility matrix
# ---------------------------------------------------------------------------
# trigger_type values from WeatherService._build_result():
#   "rain_heavy"    → rain > 40 mm/hr  (Smart + Elite only)
#   "rain_extreme"  → rain > 60 mm/hr  (All tiers: Lite + Smart + Elite)
#   "heat"          → temp > 42 °C     (Smart + Elite only)
#   "aqi"           → aqi  > 400       (Smart + Elite only)

_TIER_ELIGIBILITY: dict[str, set[str]] = {
    "rain_heavy":   {"Smart", "Elite"},
    "rain_extreme": {"Lite", "Smart", "Elite"},
    "heat":         {"Smart", "Elite"},
    "aqi":          {"Smart", "Elite"},
}

# From claims.py — kept in sync
_TIER_MAX_PAYOUT: dict[str, int] = {
    "Lite":  200,
    "Smart": 400,
    "Elite": 600,
}

# trigger_type → human-readable claim_type label
_TRIGGER_TO_CLAIM_TYPE: dict[str, str] = {
    "rain_heavy":   "Heavy Rain",
    "rain_extreme": "Heavy Rain",
    "heat":         "Extreme Heat",
    "aqi":          "High AQI",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_claim_id() -> str:
    digits = "".join(random.choices(string.digits, k=4))
    return f"FIG-{digits}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# 1. create_auto_claim
# ---------------------------------------------------------------------------

def create_auto_claim(worker: dict, weather: dict) -> dict:
    """
    Persist a new auto claim in 'verifying' state.

    Parameters
    ----------
    worker  : dict — worker document from db_handler
    weather : dict — zone weather dict returned by WeatherService.get_zone_weather()

    Returns
    -------
    dict — the saved claim document (without Mongo _id)
    """
    worker_id    = worker.get("worker_id", "")
    tier         = worker.get("tier", "Smart")
    trigger_type = weather.get("trigger_type", "")
    claim_type   = _TRIGGER_TO_CLAIM_TYPE.get(trigger_type, "Heavy Rain")
    now          = _now_iso()

    # Unique claim_id — retry up to 10 times to avoid collision
    claim_id = ""
    for _ in range(10):
        candidate = _generate_claim_id()
        if not db_handler.get_claim(candidate):
            claim_id = candidate
            break
    if not claim_id:
        claim_id = _generate_claim_id()   # last-resort; low probability of collision

    avg_earnings  = worker.get("avg_daily_earnings", 600)
    income_loss   = avg_earnings // 2            # conservative 50 % estimate
    eligible      = min(int(income_loss * 0.66), _TIER_MAX_PAYOUT.get(tier, 200))

    claim_doc = {
        **CLAIM_SCHEMA_TEMPLATE,
        # ── Identity ──────────────────────────────────────────────────────
        "claim_id":             claim_id,
        "worker_id":            worker_id,
        "claim_source":         "auto",
        "claim_type":           claim_type,
        # ── Zone & trigger ────────────────────────────────────────────────
        "zone":                 weather.get("zone", ""),
        "rain_mm_hr":           weather.get("rain_mm_hr", 0.0),
        "temp_c":               weather.get("temp_c", 0.0),
        "aqi":                  weather.get("aqi", 0),
        # ── Financial ─────────────────────────────────────────────────────
        "estimated_loss":       avg_earnings // 2,
        "income_loss":          income_loss,
        "eligible_payout":      eligible,
        "tier_max_payout":      _TIER_MAX_PAYOUT.get(tier, 200),
        # ── Payout ────────────────────────────────────────────────────────
        "payout_upi":           worker.get("upi_id", ""),
        "payout_status":        "pending",
        # ── Status ────────────────────────────────────────────────────────
        "status":               "verifying",
        # ── Timestamps ────────────────────────────────────────────────────
        "created_at":           now,
        "updated_at":           now,
    }

    db_handler.save_claim(claim_doc)
    logger.info(
        f"[CREATE_CLAIM] ✅ {claim_id} — worker={worker_id} "
        f"zone={weather.get('zone')} trigger={trigger_type} payout=₹{eligible}"
    )
    return claim_doc


# ---------------------------------------------------------------------------
# 2. verify_and_payout  — full fraud + payout pipeline
# ---------------------------------------------------------------------------

def verify_and_payout(claim: dict, weather: dict | None = None) -> None:
    """
    Run the full post-claim pipeline for an auto-created claim:

    Steps
    -----
    1. Fetch the worker document so the fraud scorer has context.
    2. ``score_fraud_risk(claim, worker)``  — additive rule-based scoring.
    3. ``build_payout_summary(worker, claim, weather)``  — exact INR amount.
    4. Merge the payout figures into the claim dict before persisting.
    5. ``apply_fraud_decision(claim_id, fraud_result)``  — transitions status
       to ``approved`` / ``verifying`` / ``manual_review`` accordingly.

    Parameters
    ----------
    claim   : dict — claim document returned by create_auto_claim()
    weather : dict | None — zone weather dict from WeatherService;
              passed through to is_extreme_disruption() for Elite surge bonus.
    """
    claim_id  = claim.get("claim_id",  "?")
    worker_id = claim.get("worker_id", "?")

    # ── 1. Fetch worker ──────────────────────────────────────────────────────
    workers = db_handler.get_all_workers()
    worker  = next((w for w in workers if w.get("worker_id") == worker_id), {})

    if not worker:
        logger.warning(
            f"[VERIFY] Worker '{worker_id}' not found — "
            f"claim '{claim_id}' cannot be verified. Skipping."
        )
        return

    # ── 2. Fraud scoring ─────────────────────────────────────────────────────
    fraud_result = score_fraud_risk(claim, worker)
    logger.info(
        f"[VERIFY] Claim '{claim_id}' fraud score: "
        f"{fraud_result['score']}/100 → {fraud_result['risk_level']} "
        f"({fraud_result['action']})"
    )

    # ── 3. Payout calculation ────────────────────────────────────────────────
    _weather = weather or {}
    payout_summary = build_payout_summary(worker, claim, _weather)

    # ── 4. Merge payout fields into fraud_result so apply_fraud_decision ─────
    #    can write them in a single DB update call.
    fraud_result["_payout"] = payout_summary   # internal carry — not persisted directly

    # Patch claim in-memory so apply_fraud_decision finds income_loss / tier
    claim["income_loss"]  = payout_summary["income_loss"]
    claim["eligible_payout"] = payout_summary["eligible_payout"]
    claim["tier"]         = worker.get("tier", "Smart")

    # ── 5. Apply decision → persists status transition ───────────────────────
    ok = apply_fraud_decision(claim_id, fraud_result)
    if ok:
        logger.info(
            f"[VERIFY] ✅ Claim '{claim_id}' decision applied: "
            f"{fraud_result['action']} | payout=₹{payout_summary['eligible_payout']}"
        )
    else:
        logger.error(
            f"[VERIFY] ❌ Failed to apply decision for claim '{claim_id}'."
        )


# ---------------------------------------------------------------------------
# 3. check_weather_and_trigger  — the main scheduled job
# ---------------------------------------------------------------------------

def check_weather_and_trigger() -> None:
    """
    Parametric trigger job — runs every 15 minutes via BackgroundScheduler.

    For each Chennai zone:
      a) Fetch weather via WeatherService (cached, 10-min TTL)
      b) If disruption triggered → iterate active workers in that zone
      c) Skip workers whose tier isn't eligible for this trigger type
      d) Skip workers who already have a claim filed today
      e) Create 'verifying' auto claim + queue PoW verification
    """
    # BackgroundScheduler threads have no Flask context — push one explicitly
    with app.app_context():
        from app.utils.weather import WeatherService

        zones = ["North", "South", "East", "West", "Central"]
        svc   = WeatherService()

        logger.info(f"[SCHEDULER] ⏱ Weather poll started — {len(zones)} zones.")

        for zone_name in zones:
            try:
                weather = svc.get_zone_weather(zone_name)

                if not weather.get("disruption_triggered"):
                    logger.debug(f"[SCHEDULER] Zone '{zone_name}' — clear, no trigger.")
                    continue

                trigger_type = weather.get("trigger_type")
                eligible_tiers = _TIER_ELIGIBILITY.get(trigger_type, set())

                logger.info(
                    f"[SCHEDULER] ⚡ Zone '{zone_name}' triggered: {trigger_type} | "
                    f"eligible tiers: {eligible_tiers}"
                )

                # Active workers in this zone (all tiers — filter below)
                active_workers = db_handler.get_workers_by_zone_and_status(
                    zone_name, "active"
                )
                logger.info(
                    f"[SCHEDULER] Zone '{zone_name}' — {len(active_workers)} active workers."
                )

                claims_filed = 0

                for worker in active_workers:
                    worker_id = worker.get("worker_id", "")
                    tier      = worker.get("tier", "Smart")

                    # ── Tier eligibility check ─────────────────────────────
                    if tier not in eligible_tiers:
                        logger.debug(
                            f"[SCHEDULER] Worker {worker_id} ({tier}) skipped — "
                            f"tier not eligible for '{trigger_type}'."
                        )
                        continue

                    # ── Deduplication: no duplicate claim today ────────────
                    existing = db_handler.get_todays_claim(worker_id)
                    if existing:
                        logger.debug(
                            f"[SCHEDULER] Worker {worker_id} already has claim "
                            f"'{existing.get('claim_id')}' today — skipping."
                        )
                        continue

                    # ── Create claim + queue verification ──────────────────
                    claim = create_auto_claim(worker, weather)
                    verify_and_payout(claim, weather=weather)  # weather → Elite surge bonus
                    claims_filed += 1

                logger.info(
                    f"[SCHEDULER] Zone '{zone_name}' — {claims_filed} claims created."
                )

            except Exception as exc:
                logger.error(
                    f"[SCHEDULER] Error processing zone '{zone_name}': {exc}",
                    exc_info=True,
                )

        logger.info("[SCHEDULER] ✅ Weather poll complete.")


# ---------------------------------------------------------------------------
# 4. Scheduler bootstrap
# ---------------------------------------------------------------------------

def _build_scheduler() -> BackgroundScheduler:
    """Instantiate and configure the BackgroundScheduler."""
    interval_minutes = int(app.config.get("SCHEDULER_INTERVAL_MINUTES", 15))

    bg_scheduler = BackgroundScheduler(
        job_defaults={
            "coalesce":      True,   # collapse missed runs into one
            "max_instances": 1,      # no overlapping runs
        }
    )
    bg_scheduler.add_job(
        func=check_weather_and_trigger,
        trigger="interval",
        minutes=interval_minutes,
        id="figgy_weather_trigger",
        replace_existing=True,
        name="Figgy Parametric Weather Trigger",
    )
    return bg_scheduler


# ---------------------------------------------------------------------------
# Main — scheduler starts here, Flask follows
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    host  = os.getenv("HOST", "0.0.0.0")
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    # ------------------------------------------------------------------
    # Start BackgroundScheduler
    # ------------------------------------------------------------------
    bg_scheduler = _build_scheduler()
    bg_scheduler.start()
    logger.info(
        f"[SCHEDULER] ✅ BackgroundScheduler started — "
        f"interval={app.config.get('SCHEDULER_INTERVAL_MINUTES', 15)} min."
    )

    # Graceful shutdown when the process exits (Ctrl-C / SIGTERM)
    atexit.register(lambda: _shutdown_scheduler(bg_scheduler))

    # ------------------------------------------------------------------
    # (Optional) Fire once immediately on startup so you don't have to
    # wait up to 15 min during development. Remove for production.
    # ------------------------------------------------------------------
    if os.getenv("TRIGGER_ON_STARTUP", "True").lower() == "true":
        logger.info("[SCHEDULER] 🚀 Running immediate startup trigger poll …")
        try:
            check_weather_and_trigger()
        except Exception as exc:
            logger.error(f"[SCHEDULER] Startup poll failed (non-fatal): {exc}")

    # ------------------------------------------------------------------
    # Start Flask
    # ------------------------------------------------------------------
    logger.info(f"[APP] 🌐 Flask starting on {host}:{port}  debug={debug}")
    app.run(host=host, port=port, debug=debug, use_reloader=False)
    # NOTE: use_reloader=False is required when running APScheduler alongside
    # Flask dev server — the reloader forks the process which would start a
    # second scheduler instance and double-fire every job.


def _shutdown_scheduler(sched: BackgroundScheduler) -> None:
    """Cleanly stop the scheduler on process exit."""
    if sched.running:
        logger.info("[SCHEDULER] 🛑 Shutting down BackgroundScheduler …")
        sched.shutdown(wait=False)
