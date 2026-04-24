"""
figgy_backend/app/routes/claims.py
===================================
Claims Blueprint for Figgy GigShield — Parametric Micro-Insurance.
Handles both the parametric auto-trigger pipeline and the manual claim
submission flow, converging on a single Razorpay UPI payout call.

Mount point: /api/claim
Blueprint name: claims_bp

Routes
------
POST  /api/claim/auto_trigger      — APScheduler cron, never called by user
POST  /api/claim/manual            — Worker taps "Submit Claim" in app
GET   /api/claim/status/<claim_id> — Polled every 5 s by claim_processing_screen
GET   /api/claim/list/<worker_id>  — Powers payout history on insurance_screen
POST  /api/claim/payout            — Internal only, called after claim approved
"""

import random
import string
import logging
import threading
import time
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
import razorpay

from app.models import db_handler, CLAIM_SCHEMA_TEMPLATE, ClaimStatus
from app.utils.calculations import build_payout_summary, TIER_CAPS
from app.utils.fraud import score_fraud_risk, apply_fraud_decision
from app.utils.payout import RazorpayPayoutService

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("FIGGY_CLAIMS")

# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------
claims_bp = Blueprint("claims", __name__, url_prefix="/api/claim")

# memory_claims and CLAIM_SCHEMA_TEMPLATE are imported from app.models (single source of truth)

# ---------------------------------------------------------------------------
# Tier → Max Payout mapping — sourced from calculations.py (single source of truth)
# ---------------------------------------------------------------------------
TIER_MAX_PAYOUT = TIER_CAPS   # {"Lite": 300, "Smart": 500, "Elite": 750}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_claim_id() -> str:
    """Generates a random unique claim ID: FIG- + 6 digits.
    Includes a safety collision check against the current database.
    """
    for _ in range(10): # try 10 times to find a unique ID
        digits = "".join(random.choices(string.digits, k=6))
        claim_id = f"FIG-{digits}"
        if not db_handler.get_claim(claim_id):
            return claim_id
            
    # Fallback if 10 collisions (mathematically improbable with 6 digits)
    return f"FIG-{int(random.random() * 10**8)}"


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _find_claim(claim_id: str) -> dict | None:
    return db_handler.get_claim(claim_id)


def _find_worker(worker_id: str) -> dict | None:
    """Look up a worker from the existing in-memory / DB store."""
    workers = db_handler.get_all_workers()
    for w in workers:
        if w.get("worker_id") == worker_id:
            return w
    return None


def _active_workers_in_zone(zone: str) -> list[dict]:
    """Return all workers where zone matches and policy_status == 'active'."""
    workers = db_handler.get_all_workers()
    return [
        w for w in workers
        if w.get("zone", "").lower() == zone.lower()
        and w.get("policy_status") == "active"
    ]


def _calculate_payout(income_loss: int, tier: str, weather: dict | None = None) -> int:
    """
    Delegate to calculations.build_payout_summary() so Elite surge bonus
    and the single-source TIER_CAPS are always respected.
    """
    dummy_worker = {"avg_daily_earnings": 600, "daily_hours": 8, "tier": tier}
    dummy_claim  = {"actual_earnings": 0, "time_window_hours": 1,
                    "income_loss": income_loss}
    summary = build_payout_summary(dummy_worker, dummy_claim, weather or {})
    return summary["eligible_payout"]


def _process_claim_async(app, claim_id: str, worker_id: str):
    """Demo-only async lifecycle for auto-trigger visibility in Flutter."""
    with app.app_context():
        claim = db_handler.get_claim(claim_id)
        worker = _find_worker(worker_id)
        if not claim or not worker:
            logger.warning(f"[AUTO-ASYNC] Claim/worker missing for {claim_id}.")
            return

        # Step 1: keep claim in under_review briefly so UI can render first stage
        time.sleep(2)
        db_handler.update_claim_status(claim_id, ClaimStatus.VERIFYING.value)

        # Step 2: run fraud scoring, then force low-risk in demo flow for lifecycle visibility
        time.sleep(2)
        claim = db_handler.get_claim(claim_id) or claim
        fraud_result = score_fraud_risk(claim, worker)
        fraud_result["risk_level"] = "low"
        fraud_result["action"] = "instant_payout"
        apply_fraud_decision(claim_id, fraud_result)
        db_handler.update_claim_status(claim_id, ClaimStatus.APPROVED.value, {"processing_step": 8})

        # Step 3: initiate payout and mark final status
        approved_claim = db_handler.get_claim(claim_id) or {}
        amount = int(approved_claim.get("eligible_payout") or approved_claim.get("estimated_loss", 0))
        payout_result = RazorpayPayoutService().initiate_payout(worker, claim_id, amount)

        if payout_result.get("status") == "error":
            db_handler.update_claim_status(
                claim_id,
                "payment_failed",
                {
                    "payout_error": payout_result.get("error_message"),
                    "retry_eligible": True,
                    "last_upi_attempted": worker.get("upi_id", ""),
                },
            )
            return

        db_handler.update_claim_status(
            claim_id,
            ClaimStatus.PAID.value,
            {"payout_reference": payout_result.get("payout_id", "PO_PENDING")},
        )


