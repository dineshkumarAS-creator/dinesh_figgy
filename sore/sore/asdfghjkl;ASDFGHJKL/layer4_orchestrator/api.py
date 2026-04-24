"""
FastAPI Debug API for Layer 4 Orchestrator

Endpoints:
- GET /health
- GET /v1/composite/{worker_id}
- GET /v1/routing/{worker_id}
- GET /v1/explain/{worker_id}
- GET /v1/dashboard
"""

import json
from datetime import datetime, timedelta

import aioredis
import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger()

app = FastAPI(title="Layer 4 Orchestrator API", version="1.0.0")

# Global state
redis_client: aioredis.Redis = None
score_collector = None
router = None
publisher = None


# ============================================================================
# Models
# ============================================================================


class HealthStatus(BaseModel):
    status: str
    timestamp: datetime
    version: str


class DashboardStats(BaseModel):
    hour_start: datetime
    hour_end: datetime
    auto_payout_count: int
    soft_verify_count: int
    manual_flag_count: int
    auto_payout_percent: float
    avg_composite_score: float
    median_composite_score: float
    p95_composite_score: float
    p99_composite_score: float
    model_timeout_rate_percent: float


# ============================================================================
# Initialization
# ============================================================================


async def initialize_redis(redis_url: str):
    """Initialize Redis connection."""
    global redis_client
    redis_client = await aioredis.from_url(redis_url, decode_responses=True)
    logger.info("Redis connected for API")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    if redis_client:
        await redis_client.close()


# ============================================================================
# Health Check
# ============================================================================


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    return HealthStatus(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
    )


# ============================================================================
# Composite Score Retrieval
# ============================================================================


@app.get("/v1/composite/{worker_id}")
async def get_latest_composite_score(worker_id: str):
    """
    Get latest composite claim score for a worker.

    Args:
        worker_id: Worker identifier

    Returns:
        CompositeClaimScore JSON
    """
    redis_key = f"composite_score:latest:{worker_id}"
    score_json = await redis_client.get(redis_key)

    if not score_json:
        raise HTTPException(
            status_code=404,
            detail=f"No composite score found for worker {worker_id}",
        )

    return json.loads(score_json)


# ============================================================================
# Routing Decision Retrieval
# ============================================================================


@app.get("/v1/routing/{worker_id}")
async def get_latest_routing_decision(worker_id: str):
    """
    Get latest routing decision for a worker.

    Args:
        worker_id: Worker identifier

    Returns:
        RoutingDecision JSON
    """
    redis_key = f"routing_decision:latest:{worker_id}"
    decision_json = await redis_client.get(redis_key)

    if not decision_json:
        raise HTTPException(
            status_code=404,
            detail=f"No routing decision found for worker {worker_id}",
        )

    return json.loads(decision_json)


# ============================================================================
# Explainability / Risk Signals
# ============================================================================


@app.get("/v1/explain/{worker_id}")
async def get_explainability(worker_id: str):
    """
    Get merged explainability signals for a worker.

    Returns top risk signals, score components, and model interpretations.

    Args:
        worker_id: Worker identifier

    Returns:
        Explainability summary with top_risk_signals, score_components
    """
    redis_key = f"composite_score:latest:{worker_id}"
    score_json = await redis_client.get(redis_key)

    if not score_json:
        raise HTTPException(
            status_code=404,
            detail=f"No score found for worker {worker_id}",
        )

    score = json.loads(score_json)
    return {
        "worker_id": worker_id,
        "composite_claim_score": score.get("composite_claim_score"),
        "confidence_level": score.get("confidence_level"),
        "anti_spoofing_flag": score.get("anti_spoofing_flag"),
        "top_risk_signals": score.get("top_risk_signals", []),
        "score_components": score.get("score_components", {}),
        "trigger_types_active": score.get("trigger_types_active", []),
        "explanation": _generate_explanation(score),
    }


def _generate_explanation(score: dict) -> str:
    """Generate human-readable explanation of score."""
    composite = score.get("composite_claim_score", 0)
    confidence = score.get("confidence_level", "unknown")
    disruption = score.get("disruption_score", 0)
    pow_conf = score.get("pow_confidence", 0)
    fraud_prob = score.get("fraud_probability", 0)

    parts = []
    parts.append(
        f"Composite claim score: {composite:.3f} ({confidence} confidence)"
    )
    parts.append(f"Disruption detected: {disruption:.1%} probability")
    parts.append(f"POW confidence: {pow_conf:.1%}")
    parts.append(f"Fraud probability: {fraud_prob:.1%}")

    if score.get("anti_spoofing_flag"):
        parts.append("⚠️  SPOOFING DETECTED")

    if score.get("top_risk_signals"):
        signals_str = "; ".join(
            f"{s['source']}: {s['signal']}"
            for s in score.get("top_risk_signals", [])[:5]
        )
        parts.append(f"Top risk signals: {signals_str}")

    return " | ".join(parts)


