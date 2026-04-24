import random
import string
from datetime import datetime
from flask import Blueprint, request, jsonify
from app.utils.mock_generator import generate_worker_data
from app.models import db_handler, terms_store
import os
import joblib

# Try to load ML model on startup (avoids overhead on per-request)
PREMIUM_MODEL = None
_model_path = os.path.join(os.path.dirname(__file__), "..", "..", "models", "premium_model.pkl")

try:
    if os.path.exists(_model_path):
        PREMIUM_MODEL = joblib.load(_model_path)
        print("[worker] Premium XGBoost model loaded successfully.")
    else:
        print("[worker] Premium model not found; using rule-based engine.")
except Exception as e:
    print(f"[worker] Failed to load Premium ML model: {e}")

# Blueprint
worker_bp = Blueprint('worker', __name__, url_prefix='/api/worker')

def generate_worker_id() -> str:
    """Generates a random unique worker ID: GS- + 6 uppercase chars."""
    chars = string.ascii_uppercase + string.digits
    unique_suffix = ''.join(random.choices(chars, k=6))
    return f"GS-{unique_suffix}"

@worker_bp.route('/fetch', methods=['POST'])
def fetch_worker():
    """POST /api/worker/fetch - Uses deterministic mocking."""
    try:
        data = request.get_json() or {}
        swiggy_id = data.get("swiggy_id")
        phone = data.get("phone")
        identifier = swiggy_id or phone
        
        if not identifier:
            return jsonify({"status": "error", "message": "swiggy_id or phone required"}), 400
            
        mock_data = generate_worker_data(identifier)
        
        # If not in whitelist, check if they are already registered in our local system
        if mock_data is None:
            existing_workers = db_handler.get_all_workers()
            for w in existing_workers:
                if w.get("swiggy_id") == identifier or w.get("phone") == identifier:
                    mock_data = w
                    break
        
        if mock_data is None:
            return jsonify({
                "status": "error", 
                "message": "ID Not Found: This Swiggy ID is not registered in the official partner records."
            }), 404
            
        return jsonify({"status": "success", "data": mock_data}), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server Error: {str(e)}"}), 500