# ===========================================================================
# ROUTE 1 — POST /api/claim/auto_trigger
# ===========================================================================

# Mapping from TRIGGER_THRESHOLDS keys → human-readable disruption type
_TRIGGER_TYPE_LABELS: dict[str, str] = {
    "RAIN":   "Heavy Rain",
    "AQI":    "High AQI",
    "CURFEW": "Curfew",
    "FLOOD":  "Flood Warning",
    # Legacy heat key (old scheduler path)
    "HEAT":   "Extreme Heat",
}


@claims_bp.route("/auto_trigger", methods=["POST"])
def auto_trigger():
    """
    Called by APScheduler every 15 min per active zone — NOT by the user.

    Accepts TWO payload shapes (both supported for backward-compat):

    Shape A — NEW (from updated scheduler using weather_client + thresholds):
        { zone_id, trigger_type, detected_value }

    Shape B — LEGACY (from older scheduler / tests / admin demo):
        { zone, rain_mm_hr, temp_c, aqi, timestamp }

    Finds all workers in the zone with active policies, creates a
    'verifying' claim for each, and dispatches PoW verification jobs.
    """
    try:
        data      = request.get_json() or {}
        timestamp = data.get("timestamp", _now_iso())

        # ── Detect payload shape ─────────────────────────────────────────
        is_new_payload = "trigger_type" in data and "zone_id" in data

        if is_new_payload:
            # ── Shape A: new simplified payload ──────────────────────────
            zone_id        = data.get("zone_id", "")
            trigger_type   = data.get("trigger_type", "").upper()   # e.g. "RAIN"
            detected_value = data.get("detected_value")

            # zone_id is often the same as zone (e.g. "North"), normalise
            zone = zone_id

            # Map trigger_type → claim_type label shown in UI
            claim_type = _TRIGGER_TYPE_LABELS.get(trigger_type, trigger_type)

            # Reconstruct minimal weather snapshot for claim doc
            rain_mm_hr = float(detected_value) if trigger_type == "RAIN" else 0.0
            aqi        = int(detected_value)   if trigger_type == "AQI"  else 0
            temp_c     = 0.0

            rain_triggered = (trigger_type == "RAIN")

            logger.info(
                f"[AUTO] Shape-A payload — zone='{zone}' trigger={trigger_type} "
                f"detected_value={detected_value}"
            )

        else:
            # ── Shape B: legacy payload ───────────────────────────────────
            zone       = data.get("zone", "")
            rain_mm_hr = float(data.get("rain_mm_hr", 0))
            temp_c     = float(data.get("temp_c", 0))
            aqi        = int(data.get("aqi", 0))

            rain_triggered = rain_mm_hr > 40
            aqi_triggered  = aqi > 400
            heat_triggered = temp_c > 42

            if not any([rain_triggered, aqi_triggered, heat_triggered]):
                return jsonify({
                    "triggered":  False,
                    "reason":     "No threshold crossed — no action taken.",
                    "zone":       zone,
                    "rain_mm_hr": rain_mm_hr,
                    "temp_c":     temp_c,
                    "aqi":        aqi,
                }), 200

            if rain_triggered:
                claim_type   = "Heavy Rain"
                trigger_type = "RAIN"
            elif heat_triggered:
                claim_type   = "Extreme Heat"
                trigger_type = "HEAT"
            else:
                claim_type   = "High AQI"
                trigger_type = "AQI"

            logger.info(
                f"[AUTO] Shape-B payload — zone='{zone}' claim_type={claim_type} "
                f"rain={rain_mm_hr} temp={temp_c} aqi={aqi}"
            )

        # ── 1. Fetch active workers in zone ──────────────────────────────
        active_workers = _active_workers_in_zone(zone)

        # ── 1.1 Bulk duplicate check — skip workers already claimed today ─
        worker_ids      = [w.get("worker_id") for w in active_workers]
        already_claimed = db_handler.get_workers_with_active_claims_today(worker_ids, claim_type)

        if already_claimed:
            logger.info(
                f"[AUTO] Filtered {len(already_claimed)} workers with existing "
                f"{claim_type} claims today."
            )
            active_workers = [
                w for w in active_workers
                if w.get("worker_id") not in already_claimed
            ]

        claims_created: list[str] = []

        # ── 2. Create an 'under_review' claim for each eligible worker ───
        for worker in active_workers:
            worker_id = worker.get("worker_id", "")
            tier      = worker.get("tier", "Smart")

            # Lite tier: only pay out on rain events
            if tier == "Lite" and not rain_triggered:
                logger.info(
                    f"[AUTO] Skipping worker {worker_id}: Lite tier "
                    f"does not cover {claim_type}."
                )
                continue

            claim_id  = _generate_claim_id()
            claim_doc = {
                **CLAIM_SCHEMA_TEMPLATE,
                "claim_id":          claim_id,
                "worker_id":         worker_id,
                "claim_source":      "auto",
                "claim_type":        "auto",
                "disruption_type":   claim_type,
                "trigger_type":      trigger_type,    # NEW — links to TRIGGER_THRESHOLDS key
                "zone":              zone,
                "time_window_hours": 4.0,
                "rain_mm_hr":        rain_mm_hr,
                "temp_c":            temp_c,
                "aqi":               aqi,
                "estimated_loss":    worker.get("avg_daily_earnings", 600) // 2,
                "tier_max_payout":   TIER_MAX_PAYOUT.get(tier, 200),
                "tier":              tier,
                "payout_upi":        worker.get("upi_id", ""),
                "status":            ClaimStatus.UNDER_REVIEW.value,
                "created_at":        timestamp,
                "updated_at":        _now_iso(),
            }

            db_handler.save_claim(claim_doc)
            claims_created.append(claim_id)

            # ── 3. Start async demo lifecycle progression ──────────────────
            app_obj = current_app._get_current_object()
            threading.Thread(
                target=_process_claim_async,
                args=(app_obj, claim_id, worker_id),
                daemon=True,
            ).start()
            logger.info(
                f"[AUTO] Claim {claim_id} created for worker {worker_id} "
                f"(zone={zone}, trigger={trigger_type}). Async lifecycle started."
            )

        return jsonify({
            "triggered":        True,
            "trigger_type":     trigger_type,
            "claim_type":       claim_type,
            "zone":             zone,
            "workers_notified": len(claims_created),
            "claims_created":   claims_created,
        }), 200

    except Exception as exc:
        logger.error(f"[AUTO_TRIGGER] Error: {exc}", exc_info=True)
        return jsonify({"status": "error", "message": f"Server Error: {str(exc)}"}), 500


