import os
import requests
from flask import Blueprint, jsonify

payout_bp = Blueprint('payout', __name__, url_prefix='/api/payout')

@payout_bp.route('/status/<rrn>', methods=['GET'])
def get_payout_status(rrn):
    demo_mode = str(os.getenv("DEMO_MODE", "false")).lower() == "true"
    if demo_mode:
        return jsonify({"status": "processed", "rrn": rrn}), 200

    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    
    if not key_id or not key_secret:
        return jsonify({"error": "Keys not configured"}), 500
        
    try:
        res = requests.get(
            f"https://api.razorpay.com/v1/payouts/{rrn}",
            auth=(key_id, key_secret)
        )
        if res.ok:
            data = res.json()
            return jsonify({"status": data.get("status", "unknown"), "rrn": rrn}), 200
        else:
            return jsonify({"error": res.json()}), res.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500
