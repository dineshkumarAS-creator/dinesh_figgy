import logging
from flask import Blueprint, request, jsonify
from datetime import datetime
from app.utils.disruption_client import DisruptionClient
from app.utils.disruption_scorer import DisruptionScorer
from app.utils.calculations import predict_income_loss

logger = logging.getLogger("FIGGY_APP")

telemetry_bp = Blueprint('telemetry', __name__)

# Simple in-memory store for the hackathon
memory_telemetry = []

# --- MVP ZONE BOUNDARIES (bounding boxes) ---
ZONE_BOUNDARIES = {
    "A": {"zone_name": "Anna Nagar", "lat_min": 13.09, "lat_max": 13.13, "lng_min": 80.21, "lng_max": 80.25},
    "B": {"zone_name": "T Nagar", "lat_min": 13.03, "lat_max": 13.06, "lng_min": 80.22, "lng_max": 80.24},
    "C": {"zone_name": "Adyar", "lat_min": 13.00, "lat_max": 13.03, "lng_min": 80.24, "lng_max": 80.27},
    "D": {"zone_name": "Nungambakkam", "lat_min": 13.06, "lat_max": 13.09, "lng_min": 80.23, "lng_max": 80.26},
}

# --- In-memory worker state ---
worker_state = {}

@telemetry_bp.route('/api/worker/telemetry', methods=['POST'])
def save_telemetry():
    """Receive live telemetry from worker app."""
    try:
        data = request.get_json() or {}
        worker_id = data.get('worker_id')
        
        if not worker_id:
            return jsonify({"status": "error", "message": "worker_id is required"}), 400
            
        # Append timestamp if missing
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow().isoformat() + "Z"
            
        memory_telemetry.append(data)
        
        return jsonify({
            "status": "success", 
            "message": "Telemetry saved", 
            "telemetry_count": len(memory_telemetry)
        }), 201

    except Exception as e:
        logger.error(f"Error saving telemetry: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@telemetry_bp.route('/api/worker/telemetry_summary/<worker_id>', methods=['GET'])
def get_telemetry_summary(worker_id):
    """Return aggregated telemetry summary for a worker."""
    try:
        # Check if we have real telemetry points for this worker
        worker_points = [t for t in memory_telemetry if t.get('worker_id') == worker_id]
        
        # Return the expected mock aggregation for the UI exactly as required
        return jsonify({
            "status": "success",
            "worker_id": worker_id,
            "active_hours": 5,
            "normal_deliveries": 20,
            "rainday_deliveries": 2,
            "disruption_earnings": 119,
            "gps_km_during_disruption": 12.4,
            "data_points": len(worker_points)
        }), 200

    except Exception as e:
        logger.error(f"Error fetching telemetry summary: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@telemetry_bp.route('/telemetry/location', methods=['POST'])
def location_telemetry():
    data = request.get_json(force=True)
    worker_id = data.get('worker_id')
    lat = data.get('lat')
    lng = data.get('lng')
    if not worker_id or lat is None or lng is None:
        return jsonify({"error": "worker_id, lat, lng required"}), 400

    # 1. Reverse-geocode to zone_id
    zone_id = None
    for zid, bounds in ZONE_BOUNDARIES.items():
        if bounds['lat_min'] <= lat <= bounds['lat_max'] and bounds['lng_min'] <= lng <= bounds['lng_max']:
            zone_id = zid
            break
    if not zone_id:
        return jsonify({"error": "Location outside supported zones"}), 400
    zone_name = ZONE_BOUNDARIES[zone_id]['zone_name']

    # 2. Run DisruptionScorer
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    signals = loop.run_until_complete(DisruptionClient.fetch_all(zone_id))
    scorer = DisruptionScorer()
    risk = scorer.score(
        zone_id=zone_id,
        weather=signals.get('fetch_weather', {}),
        govt=signals.get('fetch_govt_alerts', []),
        news=signals.get('fetch_news_signals', {}),
        social=signals.get('fetch_social_signals', {})
    )
    loop.close()

    # 3. If risk_score > 60, push FCM, set protection, call predict_income_loss
    protection_auto_on = False
    recommended_zone_id = zone_id
    income_loss = {}
    if risk.risk_score > 60:
        # Find safest zone
        safe_zones = [(zid, ZONE_BOUNDARIES[zid]['zone_name']) for zid in ZONE_BOUNDARIES if zid != zone_id]
        recommended_zone_id = zone_id
        min_risk = risk.risk_score
        for zid, _ in safe_zones:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            sig = loop.run_until_complete(DisruptionClient.fetch_all(zid))
            r = scorer.score(
                zone_id=zid,
                weather=sig.get('fetch_weather', {}),
                govt=sig.get('fetch_govt_alerts', []),
                news=sig.get('fetch_news_signals', {}),
                social=sig.get('fetch_social_signals', {})
            )
            loop.close()
            if r.risk_score < min_risk:
                min_risk = r.risk_score
                recommended_zone_id = zid
        # a. Push FCM notification (mock)
        from app.utils import notification_service
        notification_service.push_fcm(
            worker_id,
            f"High disruption risk in {zone_name}. Zone {ZONE_BOUNDARIES[recommended_zone_id]['zone_name']} is clear — head there now."
        )
        # b. Set protection_auto_on
        worker_state[worker_id] = {"protection_auto_on": True}
        protection_auto_on = True
        # c. Call predict_income_loss (with risk_score)
        income_loss = predict_income_loss(worker_id, zone_id, risk.risk_score)
    else:
        worker_state[worker_id] = {"protection_auto_on": False}

    return jsonify({
        "in_risk_zone": risk.risk_score > 60,
        "zone_id": zone_id,
        "risk_label": risk.risk_label,
        "risk_score": risk.risk_score,
        "protection_auto_on": protection_auto_on,
        "recommended_zone_id": recommended_zone_id,
        "income_loss": income_loss
    })