# ===========================================================================
# ROUTE 2 — POST /api/claim/manual
# ===========================================================================

@claims_bp.route("/manual", methods=["POST"])
def submit_manual_claim():
    """
    Called when worker taps 'Submit' in manual_claim_screen.dart.

    Stores claim with status='under_review' and returns FIG-XXXX claim_id
    for the frontend to begin polling /api/claim/status/<claim_id>.
    """
    try:
        data = request.get_json() or {}

        worker_id      = data.get("worker_id", "")
        claim_type     = data.get("claim_type", "")
        start_time     = data.get("start_time", "")
        end_time       = data.get("end_time", "")
        description    = data.get("description", "")
        proof_urls     = data.get("proof_urls", [])

        try:
            estimated_loss = int(data.get("estimated_loss", 0))
        except ValueError:
            return jsonify({"status": "error", "message": "estimated_loss must be a number"}), 400

        # ── 1. Validate required fields ──────────────────────────────────
        if not all([worker_id, claim_type, start_time, end_time]):
            return jsonify({"status": "error", "message": "worker_id, claim_type, start_time, and end_time are required"}), 400

        # ── 3. Validate estimated_loss ───────────────────────────────────
        if not (0 < estimated_loss < 5000):
            return jsonify({"status": "error", "message": "estimated_loss must be > 0 and < 5000"}), 400

        # ── 5. Validate claim_type ───────────────────────────────────────
        valid_claim_types = ["Heavy Rain", "Flood", "Extreme Heat", "Strike", "Traffic", "Other"]
        if claim_type not in valid_claim_types:
            return jsonify({"status": "error", "message": f"claim_type must be one of: {valid_claim_types}"}), 400

        # ── 2 & 7. Validate times and calculate window ───────────────────
        try:
            # Handle ISO formatting with Z from typical frontends
            st_clean = start_time.replace("Z", "+00:00")
            et_clean = end_time.replace("Z", "+00:00")
            start_dt = datetime.fromisoformat(st_clean)
            end_dt = datetime.fromisoformat(et_clean)
        except ValueError:
            return jsonify({"status": "error", "message": "start_time and end_time must be valid ISO 8601 strings"}), 400

        if start_dt >= end_dt:
            return jsonify({"status": "error", "message": "start_time must be before end_time"}), 400

        time_window_hours = round((end_dt - start_dt).total_seconds() / 3600.0, 2)

        # ── 4. Validate worker ───────────────────────────────────────────
        worker = _find_worker(worker_id)
        if not worker or worker.get("policy_status") != "active":
            return jsonify({"status": "error", "message": "Worker not found or policy not active"}), 404

        tier = worker.get("tier", "Smart")

        # ── 6. Generate unique claim_id ──────────────────────────────────
        claim_id = ""
        for _ in range(10):
            cid = _generate_claim_id()
            if not _find_claim(cid):
                claim_id = cid
                break
        if not claim_id:
            return jsonify({"status": "error", "message": "Failed to generate unique claim_id"}), 500

        # ── 8. Create claim document ─────────────────────────────────────
        claim_doc = {
            "claim_id":        claim_id,
            "worker_id":       worker_id,
            "claim_type":      "manual",
            "claim_source":    "manual",
            "disruption_type": claim_type,
            "zone":            worker.get("zone", ""),
            "start_time":      start_time,
            "end_time":        end_time,
            "time_window_hours": time_window_hours,
            "estimated_loss":  estimated_loss,
            "actual_earnings": None,
            "income_loss":     None,
            "eligible_payout": None,
            "tier":            tier,
            "proof_urls":      proof_urls,
            "description":     description,
            "status":          "under_review",
            "payout_status":   "pending",
            "fraud_risk":      None,
            "created_at":      datetime.utcnow().isoformat() + "Z",
            "resolved_at":     None
        }

        db_handler.save_claim(claim_doc)
        logger.info(f"[MANUAL] Claim {claim_id} submitted by worker {worker_id}.")

        # ── 9. Return 201 ────────────────────────────────────────────────
        return jsonify({
            "status":       "success",
            "claim_id":     claim_id,
            "claim_status": ClaimStatus.UNDER_REVIEW.value,
            "message":      "Claim submitted successfully",
        }), 201

    except Exception as e:
        logger.error(f"[MANUAL_CLAIM] Error: {e}")
        return jsonify({"status": "error", "message": f"Server Error: {str(e)}"}), 500


