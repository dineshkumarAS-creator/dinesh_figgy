from flask import Blueprint, request, jsonify
from app.utils.recommendation_engine import get_recommendations

policy_bp = Blueprint("policy", __name__, url_prefix="/api/policy")

@policy_bp.route("/match", methods=["POST"])
def match_policy():
    """
    POST /api/policy/match
    Input: worker profile JSON
    Output: ranked list of policy recommendations.
    """
    try:
        data = request.get_json() or {}
        
        # REQUIRED FIELDS
        required_fields = ["worker_id", "age", "monthly_income", "job_type", "city", "risk_level", "existing_insurance"]
        # Check if they exist, or provide defaults if they are missing but we want it to be robust
        # For now, let's keep it strict or provide defaults as needed.
        
        # Build worker profile for engine
        worker_profile = {
            "worker_id": data.get("worker_id", "unknown"),
            "age": int(data.get("age", 25)),
            "monthly_income": int(data.get("monthly_income", 15000)),
            "job_type": data.get("job_type", "delivery"),
            "city": data.get("city", "Bangalore"),
            "risk_level": data.get("risk_level", "medium"),
            "existing_insurance": data.get("existing_insurance", False)
        }

        # Run Recommendation Engine
        recommendations = get_recommendations(worker_profile)
        
        # Format the response
        formatted_recommendations = []
        for rec in recommendations:
            formatted_recommendations.append({
                "policy_id": rec.get("policy_id"),
                "policy_name": rec.get("policy_name"),
                "score": int(rec.get("score")),
                "category": rec.get("category"),
                "description": rec.get("description"),
                "reason": rec.get("reason"),
                "official_link": rec.get("official_link")
            })

        return jsonify(formatted_recommendations), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Policy matching failed: {str(e)}",
        }), 500
