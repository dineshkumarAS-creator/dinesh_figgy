from flask import Blueprint, request, jsonify
import asyncio
import time
from app.utils.disruption_client import DisruptionClient
from app.utils.disruption_scorer import DisruptionScorer, ZoneRiskResult
from app.models import db_handler

radar_bp = Blueprint('radar', __name__)

# --- Manual rate limit store ---
_summary_rate_limit = {}

ZONE_BOUNDARIES = {
    "A": {"zone_name": "Anna Nagar", "lat_min": 13.09, "lat_max": 13.13, "lng_min": 80.21, "lng_max": 80.25},
    "B": {"zone_name": "T Nagar", "lat_min": 13.03, "lat_max": 13.06, "lng_min": 80.22, "lng_max": 80.24},
    "C": {"zone_name": "Adyar", "lat_min": 13.00, "lat_max": 13.03, "lng_min": 80.24, "lng_max": 80.27},
    "D": {"zone_name": "Nungambakkam", "lat_min": 13.06, "lat_max": 13.09, "lng_min": 80.23, "lng_max": 80.26},
}

ZONE_CONFIG = {
    "A": {"zone_id": "A", "zone_name": "Anna Nagar", "zone_letter": "A", "distance_km": 4.1, "eta_min": 10},
    "B": {"zone_id": "B", "zone_name": "T Nagar", "zone_letter": "B", "distance_km": 2.7, "eta_min": 7},
    "C": {"zone_id": "C", "zone_name": "Adyar", "zone_letter": "C", "distance_km": 3.2, "eta_min": 8},
    "D": {"zone_id": "D", "zone_name": "Nungambakkam", "zone_letter": "D", "distance_km": 5.0, "eta_min": 12},
}


@radar_bp.route('/api/radar/disruption', methods=['GET'])
def get_disruption_radar():
    zone_id = request.args.get('zone_id', 'default')
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    disruption_data = loop.run_until_complete(DisruptionClient.fetch_all(zone_id))
    loop.close()

    scorer = DisruptionScorer()
    risk = scorer.score(
        zone_id=zone_id,
        weather=disruption_data.get('fetch_weather', {}),
        govt=disruption_data.get('fetch_govt_alerts', []),
        news=disruption_data.get('fetch_news_signals', {}),
        social=disruption_data.get('fetch_social_signals', {})
    )
    # Merge disruption data and risk result
    response = {
        "zone_id": zone_id,
        "signals": disruption_data,
        "risk": risk.__dict__,
    }
    return jsonify(response)


@radar_bp.route('/radar/summary', methods=['GET'])
def radar_summary():
    """
    Aggregated radar summary for a worker.
    Combines zones, earnings, location risk, and pending claims.
    Rate limited: 1 per 30s per worker_id
    """
    worker_id = request.args.get('worker_id')
    if not worker_id:
        return jsonify({"error": "worker_id required"}), 400
    
    # Rate limit check
    now = time.time()
    last = _summary_rate_limit.get(worker_id, 0)
    if now - last < 30:
        return jsonify({"error": "Rate limit: 1 request per 30 seconds"}), 429
    _summary_rate_limit[worker_id] = now
    
    try:
        # 1. Get worker record
        worker = None
        try:
            worker = db_handler.get_worker(worker_id)
        except Exception:
            pass
        
        if not worker:
            return jsonify({"error": "Worker not found"}), 404
        
        # 2. Get earnings today
        earned_inr = float(worker.get("earnings_today", 0) or 0)
        rides_done = int(worker.get("rides_done_today", 0) or 0)
        protected_inr = 0  # TODO: aggregate from successful claims today
        
        # 3. Get pending claim
        claim_pending = None
        try:
            claims = db_handler.get_claims_by_worker(worker_id)
            for claim in claims:
                if claim.get("status") in ["under_review", "approved", "processing"]:
                    claim_pending = {
                        "amount_inr": claim.get("income_loss", 0),
                        "reason": claim.get("claim_source", "manual"),
                        "claim_id": claim.get("claim_id")
                    }
                    break
        except Exception:
            pass
        
        # 4. Get zones with opportunity index
        import random
        MAX_ORDERS = 20
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
            order_count = random.randint(5, MAX_ORDERS)
            boost_inr = random.choice([0, 50, 100, 180, 250])
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
        
        # Sort zones by opportunity index
        zones.sort(key=lambda z: z["opportunity_index"], reverse=True)
        for idx, z in enumerate(zones):
            z["recommended"] = (idx == 0)
        
        # 5. Get current location and call /telemetry/location
        last_lat = float(worker.get("last_lat", 13.05) or 13.05)
        last_lng = float(worker.get("last_lng", 80.24) or 80.24)
        rider_risk = {
            "in_risk_zone": False,
            "zone_id": None,
            "risk_label": "Safe",
            "protection_auto_on": False
        }
        
        # Reverse geocode location to zone
        for zone_id, bounds in ZONE_BOUNDARIES.items():
            if bounds['lat_min'] <= last_lat <= bounds['lat_max'] and bounds['lng_min'] <= last_lng <= bounds['lng_max']:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                signals = loop.run_until_complete(DisruptionClient.fetch_all(zone_id))
                risk = scorer.score(
                    zone_id=zone_id,
                    weather=signals.get('fetch_weather', {}),
                    govt=signals.get('fetch_govt_alerts', []),
                    news=signals.get('fetch_news_signals', {}),
                    social=signals.get('fetch_social_signals', {})
                )
                loop.close()
                rider_risk = {
                    "in_risk_zone": risk.risk_score > 60,
                    "zone_id": zone_id,
                    "risk_label": risk.risk_label,
                    "protection_auto_on": risk.risk_score > 60
                }
                break
        
        # 6. Build alert message
        alert_severity = "None"
        alert_message = "All zones clear"
        for zone in zones:
            if zone["risk_score"] > 60:
                alert_severity = "High"
                alert_message = f"{zone['primary_signal'].capitalize()} active in {zone['zone_name']}. "
                safe_zones = [z["zone_name"] for z in zones if z["risk_score"] < 30]
                if safe_zones:
                    alert_message += f"{' and '.join(safe_zones)} are clear."
                break
            elif zone["risk_score"] > 30:
                alert_severity = "Moderate"
        
        return jsonify({
            "alert": {
                "severity": alert_severity,
                "message": alert_message
            },
            "zones": zones,
            "earnings_today": {
                "earned_inr": earned_inr,
                "rides_done": rides_done,
                "protected_inr": protected_inr,
                "claim_pending": claim_pending
            },
            "rider_risk": rider_risk
        })
    
    except Exception as e:
        import logging
        logger = logging.getLogger("FIGGY_APP")
        logger.error(f"[RADAR_SUMMARY] Error: {e}")
        return jsonify({"error": str(e)}), 500
