"""
figgy_backend/app/utils/scheduler.py
======================================
Parametric Trigger Engine — Figgy GigShield.

Uses Flask-APScheduler to run a cron-style job every 15 minutes (configurable).
For each active zone it calls get_zone_conditions(), evaluates every entry in
TRIGGER_THRESHOLDS, and — when a threshold is crossed — POSTs internally to
/api/claim/auto_trigger with the simplified payload:

    { zone_id, trigger_type, detected_value }

Legacy internal call (zone / rain_mm_hr / temp_c / aqi payload) is also kept
so the existing test suite and admin demo endpoints continue to work.

Setup
-----
Call `init_scheduler(app)` from create_app() in app/__init__.py.
"""

import logging
import requests as http_requests
from datetime import datetime
from flask import Flask
from flask_apscheduler import APScheduler

from app.utils.weather_client import get_zone_conditions, ZONE_COORDS
from app.config.thresholds import TRIGGER_THRESHOLDS, evaluate_threshold

logger = logging.getLogger("FIGGY_SCHEDULER")

# ---------------------------------------------------------------------------
# Scheduler singleton
# ---------------------------------------------------------------------------
scheduler = APScheduler()


# ---------------------------------------------------------------------------
# Internal: fire auto_trigger for a single (zone, trigger_type) pair
# ---------------------------------------------------------------------------

def _call_auto_trigger(app: Flask, zone_id: str, trigger_type: str, detected_value):
    """
    Calls the /api/claim/auto_trigger route handler directly (no HTTP round-trip)
    using Flask's test_request_context.

    Payload sent:  { zone_id, trigger_type, detected_value }
    """
    from app.routes.claims import auto_trigger as _auto_trigger_fn

    payload = {
        "zone_id":        zone_id,
        "trigger_type":   trigger_type,
        "detected_value": detected_value,
        # Legacy fields kept for backward-compat with existing route logic
        "zone":           zone_id,
    }

    with app.test_request_context(
        "/api/claim/auto_trigger",
        method="POST",
        json=payload,
        headers={"Content-Type": "application/json"},
    ):
        response = _auto_trigger_fn()

    # Unpack Flask response tuple (response, status_code) or plain response
    if isinstance(response, tuple):
        resp_obj = response[0]
    else:
        resp_obj = response

    try:
        data = resp_obj.get_json()
    except Exception:
        data = {}

    if data and data.get("triggered"):
        logger.info(
            f"[SCHEDULER] ⚡ Zone '{zone_id}' | trigger={trigger_type} | "
            f"value={detected_value} → "
            f"{data.get('workers_notified', 0)} workers notified, "
            f"claims: {data.get('claims_created', [])}"
        )
    else:
        logger.debug(
            f"[SCHEDULER] Zone '{zone_id}' | trigger={trigger_type} — "
            f"auto_trigger returned no action (reason: {data.get('reason', 'unknown')})."
        )


# ---------------------------------------------------------------------------
# Main scheduled job — runs every 15 minutes
# ---------------------------------------------------------------------------