# ===========================================================================
# ROUTE 3 — GET /api/claim/status/<claim_id>
# ===========================================================================

@claims_bp.route("/status/<claim_id>", methods=["GET"])
def get_claim_status(claim_id: str):
    """
    Polled by claim_processing_screen.dart every 5 seconds.
    Returns full claim status payload including exactly 10-step breakdown.
    """
    try:
        claim = _find_claim(claim_id)
        if not claim:
            return jsonify({"status": "error", "message": "Claim not found"}), 404

        worker = _find_worker(claim.get("worker_id")) or {}
        upi_id = worker.get("upi_id", "your UPI")

        c_status = claim.get("status", "verifying")
        processing_step = claim.get("processing_step", 1)
        payout_amount = claim.get("payout_amount", claim.get("eligible_payout", 0))
        risk_level = claim.get("fraud_risk", "LOW")

        msg_map = {
            "verifying": "Checking your activity records…",
            "approved": "Payout approved! Sending to your UPI…",
            "paid": f"₹{payout_amount} sent to {upi_id} ✓",
            "manual_review": "Quick security check needed — usually done in 2 hours",
            "payment_failed": "Payment bounced — please check your UPI ID",
            "rejected": "Sorry, we couldn't verify disruption in your area",
            "under_review": "Checking your activity records…"
        }

        ui_message = msg_map.get(c_status, "Processing claim...")

        # Get breakdown or dummy breakdown if not generated yet.
        breakdown_data = claim.get("payout_breakdown", {})
        breakdown = {
            "expected": breakdown_data.get("expected_earnings", 0),
            "actual": breakdown_data.get("actual_earnings", 0),
            "loss": breakdown_data.get("calc_loss", 0),
            "tier_cap": breakdown_data.get("tier_cap", 0),
            "surge_bonus": breakdown_data.get("applied_surge_multiplier", 1.0)
        }

        return jsonify({
            "status": c_status,
            "processing_step": processing_step,
            "ui_message": ui_message,
            "payout_amount": payout_amount,
            "breakdown": breakdown,
            "risk_level": risk_level,
            "claim_id": claim_id
        }), 200

    except Exception as e:
        logger.error(f"[CLAIM_STATUS] Error: {e}")
        return jsonify({"status": "error", "message": f"Server Error: {str(e)}"}), 500


