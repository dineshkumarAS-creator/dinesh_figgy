"""
figgy_backend/app/routes/demo.py
================================
Demo endpoints for Hackathon presentation.
"""

import logging
import threading
from flask import Blueprint, request, jsonify, current_app
from app.models import db_handler, CLAIM_SCHEMA_TEMPLATE, ClaimStatus
from app.utils.claim_processor import verify_and_payout
import string
import random
from datetime import datetime

logger = logging.getLogger("FIGGY_DEMO")

demo_bp = Blueprint("demo", __name__, url_prefix="/api/demo")

def _generate_claim_id() -> str:
    digits = "".join(random.choices(string.digits, k=4))
    return f"FIG-{digits}"

def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

@demo_bp.route("/trigger_rain", methods=["POST"])
def trigger_rain():
    """
    POST /api/demo/trigger_rain
    Simulates a parametric trigger and bypasses APScheduler to run synchronously
    for a live 60-second hackathon demo.
    """
    try:
        # 1. Validate environment
        if current_app.config.get("ENV") == "production":
            return jsonify({"status": "error", "message": "Demo mode disabled in production"}), 403

        data = request.get_json() or {}
        zone = data.get("zone", "North")
        rain_mm_hr = float(data.get("rain_mm_hr", 52.0))
        target_worker_id = data.get("worker_id") # Optional

        logger.info(f"[DEMO] Triggering simulated rain ({rain_mm_hr}mm/h) in {zone} zone.")

        # 3. Fetch workers
        all_workers = db_handler.get_all_workers()
        if target_worker_id:
            active_workers = [w for w in all_workers if w.get("worker_id") == target_worker_id]
        else:
            active_workers = [
                w for w in all_workers
                if w.get("zone", "").lower() == zone.lower() and w.get("policy_status") == "active"
            ]

        claims_created = []

        # 4. Create synchronous claims for demo
        for worker in active_workers:
            claim_id = _generate_claim_id()
            worker_id = worker.get("worker_id", "")
            tier = worker.get("tier", "Smart")

            claim_doc = {
                **CLAIM_SCHEMA_TEMPLATE,
                "claim_id":       claim_id,
                "worker_id":      worker_id,
                "claim_source":   "auto",
                "claim_type":     "Heavy Rain",
                "zone":           zone,
                "rain_mm_hr":     rain_mm_hr,
                "estimated_loss": worker.get("avg_daily_earnings", 600) // 2,
                "tier_max_payout": 500 if tier == "Smart" else 300,
                "payout_upi":     worker.get("upi_id", ""),
                "status":         "verifying", # Start immediately at verifying phase
                "created_at":     _now_iso(),
                "updated_at":     _now_iso(),
            }

            db_handler.save_claim(claim_doc)
            claims_created.append(claim_id)

            logger.info(f"[DEMO] Claim {claim_id} created for {worker_id}")

            # 5. Fire verify_and_payout in a background thread so we return
            #    immediately — the Flutter polling loop will pick up status changes.
            t = threading.Thread(
                target=verify_and_payout,
                args=(claim_id,),
                daemon=True,
            )
            t.start()

        # 6. Response
        return jsonify({
            "claims_created": claims_created,
            "demo_mode": True,
            "message": f"Demo rain triggered in {zone} zone."
        }), 200

    except Exception as e:
        logger.error(f"[DEMO_TRIGGER] Error: {e}")
        return jsonify({"status": "error", "message": f"Server Error: {str(e)}"}), 500

# DEMO SCRIPT FOR JUDGES:
# 1. Show Ravi's profile — active Smart policy
# 2. Open Radar tab — currently clear
# 3. Tap "SIMULATE RAIN (DEMO)"  
# 4. Switch to Insurance tab — claim appears as "Processing"
# 5. Wait 10 seconds — status changes to "PAID — Rs.400"
# 6. Tap VIEW CLAIM DETAILS — show full breakdown
# Total demo time: ~60 seconds