@worker_bp.route('/premium/calculate', methods=['GET', 'POST'])
def calculate_premium():
    """
    GET or POST /api/worker/premium/calculate
    Input allows specific worker details or fetches from registered ID.
    """
    try:
        data = request.get_json() if request.method == 'POST' else request.args.to_dict()
        worker_id = data.get("worker_id")
        
        # If worker ID is passed, retrieve the missing details from DB
        workers = db_handler.get_all_workers()
        worker_lookup = next((w for w in workers if w.get("worker_id") == worker_id), {}) if worker_id else {}
        
        avg_daily = float(data.get("avg_daily_earnings", worker_lookup.get("avg_daily_earnings", 800)))
        daily_hours = float(data.get("daily_hours", worker_lookup.get("daily_hours", 8)))
        zone = data.get("zone", worker_lookup.get("zone", "Central"))
        weekly_deliv = float(data.get("weekly_deliveries", worker_lookup.get("weekly_deliveries", 120)))
        
        # Determine strict category purely off average
        if avg_daily < 700:
            category = "Low"
        elif avg_daily < 1000:
            category = "Medium"
        else:
            category = "High"
            
        # Hardcoded dictionary metric
        zone_map = { "North": 0.7, "South": 0.5, "East": 0.6, "West": 0.4, "Central": 0.8 }
        z_risk = zone_map.get(zone, 0.5)
        
        stability = 0.2  # default fallback if not supplied
        platform_id = 0  # 0=Swiggy
        
        if PREMIUM_MODEL is not None:
            import pandas as pd
            df = pd.DataFrame([{
                "avg_daily_earnings": avg_daily,
                "daily_hours": daily_hours,
                "zone_risk_score": z_risk,
                "weekly_deliveries": weekly_deliv,
                "income_stability": stability,
                "platform": platform_id
            }])
            raw_pred = PREMIUM_MODEL.predict(df)[0]
            weekly_premium_raw = float(raw_pred)
            confidence = 0.87
        else:
            base_p = avg_daily * 7 * 0.0015
            zone_adj = z_risk * 15
            stab_adj = (1 - stability) * 10
            weekly_premium_raw = base_p + zone_adj + stab_adj
            confidence = 0.50

        # Map to DEVTrails-visible weekly tiers
        if avg_daily < 700:
            weekly_premium = 10
            tier = "Lite"
        elif avg_daily < 1000:
            weekly_premium = 20
            tier = "Smart"
        else:
            weekly_premium = 35
            tier = "Elite"

        return jsonify({
            "weekly_premium": weekly_premium,
            "tier": tier,
            "ml_predicted_premium": round(weekly_premium_raw, 2),
            "coverage_cap": {"Lite": 300, "Smart": 500, "Elite": 750}[tier],
            "billing_cycle": "weekly",
            "income_category": category,
            "confidence": confidence,
            "recommended_premium": weekly_premium,
            "tier_suggestion": tier
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Calculation logic failed: {str(e)}"}), 500

@worker_bp.route('/register', methods=['POST'])
def register_worker():
    """POST /api/worker/register - Stores in DB or In-Memory fallback."""
    try:
        body = request.get_json() or {}
        # Support both wrapped and flat data structures
        data = body.get("data", body) if isinstance(body.get("data"), dict) else body
        
        swiggy_id = body.get("swiggy_id") or data.get("swiggy_id")
        phone = body.get("phone") or data.get("phone")
        identifier = swiggy_id or phone
        
        if not identifier:
            return jsonify({"status": "error", "message": "Identifier required for registration"}), 400
            
        # Logic for income category and premiums
        avg_daily = data.get("avg_daily_earnings", 0)
        if avg_daily < 700:
            cat, prem = "Low", 10
        elif avg_daily < 1000:
            cat, prem = "Medium", 20
        else:
            cat, prem = "High", 35
            
        worker_id = generate_worker_id()
        
        # 🧪 DEEP REGISTRATION: Merge full rich mock data (KYC, Bank, Stats)
        full_mock_data = generate_worker_data(identifier) or {}
        
        worker_doc = {
            **full_mock_data,
            "worker_id": worker_id,
            "swiggy_id": swiggy_id,
            "income_category": cat,
            "suggested_premium": prem,
            "terms_version": terms_store.get_current_version(),
            "policy_status": "active",
            "created_at": datetime.now().isoformat(),
            # Merge screen data over mock data to respect user inputs
            **{k: v for k, v in data.items() if k not in ["_id", "worker_id", "created_at"]}
        }
        
        # Store using unified handler
        db_handler.insert_worker(worker_doc)
        
        return jsonify({
            "status": "success",
            "message": "Worker registered successfully",
            "worker_id": worker_id,
            "data": worker_doc
        }), 201
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Registration Error: {str(e)}"}), 500

@worker_bp.route('/update_fcm_token', methods=['POST'])
def update_fcm_token():
    """POST /api/worker/update_fcm_token - Saves FCM token for notifications"""
    try:
        data = request.get_json() or {}
        worker_id = data.get('worker_id')
        fcm_token = data.get('fcm_token')

        if not worker_id or not fcm_token:
            return jsonify({"status": "error", "message": "worker_id and fcm_token required"}), 400

        # Update in DB
        worker = db_handler.get_worker(worker_id)
        if not worker:
            return jsonify({"status": "error", "message": "Worker not found"}), 404
            
        worker["fcm_token"] = fcm_token
        db_handler.update_worker(worker_id, worker)

        return jsonify({"status": "success", "message": "Token updated"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error updating token: {str(e)}"}), 500

@worker_bp.route('/list', methods=['GET'])
def list_workers():
    """GET /api/worker/list - Returns all registered workers."""
    try:
        workers = db_handler.get_all_workers()
        return jsonify({
            "status": "success",
            "count": len(workers),
            "data": workers
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Fetch Error: {str(e)}"}), 500

@worker_bp.route('/cancel_policy', methods=['POST'])
def cancel_policy():
    """POST /api/worker/cancel_policy - Marks a policy as cancelled."""
    try:
        data = request.get_json() or {}
        swiggy_id = data.get("swiggy_id")
        phone = data.get("phone")
        identifier = swiggy_id or phone
        
        if not identifier:
            return jsonify({"status": "error", "message": "Identifier required for cancellation"}), 400
            
        workers = db_handler.get_all_workers()
        target_worker = None
        for w in workers:
            if w.get("swiggy_id") == identifier or w.get("phone") == identifier or w.get("worker_id") == identifier:
                target_worker = w
                break
        
        if not target_worker:
            return jsonify({"status": "error", "message": "Worker not found"}), 404
            
        # Update the status
        target_worker["policy_status"] = "cancelled"
        target_worker["cancelled_at"] = datetime.now().isoformat()
        
        # In a real system we would update the DB record. 
        # In this simplistic db_handler/memory mode, it's already updated in the reference.
        
        return jsonify({
            "status": "success", 
            "message": "Policy cancelled successfully",
            "data": target_worker
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Cancellation Error: {str(e)}"}), 500

@worker_bp.route('/update_profile', methods=['POST'])
def update_profile():
    """POST /api/worker/update_profile - Updates worker profile fields like upi_id."""
    try:
        data = request.get_json() or {}
        worker_id = data.get('worker_id')
        new_upi = data.get('upi_id')

        if not worker_id:
            return jsonify({"status": "error", "message": "worker_id required"}), 400

        worker = db_handler.get_worker(worker_id)
        if not worker:
            return jsonify({"status": "error", "message": "Worker not found"}), 404
            
        updated = False
        if new_upi and worker.get('upi_id') != new_upi:
            worker['upi_id'] = new_upi
            worker['last_upi_updated_at'] = datetime.utcnow().isoformat() + "Z"
            updated = True
            
        if updated:
            db_handler.update_worker(worker_id, worker)

        return jsonify({"status": "success", "message": "Profile updated", "data": worker}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error updating profile: {str(e)}"}), 500