# ===========================================================================
# ROUTE 4 — GET /api/claim/list/<worker_id>
# ===========================================================================

@claims_bp.route("/list/<worker_id>", methods=["GET"])
def list_worker_claims(worker_id: str):
    """
    Powers the payout history list on insurance_screen.dart.

    Returns a summary list for every claim belonging to the worker,
    ordered newest-first.
    """
    try:
        worker_claims = db_handler.get_claims_by_worker(worker_id)

        summary = [
            {
                "claim_id":       c["claim_id"],
                "type":           c["claim_type"],
                "date":           c.get("created_at", "")[:10],   # YYYY-MM-DD
                "status":         c["status"],
                "estimated_loss": c["estimated_loss"],
                "compensation":   c["eligible_payout"],
                "payout_status":  c["payout_status"],
            }
            for c in worker_claims
        ]

        return jsonify({
            "worker_id":    worker_id,
            "total_claims": len(summary),
            "claims":       summary,
        }), 200

    except Exception as e:
        logger.error(f"[CLAIM_LIST] Error: {e}")
        return jsonify({"status": "error", "message": f"Server Error: {str(e)}"}), 500


# ===========================================================================
# ROUTE 5 — POST /api/claim/payout  (INTERNAL — called after approval)
# ===========================================================================

@claims_bp.route("/payout", methods=["POST"])
def trigger_payout():
    """
    Internal route — never called directly by the Flutter app.
    Invoked after a claim is marked 'approved' by the verification engine.

    Hits Razorpay Payout API to initiate a UPI transfer.
    Falls back to demo mode if Razorpay keys are not configured.

    Body: { claim_id, worker_id, amount_inr, upi_id }
    """
    try:
        data      = request.get_json() or {}
        claim_id  = data.get("claim_id", "")
        worker_id = data.get("worker_id", "")
        amount_inr = float(data.get("amount_inr", 0))
        upi_id    = data.get("upi_id", "")

        # ── Validation ───────────────────────────────────────────────────
        if not all([claim_id, worker_id, upi_id]):
            return jsonify({"status": "error", "message": "claim_id, worker_id, and upi_id are required"}), 400
        if amount_inr <= 0:
            return jsonify({"status": "error", "message": "amount_inr must be > 0"}), 400

        # ── Verify claim exists and is approved ───────────────────────────
        claim = _find_claim(claim_id)
        if not claim:
            return jsonify({"status": "error", "message": f"Claim {claim_id} not found"}), 404
        if claim.get("status") != "approved":
            return jsonify({"status": "error", "message": "Payout can only be triggered for approved claims"}), 400

        amount_paise = int(amount_inr * 100)  # Razorpay uses paise (1 INR = 100 paise)

        key_id     = current_app.config.get("RAZORPAY_KEY_ID")
        key_secret = current_app.config.get("RAZORPAY_KEY_SECRET")
        account_number = current_app.config.get("RAZORPAY_ACCOUNT_NUMBER", "FIGGY_CURRENT_ACC")

        # ── Demo Mode fallback ────────────────────────────────────────────
        if not key_id or not key_secret:
            demo_payout_id = f"pout_demo_{claim_id}_{int(datetime.utcnow().timestamp())}"
            _update_claim_payout(claim, demo_payout_id, "initiated")
            logger.info(f"[PAYOUT] DEMO mode — Claim {claim_id} payout simulated: {demo_payout_id}")
            return jsonify({
                "status":             "success",
                "razorpay_payout_id": demo_payout_id,
                "mode":               "demo",
                "message":            f"Demo payout of ₹{amount_inr} initiated to {upi_id}",
            }), 200

        # ── Real Razorpay Payout API ──────────────────────────────────────
        client = razorpay.Client(auth=(key_id, key_secret))

        # NOTE: Requires Razorpay X (Payout API) — separate from payment gateway.
        # The worker must have a fund_account_id stored on their profile.
        worker = _find_worker(worker_id)
        fund_account_id = worker.get("razorpay_fund_account_id", "") if worker else ""

        if not fund_account_id:
            return jsonify({
                "status":  "error",
                "message": "Worker does not have a Razorpay fund account registered. Payout requires KYC."
            }), 400

        payout_data = {
            "account_number":   account_number,
            "fund_account_id":  fund_account_id,
            "amount":           amount_paise,
            "currency":         "INR",
            "mode":             "UPI",
            "purpose":          "payout",
            "queue_if_low_balance": True,
            "narration":        f"GigShield claim {claim_id}",
            "reference_id":     claim_id,
        }

        payout_response = client.payout.create(data=payout_data)
        payout_id = payout_response.get("id", "")

        _update_claim_payout(claim, payout_id, "initiated")
        logger.info(f"[PAYOUT] Claim {claim_id} — Razorpay payout {payout_id} initiated to {upi_id}")

        return jsonify({
            "status":             "success",
            "razorpay_payout_id": payout_id,
            "payout_status":      "initiated",
            "amount_inr":         amount_inr,
            "upi_id":             upi_id,
        }), 200

    except Exception as e:
        logger.error(f"[PAYOUT] Error: {e}")
        return jsonify({"status": "error", "message": f"Server Error: {str(e)}"}), 500


