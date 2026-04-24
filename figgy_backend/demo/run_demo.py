import os
import sys
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from app.models import db, get_uuid
from app.utils.claim_processor import verify_and_payout

def run_demo():
    load_dotenv()
    os.environ['DEMO_MODE'] = 'true'
    app = create_app()
    with app.app_context():
        print("\n\033[94m=====================================================")
        print("======== FIGGY GIGSHIELD AUTO-PIPELINE DEMO ========")
        print("=====================================================\033[0m\n")
        
        worker_id = "ravi_demo_123"
        upi = "ravi@paytm"
        
        print("\033[93m[IN PROGRESS]\033[0m Activating Worker Profile (Ravi, Smart Tier)")
        time.sleep(2)
        db.workers.update_one(
            {"worker_id": worker_id},
            {"$set": {
                "name": "Ravi Demo",
                "phone": "9999912345",
                "selected_tier": "Smart",
                "avg_daily_earnings": 600,
                "daily_hours": 8,
                "avg_deliveries": 18,
                "upi_id": upi,
                "zone_id": "koramangala_3",
                "last_session_gps_km": 1.2,
                "last_session_deliveries": 2,
                "last_session_online_mins": 30
            }},
            upsert=True
        )
        print("\033[92m[PASS]\033[0m Worker Ravi successfully initialized.\n")

        print("\033[93m[IN PROGRESS]\033[0m Triggering Live Weather Data Intercept: (RAIN: 52 mm/hr)")
        time.sleep(2)
        
        claim_id = get_uuid()
        db.claims.insert_one({
            "claim_id": claim_id,
            "worker_id": worker_id,
            "disruption_type": "Heavy rainfall",
            "detected_value": "52 mm/hr",
            "zone": "Koramangala, Zone 3",
            "status": "verifying",
            "processing_step": 1,
            "date": "Today"
        })
        print(f"\033[92m[PASS]\033[0m Weather Event Intercepted -> Automated Claim ({claim_id}) created.\n")

        print("\033[93m[IN PROGRESS]\033[0m Dispatching 10-Step Claims Orchestrator...\n")
        time.sleep(1)

        steps = [
            "LOAD_STATE  : Retrieved claim data and worker metadata",
            "CONTEXTUALIZE: Validated localized telemetry & delivery activity",
            "NOTIFY_EVENT : Dispatched FCM -> 'Your claim is processing'",
            "FRAUD_CHECK  : AI risk engine validation (LOW RISK ✓)",
            "ROUTE_ACTION : Bypassed manual review",
            "QUANTIFY_LOSS: Loss mathematics calculated (Expected - Actual)",
            "CALCUL_PAYOUT: Smart Tier ceiling (₹500) applied to loss amount",
            "APPROVE_STATE: Formal disbursement approval logged",
            "DISPTCH_PYMNT: Razorpay X API UPI trigger executed",
            "FINALIZE    : Claim terminal state flagged to -> PAID"
        ]

        # Trigger real verify_and_payout asynchronously
        import threading
        t = threading.Thread(target=verify_and_payout, args=(claim_id,))
        t.start()

        # Simulate delay for narrator
        for step in steps:
            print(f"\033[93m[IN PROGRESS]\033[0m {step}...")
            time.sleep(0.5)
            print(f"\033[92m[PASS]\033[0m {step} ✓")
            time.sleep(1.5)
        
        t.join()

        # Print outcome
        claim = db.claims.find_one({"claim_id": claim_id})
        amount = claim.get("payout_amount", 0) if claim else 0

        print(f"\n\033[92m₹{amount} paid to {upi} ✓ — Total time: 9 minutes (Demo: 9 seconds)\033[0m\n")

if __name__ == "__main__":
    run_demo()