# ============================================================================
# Dashboard / Aggregated Stats
# ============================================================================


@app.get("/v1/dashboard", response_model=DashboardStats)
async def get_dashboard_stats():
    """
    Get aggregated statistics for last hour.

    Returns:
        Dashboard with routing breakdown, score distribution, model health
    """
    hour_start = datetime.utcnow() - timedelta(hours=1)
    hour_end = datetime.utcnow()

    # Scan Redis for all routing decisions in last hour
    # Note: In production, use a time-series DB or pre-aggregated metrics
    pattern = "routing_decision:latest:*"
    decisions = []
    scores = []

    cursor = 0
    while True:
        cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)

        for key in keys:
            decision_json = await redis_client.get(key)
            if decision_json:
                try:
                    decision = json.loads(decision_json)
                    routing_timestamp = datetime.fromisoformat(
                        decision.get("routing_timestamp").replace("Z", "+00:00")
                    )
                    if hour_start <= routing_timestamp <= hour_end:
                        decisions.append(decision)
                except Exception as e:
                    logger.error("dashboard_parse_error", error=str(e))

        if cursor == 0:
            break

    # Get all composite scores for distribution analysis
    pattern = "composite_score:latest:*"
    cursor = 0
    while True:
        cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)

        for key in keys:
            score_json = await redis_client.get(key)
            if score_json:
                try:
                    score = json.loads(score_json)
                    scores.append(score.get("composite_claim_score", 0))
                except Exception as e:
                    logger.error("dashboard_parse_error", error=str(e))

        if cursor == 0:
            break

    # Calculate stats
    auto_payout = sum(1 for d in decisions if d.get("route") == "auto_payout")
    soft_verify = sum(1 for d in decisions if d.get("route") == "soft_verify")
    manual_flag = sum(1 for d in decisions if d.get("route") == "manual_flag")
    total = len(decisions)

    auto_payout_percent = (auto_payout / total * 100) if total > 0 else 0

    # Score distribution
    if scores:
        scores_sorted = sorted(scores)
        avg_score = sum(scores) / len(scores)
        median_score = scores_sorted[len(scores) // 2]
        p95_idx = max(0, int(len(scores) * 0.95) - 1)
        p99_idx = max(0, int(len(scores) * 0.99) - 1)
        p95_score = scores_sorted[p95_idx]
        p99_score = scores_sorted[p99_idx]
    else:
        avg_score = median_score = p95_score = p99_score = 0.0

    # Model timeout rate (from score_collector if available)
    model_timeout_rate = 0.0
    if score_collector:
        metrics = score_collector.get_metrics()
        model_timeout_rate = metrics.get("timeout_rate_percent", 0.0)

    return DashboardStats(
        hour_start=hour_start,
        hour_end=hour_end,
        auto_payout_count=auto_payout,
        soft_verify_count=soft_verify,
        manual_flag_count=manual_flag,
        auto_payout_percent=auto_payout_percent,
        avg_composite_score=avg_score,
        median_composite_score=median_score,
        p95_composite_score=p95_score,
        p99_composite_score=p99_score,
        model_timeout_rate_percent=model_timeout_rate,
    )


# ============================================================================
# Metrics Endpoints
# ============================================================================


@app.get("/v1/metrics/collector")
async def get_collector_metrics():
    """Get score collector metrics."""
    if not score_collector:
        raise HTTPException(status_code=503, detail="Collector not initialized")
    return score_collector.get_metrics()


@app.get("/v1/metrics/router")
async def get_router_metrics():
    """Get router metrics."""
    if not router:
        raise HTTPException(status_code=503, detail="Router not initialized")
    return router.get_metrics()


@app.get("/v1/metrics/publisher")
async def get_publisher_metrics():
    """Get publisher metrics."""
    if not publisher:
        raise HTTPException(status_code=503, detail="Publisher not initialized")
    return publisher.get_metrics()