# ---------------------------------------------------------------------------
# Internal helper — update claim's payout fields in-place
# ---------------------------------------------------------------------------

def _update_claim_payout(claim: dict, payout_id: str, payout_status: str):
    claim_id = claim.get("claim_id", "")
    db_handler.update_claim_status(claim_id, claim["status"], {
        "razorpay_payout_id": payout_id,
        "payout_status":      payout_status,
    })


# ===========================================================================
# ROUTE 6 — POST /api/claim/retry_payment/<claim_id>
# ===========================================================================

@claims_bp.route("/retry_payment/<claim_id>", methods=["POST"])
def retry_claim_payment(claim_id: str):
    """
    Called when worker wants to retry a failed payment.
    Requires that the worker has updated their UPI ID.
    Re-runs only steps 9-10 without re-evaluating fraud or calculations.
    """
    try:
        claim = _find_claim(claim_id)
        if not claim:
            return jsonify({"status": "error", "message": "Claim not found"}), 404

        # ── 1. Idempotency Check ──────────────────────────────────────────
        if claim.get("status") == "paid":
            return jsonify({"status": "error", "message": "Claim is already paid"}), 409

        # ── 2. Eligibility Check ──────────────────────────────────────────
        if claim.get("status") != "payment_failed" or not claim.get("retry_eligible"):
            return jsonify({
                "status": "error", 
                "message": "Claim is not eligible for payment retry"
            }), 400

        worker_id = claim.get("worker_id")
        worker = _find_worker(worker_id)
        if not worker:
            return jsonify({"status": "error", "message": "Worker not found"}), 404

        # ── 3. UPI Update Validation ──────────────────────────────────────
        last_upi = claim.get("last_upi_attempted")
        current_upi = worker.get("upi_id")
        
        if last_upi and current_upi and last_upi == current_upi:
            return jsonify({
                "status": "error", 
                "message": "Please update your UPI ID in your profile before retrying"
            }), 400

        # ── 4. Set retry_eligible = False to prevent loops ──────────────────
        db_handler.update_claim_status(
            claim_id, 
            "payment_failed", 
            {"retry_eligible": False}
        )

        # ── 5. Dispatch retry_payout task ─────────────────────────────────
        from app.utils.scheduler import scheduler
        from app.utils.claim_processor import retry_payout
        
        job_id = f"retry_pow_{claim_id}"
        scheduler.add_job(
            id=job_id,
            func=retry_payout,
            args=[claim_id],
            misfire_grace_time=3600
        )
        logger.info(f"[RETRY_PAYMENT] Claim {claim_id} dispatched to background job {job_id}.")

        return jsonify({
            "status": "retrying",
            "claim_id": claim_id,
        }), 200

    except Exception as e:
        logger.error(f"[RETRY_PAYMENT] Error: {e}")
        return jsonify({"status": "error", "message": f"Server Error: {str(e)}"}), 500


# ===========================================================================
# ROUTE 7 — POST /api/claim/appeal/<claim_id>
# ===========================================================================

