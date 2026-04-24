from flask import Blueprint, jsonify, request
import random, math
import time
from app.utils.disruption_client import DisruptionClient
from app.utils.disruption_scorer import DisruptionScorer
from flask import current_app
import asyncio


demand_bp = Blueprint("demand", __name__, url_prefix="/api/demand")

# Stub demand data — in production replace with real LSTM output
ZONE_DEMAND = {
    "North": {"base_index": 0.72, "peak_hours": [12, 13, 19, 20, 21]},
    "South": {"base_index": 0.58, "peak_hours": [11, 12, 19, 20]},
    "East": {"base_index": 0.65, "peak_hours": [12, 13, 20, 21]},
    "West": {"base_index": 0.48, "peak_hours": [11, 12, 18, 19]},
    "Central": {"base_index": 0.81, "peak_hours": [11, 12, 13, 19, 20, 21]},
}

# --- ZONE CONFIG ---
ZONE_CONFIG = {
    "A": {"zone_id": "A", "zone_name": "Anna Nagar", "zone_letter": "A", "distance_km": 4.1, "eta_min": 10},
    "B": {"zone_id": "B", "zone_name": "T Nagar", "zone_letter": "B", "distance_km": 2.7, "eta_min": 7},
    "C": {"zone_id": "C", "zone_name": "Adyar", "zone_letter": "C", "distance_km": 3.2, "eta_min": 8},
    "D": {"zone_id": "D", "zone_name": "Nungambakkam", "zone_letter": "D", "distance_km": 5.0, "eta_min": 12},
}
MAX_ORDERS = 20

# --- Manual rate limit store ---
_last_req_time = {}

@demand_bp.route("/zone/<zone_name>", methods=["GET"])
def zone_demand(zone_name):
    zone_data = ZONE_DEMAND.get(zone_name, ZONE_DEMAND["Central"])
    from datetime import datetime

    hour = datetime.utcnow().hour + 5  # IST
    is_peak = hour % 24 in zone_data["peak_hours"]
    demand = zone_data["base_index"] * (1.3 if is_peak else 0.85)
    return jsonify(
        {
            "zone": zone_name,
            "demand_index": round(min(demand, 1.0), 2),
            "forecast_label": "High demand" if demand > 0.7 else "Moderate",
            "recommended": demand > 0.65,
            "model": "LSTM-stub-v1",
            "peak_hours": zone_data["peak_hours"],
        }
    )

@demand_bp.route("/zones", methods=["GET"])
def demand_zones():
    worker_id = request.args.get("worker_id")
    if not worker_id:
        return jsonify({"error": "worker_id required"}), 400
    now = time.time()
    last = _last_req_time.get(worker_id, 0)
    if now - last < 30:
        return jsonify({"error": "Rate limit: 1 request per 30 seconds"}), 429
    _last_req_time[worker_id] = now

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    scorer = DisruptionScorer()
    zones = []
    for zid, zinfo in ZONE_CONFIG.items():
        signals = loop.run_until_complete(DisruptionClient.fetch_all(zid))
        risk = scorer.score(
            zone_id=zid,
            weather=signals.get('fetch_weather', {}),
            govt=signals.get('fetch_govt_alerts', []),
            news=signals.get('fetch_news_signals', {}),
            social=signals.get('fetch_social_signals', {})
        )
        # --- DEMAND DATA (stub) ---
        order_count = random.randint(5, MAX_ORDERS)
        boost_inr = random.choice([0, 50, 100, 180, 250])
        # --- OPPORTUNITY INDEX ---
        opportunity_index = round(
            (order_count / MAX_ORDERS) * (1 - risk.risk_score / 100) * (1 + boost_inr / 500),
            3
        )
        zones.append({
            **zinfo,
            "order_count": order_count,
            "boost_inr": boost_inr,
            "risk_score": round(risk.risk_score, 2),
            "risk_label": risk.risk_label,
            "primary_signal": risk.primary_signal,
            "alert_text": risk.alert_text,
            "opportunity_index": opportunity_index,
        })
    loop.close()
    # Sort and mark recommended
    zones.sort(key=lambda z: z["opportunity_index"], reverse=True)
    if zones:
        zones[0]["recommended"] = True
    for z in zones[1:]:
        z["recommended"] = False
    return jsonify({"zones": zones})
