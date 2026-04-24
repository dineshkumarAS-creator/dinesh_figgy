import logging
import time
import os
from datetime import datetime
import requests as http_req
from app.models import db_handler
from app.utils.calculations import build_payout_summary
from app.utils.payout import RazorpayPayoutService
from app.utils.fraud import score_claim

try:
    import firebase_admin
    from firebase_admin import messaging
except ImportError:
    firebase_admin = None
    messaging = None

logger = logging.getLogger("CLAIM_PROCESSOR")
FCM_SERVER_KEY = os.getenv("FCM_SERVER_KEY", "")

def send_claim_notification(worker_id: str, event: str, claim: dict):
    worker = db_handler.get_worker(worker_id)
    fcm_token = worker.get("fcm_token") if worker else None

    messages = {
        "approved": f"Claim approved! ₹{claim.get('eligible_payout', 0)} will be credited to your UPI within 2 hours.",
        "verifying": "Your claim is being verified. We'll notify you shortly.",
        "manual_review": "Your claim needs manual review. Our team will contact you in 24-48 hrs.",
        "paid": f"₹{claim.get('eligible_payout', 0)} has been credited to your UPI account!",
    }
    msg = messages.get(event, "")

    if not fcm_token or not FCM_SERVER_KEY:
        logger.info(f"[NOTIFY-STUB] {worker_id}: {msg}")
        return

    try:
        payload = {
            "to": fcm_token,
            "notification": {"title": "GigShield Update", "body": msg},
            "data": {"claim_id": claim.get("claim_id", ""), "event": event},
        }
        response = http_req.post(
            "https://fcm.googleapis.com/fcm/send",
            headers={
                "Authorization": f"key={FCM_SERVER_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=5,
        )
        if response.status_code >= 300:
            logger.warning(
                f"[NOTIFY-FAIL] worker={worker_id} event={event} "
                f"status={response.status_code} body={response.text}"
            )
        else:
            logger.info(f"[NOTIFY-SENT] worker={worker_id} event={event}")
    except Exception as e:
        logger.error(f"[NOTIFY-ERROR] worker={worker_id} event={event}: {str(e)}")

def _update_step(claim_id: str, step: int):
    claim = db_handler.get_claim(claim_id)
    if claim:
        db_handler.update_claim_status(claim_id, claim.get("status", "verifying"), {"processing_step": step})
        logger.info(f"[{claim_id}] Reached Step {step}")

def verify_and_payout(claim_id: str):
    """
    10-step Verify-and-Payout Orchestrator.
    Runs in background thread via Flask executor or APScheduler.
    """
    logger.info(f"[{claim_id}] Starting 10-step Verify-and-Payout Orchestrator")
    
    # Step 1 — LOAD_STATE
    claim = db_handler.get_claim(claim_id)
    if not claim:
        logger.error(f"[{claim_id}] Step 1 Failed: Claim not found.")
        return
    worker_id = claim.get("worker_id")
    worker = db_handler.get_worker(worker_id)
    if not worker:
        logger.error(f"[{claim_id}] Step 1 Failed: Worker not found.")
        return
    _update_step(claim_id, 1)

    # Step 2 — CONTEXTUALIZE
    telemetry = {
        "gps_km_during_disruption": worker.get("last_session_gps_km", 2.1),
        "online_mins": worker.get("last_session_online_mins", 180),
        "delivery_count": worker.get("last_session_deliveries", 2),
        "actual_earnings": worker.get("last_session_earnings", 119)
    }
    _update_step(claim_id, 2)

    # Step 3 — NOTIFY_EVENT
    send_claim_notification(worker_id, "verifying", claim)
    _update_step(claim_id, 3)

    # Step 4 — FRAUD_CHECK
    fraud_result = score_claim(claim, worker, telemetry)
    risk_level = fraud_result.get("risk_level", "HIGH")
    
    claim = db_handler.get_claim(claim_id)
    db_handler.update_claim_status(claim_id, claim.get("status", "verifying"), {
        "fraud_risk": risk_level,
        "fraud_checks": fraud_result.get("checks", [])
    })
    _update_step(claim_id, 4)

    # Step 5 — ROUTE_ACTION
    if risk_level in ["HIGH", "MEDIUM"]:
        db_handler.update_claim_status(claim_id, "manual_review", {})
        send_claim_notification(worker_id, "manual_review", claim)
        _update_step(claim_id, 5)
        logger.warning(f"[{claim_id}] Pipeline stopped at Step 5 due to {risk_level} risk.")
        return
    _update_step(claim_id, 5)

    # Step 6 — QUANTIFY_LOSS
    weather = {"precipitation": claim.get("rain_mm_hr", 45.0)}
    summary = build_payout_summary(worker, claim, weather)
    claim = db_handler.get_claim(claim_id)
    db_handler.update_claim_status(claim_id, claim.get("status", "verifying"), {
        "payout_breakdown": summary
    })
    _update_step(claim_id, 6)

    # Step 7 — CALCULATE_PAYOUT
    eligible_payout = summary.get("eligible_payout", 0)
    claim = db_handler.get_claim(claim_id)
    db_handler.update_claim_status(claim_id, claim.get("status", "verifying"), {
        "payout_amount": eligible_payout,
        "eligible_payout": eligible_payout
    })
    _update_step(claim_id, 7)

    # Step 8 — APPROVE_STATE
    now_ts = datetime.utcnow().isoformat()
    db_handler.update_claim_status(claim_id, "approved", {
        "approved_at": now_ts
    })
    claim = db_handler.get_claim(claim_id) or claim
    send_claim_notification(worker_id, "approved", claim)
    _update_step(claim_id, 8)

    # Step 9 — DISPATCH_PAYMENT
    if worker.get("upi_id") == "fail@ybl":
        payout_result = {"status": "error", "error_message": "Simulated bank failure for fail@ybl"}
    else:
        try:
            payout_result = RazorpayPayoutService().initiate_payout(worker, claim_id, eligible_payout)
        except Exception as e:
            payout_result = {"status": "error", "error_message": str(e)}
    _update_step(claim_id, 9)

    # Step 10 — FINALIZE
    if payout_result.get("status") == "error":
        db_handler.update_claim_status(claim_id, "payment_failed", {
            "payout_error": payout_result.get("error_message"),
            "retry_eligible": True,
            "last_upi_attempted": worker.get("upi_id", ""),
        })
        send_claim_notification(worker_id, "Payment Failed", "Payment bounced — please check your UPI ID")
    else:
        db_handler.update_claim_status(claim_id, "paid", {
            "payout_reference": payout_result.get("payout_id", "PO_PENDING")
        })
        claim = db_handler.get_claim(claim_id) or claim
        send_claim_notification(worker_id, "paid", claim)
    _update_step(claim_id, 10)
    logger.info(f"[{claim_id}] Pipeline complete.")


def retry_payout(claim_id: str):
    """
    Retry only payment dispatch/finalization for payment_failed claims.
    Called by /api/claim/retry_payment background scheduler job.
    """
    claim = db_handler.get_claim(claim_id)
    if not claim:
        logger.error(f"[{claim_id}] Retry failed: claim not found.")
        return

    worker_id = claim.get("worker_id")
    worker = db_handler.get_worker(worker_id)
    if not worker:
        logger.error(f"[{claim_id}] Retry failed: worker not found.")
        return

    if claim.get("status") != "payment_failed":
        logger.warning(f"[{claim_id}] Retry skipped: claim status is {claim.get('status')}.")
        return

    amount = int(claim.get("eligible_payout") or claim.get("payout_amount") or 0)
    if amount <= 0:
        logger.error(f"[{claim_id}] Retry failed: invalid payout amount {amount}.")
        return

    if worker.get("upi_id") == "fail@ybl":
        payout_result = {"status": "error", "error_message": "Simulated bank failure for fail@ybl"}
    else:
        try:
            payout_result = RazorpayPayoutService().initiate_payout(worker, claim_id, amount)
        except Exception as e:
            payout_result = {"status": "error", "error_message": str(e)}

    if payout_result.get("status") == "error":
        db_handler.update_claim_status(claim_id, "payment_failed", {
            "payout_error": payout_result.get("error_message"),
            "retry_eligible": True,
            "last_upi_attempted": worker.get("upi_id", ""),
        })
        logger.warning(f"[{claim_id}] Retry payout failed.")
        return

    db_handler.update_claim_status(claim_id, "paid", {
        "payout_reference": payout_result.get("payout_id", "PO_PENDING"),
        "retry_eligible": False,
    })
    claim = db_handler.get_claim(claim_id) or claim
    send_claim_notification(worker_id, "paid", claim)
    logger.info(f"[{claim_id}] Retry payout successful.")