@claims_bp.route("/appeal/<claim_id>", methods=["POST"])
def appeal_claim(claim_id: str):
    """
    Allows a worker to appeal a rejected claim.
    """
    try:
        data = request.get_json() or {}
        worker_statement = data.get("worker_statement", "")
        proof_url = data.get("proof_url", "")

        claim = _find_claim(claim_id)
        if not claim:
            return jsonify({"status": "error", "message": "Claim not found"}), 404

        if claim.get("status") != "rejected":
            return jsonify({"status": "error", "message": "Only rejected claims can be appealed"}), 400
            
        rejection_reason = claim.get("rejection_reason")
        if rejection_reason not in ["NO_DISRUPTION_DETECTED", "OUTSIDE_COVERAGE_ZONE"]:
            return jsonify({"status": "error", "message": "This claim is not eligible for appeal"}), 400
            
        if claim.get("appeal_filed"):
            return jsonify({"status": "error", "message": "An appeal has already been filed for this claim"}), 409

        # Mark original as appealed
        db_handler.update_claim_status(claim_id, "rejected", {"appeal_filed": True})

        # Create new linked claim record
        appeal_claim_id = ""
        for _ in range(10):
            cid = _generate_claim_id()
            if not _find_claim(cid):
                appeal_claim_id = cid
                break
                
        if not appeal_claim_id:
            return jsonify({"status": "error", "message": "Failed to generate appeal ID"}), 500

        appeal_doc = {
            **claim,
            "claim_id": appeal_claim_id,
            "original_claim_id": claim_id,
            "claim_source": "manual",
            "claim_type": "appeal",
            "status": "manual_review",
            "worker_statement": worker_statement,
            "proof_urls": [proof_url] if proof_url else claim.get("proof_urls", []),
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "resolved_at": None,
            "rejection_reason": None,
            "appeal_filed": False
        }
        
        db_handler.save_claim(appeal_doc)
        logger.info(f"[APPEAL] Appeal filed for {claim_id}. New appeal claim: {appeal_claim_id}")

        return jsonify({
            "status": "manual_review",
            "appeal_claim_id": appeal_claim_id
        }), 201

    except Exception as e:
        logger.error(f"[APPEAL] Error: {e}")
        return jsonify({"status": "error", "message": f"Server Error: {str(e)}"}), 500


# ===========================================================================
# INTERNAL UTILITY — approve_claim()
# Called by PoW verification engine after scoring is complete.
# ===========================================================================

def approve_claim(claim_id: str, weather: dict | None = None) -> bool:
    """
    Score fraud, calculate payout via calculations.py, and apply the
    decision via fraud.apply_fraud_decision().

    Parameters
    ----------
    claim_id : str  — e.g. "FIG-8821"
    weather  : dict | None — zone weather; enables Elite surge if extreme

    Returns True if the claim was approved (low fraud risk), False otherwise.
    """
    claim = _find_claim(claim_id)
    if not claim:
        logger.warning(f"[APPROVE] Claim {claim_id} not found.")
        return False

    worker = _find_worker(claim["worker_id"])
    if not worker:
        logger.warning(f"[APPROVE] Worker {claim['worker_id']} not found.")
        return False

    # ── Fraud scoring (utils/fraud.py) ───────────────────────────────────
    fraud_result = score_fraud_risk(claim, worker)
    risk         = fraud_result["risk_level"]

    # ── Payout calculation (utils/calculations.py) ───────────────────────
    income_loss = claim.get("income_loss") or claim.get("estimated_loss", 0)
    tier        = worker.get("tier", "Smart")

    payout_summary  = build_payout_summary(
        worker,
        {**claim, "income_loss": income_loss, "actual_earnings": claim.get("actual_earnings", 0)},
        weather or {},
    )
    eligible_payout = payout_summary["eligible_payout"]

    # Carry payout into fraud_result for apply_fraud_decision
    claim["income_loss"]     = income_loss
    claim["eligible_payout"] = eligible_payout
    claim["tier"]            = tier

    # ── Apply decision → DB status transition ────────────────────────────
    applied = apply_fraud_decision(claim_id, fraud_result)

    if risk == "low" and applied:
        logger.info(
            f"[APPROVE] ✅ Claim {claim_id} → approved | "
            f"payout=₹{eligible_payout} | surge={payout_summary['surge_bonus_applied']} "
            f"| upi={claim.get('payout_upi', '')}"
        )
        return True

    logger.info(f"[APPROVE] Claim {claim_id} → {risk} ({fraud_result['action']}).")
    return False


# ===========================================================================
# ROUTE 8 — GET /api/claim/calculate_preview/<worker_id>
# ===========================================================================