def poll_weather_and_trigger():
    """
    APScheduler job: polls weather conditions for every active zone via
    get_zone_conditions(), evaluates TRIGGER_THRESHOLDS, and fires
    auto_trigger claims for each breached threshold.

    Scheduled: every 15 minutes (configurable via SCHEDULER_INTERVAL_MINUTES).
    """
    app = scheduler.app
    if app is None:
        logger.error("[SCHEDULER] No Flask app attached to scheduler.")
        return

    logger.info(f"[SCHEDULER] Weather poll started for {len(ZONE_COORDS)} zones.")

    for zone_id in ZONE_COORDS:
        try:
            conditions = get_zone_conditions(zone_id)

            any_triggered = False
            for trigger_type, cfg in TRIGGER_THRESHOLDS.items():
                field          = cfg["field"]
                detected_value = conditions.get(field)

                if detected_value is None:
                    continue

                if evaluate_threshold(trigger_type, detected_value):
                    any_triggered = True
                    logger.info(
                        f"[SCHEDULER] ⚡ THRESHOLD BREACHED — zone='{zone_id}' "
                        f"trigger={trigger_type} field={field} "
                        f"detected={detected_value} > limit={cfg['value']}"
                    )
                    _call_auto_trigger(app, zone_id, trigger_type, detected_value)

            if not any_triggered:
                logger.debug(
                    f"[SCHEDULER] Zone '{zone_id}' — all clear. "
                    f"(rain={conditions.get('rain_mm_hr')} mm/hr, "
                    f"aqi={conditions.get('aqi')}, "
                    f"curfew={conditions.get('curfew_active')})"
                )

        except Exception as exc:
            logger.error(f"[SCHEDULER] Error processing zone '{zone_id}': {exc}", exc_info=True)

    logger.info("[SCHEDULER] Weather poll complete.")


# ---------------------------------------------------------------------------
# Stale claim cleanup job — runs every 30 minutes
# ---------------------------------------------------------------------------

def cleanup_stale_claims():
    """
    Cron job (runs every 30 minutes):
    Finds claims stuck in [verifying / under_review / approved] for > 2 hours
    and escalates them to manual_review with stale_reason=pipeline_timeout.
    """
    app = scheduler.app
    if app is None:
        return

    with app.app_context():
        from app.models import db_handler
        from app.utils.claim_processor import send_claim_notification
        from datetime import datetime, timedelta

        threshold_dt = datetime.utcnow() - timedelta(hours=2)
        all_claims   = db_handler.get_all_claims()
        stale_count  = 0

        for claim in all_claims:
            status         = claim.get("status")
            updated_at_str = claim.get("updated_at", claim.get("created_at", ""))

            if status not in ("verifying", "under_review", "approved"):
                continue

            try:
                ts_str     = updated_at_str.replace("Z", "+00:00")
                updated_at = datetime.fromisoformat(ts_str)
                if updated_at.tzinfo:
                    updated_at = updated_at.replace(tzinfo=None)
            except Exception:
                continue

            if updated_at < threshold_dt:
                claim_id  = claim.get("claim_id")
                worker_id = claim.get("worker_id")

                db_handler.update_claim_status(
                    claim_id,
                    "manual_review",
                    {"stale_reason": "pipeline_timeout"},
                )
                claim["status"] = "manual_review"
                send_claim_notification(worker_id, "manual_review", claim)
                logger.info(f"[CLEANUP] Claim {claim_id} → manual_review (pipeline_timeout).")
                stale_count += 1

        if stale_count:
            logger.info(f"[CLEANUP] Marked {stale_count} stale claim(s).")


# ---------------------------------------------------------------------------
# init_scheduler — called from create_app()
# ---------------------------------------------------------------------------

def init_scheduler(app: Flask):
    """
    Attach APScheduler to the Flask app and register all cron jobs.
    Call once from create_app() in app/__init__.py.
    """
    interval_minutes = int(app.config.get("SCHEDULER_INTERVAL_MINUTES", 15))
    app.config.setdefault("SCHEDULER_API_ENABLED", True)

    scheduler.init_app(app)

    # Weather poll — every 15 min (parametric trigger engine)
    scheduler.add_job(
        id="weather_poll",
        func=poll_weather_and_trigger,
        trigger="interval",
        minutes=interval_minutes,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Stale claim cleanup — every 30 min
    scheduler.add_job(
        id="stale_claim_cleanup",
        func=cleanup_stale_claims,
        trigger="interval",
        minutes=30,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()

    logger.info(
        f"[SCHEDULER] ✅ Weather poll registered — every {interval_minutes} min. "
        "Running immediate startup poll…"
    )
    try:
        poll_weather_and_trigger()
    except Exception as exc:
        logger.warning(f"[SCHEDULER] Startup poll failed (non-fatal): {exc}")