@claims_bp.route("/calculate_preview/<worker_id>", methods=["GET"])
def calculate_preview(worker_id: str):
    """
    GET /api/claim/calculate_preview/<worker_id>
    ?disruption_hours=2.5&trigger_type=RAIN&detected_value=62

    Returns a live payout estimate BEFORE a claim is filed.
    Flutter uses this to display:
        "If disruption continues, you may receive up to ₹X"

    Query Parameters
    ----------------
    disruption_hours : float  — how many hours the disruption has been active
                                (e.g. elapsed time since first trigger)
                                Default: 1.0
    trigger_type     : str    — "RAIN" | "AQI" | "CURFEW"   Default: "RAIN"
    detected_value   : float  — live sensor reading (mm/hr or AQI index)
                                Default: 0.0

    Response 200
    ------------
    {
        "worker_id"          : str,
        "worker_name"        : str,
        "tier"               : str,
        "expected_earnings"  : float,   // for the disruption window
        "actual_earnings"    : float,   // 0 — worst-case assumption
        "income_loss"        : float,
        "tier_cap"           : int,
        "surge_bonus_applied": bool,
        "surge_multiplier"   : float,
        "eligible_payout"    : float,
        "breakdown_label"    : str,     // human-readable summary
        "preview_message"    : str,     // Flutter display string
        "is_preview"         : true,
        "disruption_hours"   : float,
        "trigger_type"       : str,
        "detected_value"     : float
    }

    Response 404 — worker not found or policy not active
    Response 400 — invalid query param values
    Response 500 — calculation error
    """
    try:
        from app.utils.calculations import estimate_payout_preview

        # ── 1. Parse & validate query params ────────────────────────────────
        try:
            disruption_hours = float(request.args.get("disruption_hours", 1.0))
        except (ValueError, TypeError):
            return jsonify({"status": "error",
                            "message": "disruption_hours must be a positive number"}), 400

        if disruption_hours <= 0 or disruption_hours > 24:
            return jsonify({"status": "error",
                            "message": "disruption_hours must be between 0 and 24"}), 400

        trigger_type = request.args.get("trigger_type", "RAIN").strip().upper()
        if trigger_type not in {"RAIN", "AQI", "CURFEW"}:
            return jsonify({"status": "error",
                            "message": "trigger_type must be RAIN, AQI, or CURFEW"}), 400

        try:
            detected_value = float(request.args.get("detected_value", 0.0))
        except (ValueError, TypeError):
            return jsonify({"status": "error",
                            "message": "detected_value must be a number"}), 400

        # ── 2. Look up worker ────────────────────────────────────────────────
        worker = _find_worker(worker_id)
        if not worker:
            return jsonify({"status": "error",
                            "message": f"Worker '{worker_id}' not found"}), 404

        if worker.get("policy_status") != "active":
            return jsonify({
                "status":  "error",
                "message": "Worker does not have an active policy. "
                           "Activate GigShield to see your payout preview.",
                "policy_status": worker.get("policy_status", "inactive"),
            }), 404

        # ── 3. Run estimate ──────────────────────────────────────────────────
        preview = estimate_payout_preview(
            worker          = worker,
            disruption_hours= disruption_hours,
            trigger_type    = trigger_type,
            detected_value  = detected_value,
        )

        # ── 4. Build Flutter-friendly display message ────────────────────────
        payout     = preview["eligible_payout"]
        tier       = worker.get("tier", "Lite")
        surge_txt  = " (incl. surge bonus 🔥)" if preview.get("surge_bonus_applied") else ""

        preview_message = (
            f"If disruption continues for {disruption_hours:.1f}h, "
            f"you may receive up to ₹{payout:.0f}{surge_txt} under your {tier} plan."
        )

        # ── 5. Return ────────────────────────────────────────────────────────
        return jsonify({
            "worker_id":           worker_id,
            "worker_name":         worker.get("name", ""),
            "tier":                tier,
            **preview,
            "preview_message":     preview_message,
        }), 200

    except ValueError as ve:
        logger.warning(f"[PREVIEW] Validation error for worker {worker_id}: {ve}")
        return jsonify({"status": "error", "message": str(ve)}), 400

    except Exception as exc:
        logger.error(f"[PREVIEW] Error for worker {worker_id}: {exc}", exc_info=True)
        return jsonify({"status": "error",
                        "message": f"Server Error: {str(exc)}"}), 500


# ===========================================================================
# ROUTE 9 — GET /api/claim/pow_status/<claim_id>
# ===========================================================================

@claims_bp.route("/pow_status/<claim_id>", methods=["GET"])
def get_pow_status(claim_id: str):
    """
    GET /api/claim/pow_status/<claim_id>
    
    Evaluates an in-progress or closed claim using the Proof-of-Work engine
    and returns a worker-friendly breakdown of the fraud checks.
    """
    try:
        claim = _find_claim(claim_id)
        if not claim:
            return jsonify({"status": "error", "message": f"Claim '{claim_id}' not found"}), 404
            
        worker_id = claim.get("worker_id")
        worker = _find_worker(worker_id)
        if not worker:
            return jsonify({"status": "error", "message": f"Worker '{worker_id}' not found"}), 404
            
        telemetry = claim.get("telemetry", {})
        
        from app.utils.fraud import score_claim
        pow_result = score_claim(claim, worker, telemetry)
        
        return jsonify({"status": "success", **pow_result}), 200
        
    except Exception as exc:
        logger.error(f"[POW] Error for claim {claim_id}: {exc}", exc_info=True)
        return jsonify({"status": "error", "message": f"Server Error: {str(exc)}"}), 500
