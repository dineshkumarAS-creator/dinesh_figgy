"""
Manual Review Reviewer Decision API

FastAPI endpoints for reviewers to access queue, view claims, and make decisions.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Optional

import structlog
from fastapi import FastAPI, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
import redis.asyncio as aioredis
from aiokafka import AIOKafkaProducer

from manual_review.schemas import (
    ReviewQueueItem,
    ManualReviewDecision,
    ReviewerStats,
    ReviewContext,
)
from manual_review.queue import ReviewQueueService
from manual_review.reviewers import ReviewerService
from manual_review.context_builder import ClaimContextBuilder

logger = structlog.get_logger()

app = FastAPI(title="Manual Review API")


# ==============================================================================
# Mock Auth (replace with real JWT in production)
# ==============================================================================


class ReviewerAuth(BaseModel):
    """Reviewer authentication info from JWT or header."""

    reviewer_id: str
    name: str
    role: str  # "junior", "senior", "lead"
    email: str


async def get_current_reviewer(authorization: str = None) -> ReviewerAuth:
    """
    Extract reviewer from JWT bearer token.

    In production, decode JWT and validate.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")

    # For demo: extract from header like "Bearer reviewer_id:role"
    # Real implementation would decode JWT
    try:
        token = authorization.replace("Bearer ", "")
        parts = token.split(":")
        if len(parts) < 2:
            raise ValueError("Invalid token format")

        return ReviewerAuth(
            reviewer_id=parts[0],
            name=parts[0],  # In real system: from JWT claims
            role=parts[1] if len(parts) > 1 else "junior",
            email=f"{parts[0]}@figgy.app",
        )
    except Exception as e:
        logger.error("auth_error", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid token")


# ==============================================================================
# Request/Response Models
# ==============================================================================


class QueueItemResponse(BaseModel):
    """Queue item in response."""

    queue_id: str
    claim_id: str
    worker_id: str
    priority: int
    risk_score: float
    payout_eligible_inr: float
    status: str
    assigned_reviewer_id: Optional[str] = None
    sla_deadline: str


class DecisionRequest(BaseModel):
    """Decision request from reviewer."""

    decision: str = Field(..., pattern="^(approve|reject|request_more_info)$")
    rejection_reason: Optional[str] = None
    payout_override_inr: Optional[float] = None
    notes: Optional[str] = None
    confidence: int = Field(..., ge=1, le=5)


class DecisionResponse(BaseModel):
    """Decision response."""

    queue_id: str
    claim_id: str
    decision: str
    decided_at: str
    message: str


class ClaimContextResponse(BaseModel):
    """Claim context response (nested)."""

    claim_id: str
    queue_id: str
    risk_score: float
    recommended_action: str
    ml_explanations: dict
    worker_trust_profile: dict
    crowd_validation: dict
    zone_disruption_map: dict


# ==============================================================================
# Service Initialization
# ==============================================================================


async def get_redis() -> aioredis.Redis:
    """Get Redis client."""
    return await aioredis.from_url("redis://localhost:6379", decode_responses=True)


async def get_queue_service(redis: aioredis.Redis = Depends(get_redis)) -> ReviewQueueService:
    """Get review queue service."""
    # In production, use real PostgreSQL session
    return ReviewQueueService(db_session=None, redis_client=redis)


async def get_reviewer_service(redis: aioredis.Redis = Depends(get_redis)) -> ReviewerService:
    """Get reviewer service."""
    return ReviewerService(redis_client=redis)


async def get_context_builder(redis: aioredis.Redis = Depends(get_redis)) -> ClaimContextBuilder:
    """Get context builder."""
    return ClaimContextBuilder(redis_client=redis, anthropic_api_key=None)


# ==============================================================================
# API Endpoints
# ==============================================================================


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "service": "manual-review-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/review/queue")
async def get_queue(
    priority: Optional[int] = Query(None, ge=1, le=3),
    limit: int = Query(10, ge=1, le=50),
    reviewer: ReviewerAuth = Depends(get_current_reviewer),
    queue_service: ReviewQueueService = Depends(get_queue_service),
):
    """
    Get pending review queue items.

    Returns items filtered by reviewer's role and specialisation.
    Junior reviewers cannot see priority=1 (critical) items.
    """
    # Filter by role capability
    if priority == 1 and reviewer.role == "junior":
        raise HTTPException(
            status_code=403,
            detail="Junior reviewers cannot review critical claims",
        )

    items = await queue_service.get_pending_items(priority=priority, limit=limit)

    return {
        "items": [
            QueueItemResponse(
                queue_id=item.queue_id,
                claim_id=item.claim_id,
                worker_id=item.worker_id,
                priority=item.priority,
                risk_score=item.risk_score,
                payout_eligible_inr=item.payout_eligible_inr,
                status=item.status,
                assigned_reviewer_id=item.assigned_reviewer_id,
                sla_deadline=item.sla_deadline.isoformat(),
            )
            for item in items
        ],
        "total": len(items),
    }


@app.post("/v1/review/claim/{queue_id}/assign")
async def assign_claim(
    queue_id: str,
    reviewer: ReviewerAuth = Depends(get_current_reviewer),
    queue_service: ReviewQueueService = Depends(get_queue_service),
    reviewer_service: ReviewerService = Depends(get_reviewer_service),
):
    """
    Assign a claim to the current reviewer.

    Validates reviewer has capacity and is eligible for priority level.
    """
    item = await queue_service.get_by_id(queue_id)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")

    if item.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Claim is already {item.status}",
        )

    # Role check
    if item.priority == 1 and reviewer.role == "junior":
        raise HTTPException(
            status_code=403,
            detail="Junior reviewers cannot review critical claims",
        )

    # Check capacity
    profile = await reviewer_service.get_reviewer(reviewer.reviewer_id)
    if profile and profile.current_load >= profile.max_load:
        raise HTTPException(
            status_code=400,
            detail=f"Reviewer at max load ({profile.max_load} claims)",
        )

    # Assign
    now = datetime.now(timezone.utc)
    item.assigned_reviewer_id = reviewer.reviewer_id
    item.assigned_at = now
    item.status = "assigned"

    # Store in Redis (in production: also update PostgreSQL)
    await queue_service.redis.set(
        f"queue:item:{queue_id}",
        item.model_dump_json(),
        ex=3600 * 24,
    )

    # Update reviewer load
    await reviewer_service.update_load(reviewer.reviewer_id, delta=+1)

    logger.info(
        "claim_assigned",
        queue_id=queue_id,
        claim_id=item.claim_id,
        reviewer_id=reviewer.reviewer_id,
    )

    return {
        "message": "Claim assigned successfully",
        "queue_id": queue_id,
        "sla_deadline": item.sla_deadline.isoformat(),
    }


@app.get("/v1/review/claim/{claim_id}/context")
async def get_claim_context(
    claim_id: str,
    reviewer: ReviewerAuth = Depends(get_current_reviewer),
    context_builder: ClaimContextBuilder = Depends(get_context_builder),
):
    """
    Get full claim review context.

    This endpoint is intentionally slow (2-3s) due to Claude API call.
    Results are cached in Redis for 10 minutes.
    """
    try:
        # In production: fetch claim data from ClaimService
        # For demo: mock data
        context = await context_builder.build_review_context(
            claim_id=claim_id,
            claim_data={
                "claim_id": claim_id,
                "worker_id": "worker_123",
                "payout_eligible_inr": 500.0,
                "is_new_worker": True,
            },
            claim_history=[],
            feature_snapshot={
                "motion_continuity": 0.45,
                "road_match_score": 0.12,
                "app_foreground_duration_pct": 25.0,
            },
            risk_breakdown={"tier": "TIER_3", "score": 0.75},
            lstm_attention_weights=[0.05] * 30,
            if_top_signals=[
                {"feature": "road_match_score", "value": 0.12, "shap_value": -0.15},
                {"feature": "motion_continuity", "value": 0.45, "shap_value": 0.08},
            ],
            gbm_top_signals=[
                {"feature": "gps_accuracy", "value": 200.0, "shap_value": 0.12},
            ],
            worker_id="worker_123",
            worker_trust_data={"total_claims": 1, "is_new_worker": True},
            crowd_validation_result={"crowd_spike_flag": False},
            similar_past_claims=[],
            zone_disruption_map={"zone_block_1": 0.05},
            queue_id="queue_123",
            risk_score=0.75,
        )

        return {
            "claim_id": context.claim_id,
            "queue_id": context.queue_id,
            "risk_score": context.risk_score,
            "recommended_action": context.recommended_action,
            "ml_explanations": {
                "human_readable_summary": context.ml_explanations.human_readable_summary,
                "top_signals": [
                    s.model_dump()
                    for s in (context.ml_explanations.if_top_signals +
                             context.ml_explanations.gbm_top_signals)[:5]
                ],
            },
            "worker_trust_profile": context.worker_trust_profile.model_dump(),
            "crowd_validation": context.crowd_validation.model_dump(),
            "zone_disruption_map": context.zone_disruption_map,
        }

    except Exception as e:
        logger.error("context_build_error", claim_id=claim_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to build context")


@app.post("/v1/review/claim/{queue_id}/decide")
async def decide_claim(
    queue_id: str,
    decision_req: DecisionRequest,
    reviewer: ReviewerAuth = Depends(get_current_reviewer),
    queue_service: ReviewQueueService = Depends(get_queue_service),
    reviewer_service: ReviewerService = Depends(get_reviewer_service),
):
    """
    Submit reviewer decision on a claim.

    Publishes decision to Kafka for ML training and claim processing.
    """
    item = await queue_service.get_by_id(queue_id)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")

    if item.assigned_reviewer_id != reviewer.reviewer_id:
        raise HTTPException(
            status_code=403,
            detail="Claim not assigned to you",
        )

    if item.status not in ["assigned", "in_review"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot decide on {item.status} claim",
        )

    # Create decision
    now = datetime.now(timezone.utc)
    decision = ManualReviewDecision(
        queue_id=queue_id,
        claim_id=item.claim_id,
        reviewer_id=reviewer.reviewer_id,
        decision=decision_req.decision,
        rejection_reason=decision_req.rejection_reason,
        payout_override_inr=decision_req.payout_override_inr,
        notes=decision_req.notes,
        confidence=decision_req.confidence,
        decided_at=now,
    )

    # Mark as decided
    await queue_service.mark_decided(queue_id, decision)

    # Calculate decision time
    if item.assigned_at:
        decision_time_min = (now - item.assigned_at).total_seconds() / 60
    else:
        decision_time_min = 0.0

    # Update reviewer stats
    await reviewer_service.record_decision(
        reviewer_id=reviewer.reviewer_id,
        decision=decision.decision,
        decision_time_min=decision_time_min,
    )

    # Publish to Kafka (in production)
    # await kafka_producer.send_and_wait(
    #     "manual_review_outcomes",
    #     decision.model_dump_json().encode(),
    # )

    logger.info(
        "decision_submitted",
        queue_id=queue_id,
        claim_id=item.claim_id,
        decision=decision.decision,
        reviewer_id=reviewer.reviewer_id,
        decision_time_min=decision_time_min,
        confidence=decision.confidence,
    )

    return DecisionResponse(
        queue_id=queue_id,
        claim_id=item.claim_id,
        decision=decision.decision,
        decided_at=decision.decided_at.isoformat(),
        message=f"Decision recorded: {decision.decision}",
    )


@app.get("/v1/review/stats")
async def get_reviewer_stats(
    reviewer: ReviewerAuth = Depends(get_current_reviewer),
    reviewer_service: ReviewerService = Depends(get_reviewer_service),
):
    """Get reviewer's statistics."""
    stats = await reviewer_service.get_stats(reviewer.reviewer_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Reviewer not found")

    return stats.model_dump()


@app.post("/v1/review/claim/{queue_id}/release")
async def release_claim(
    queue_id: str,
    reviewer: ReviewerAuth = Depends(get_current_reviewer),
    queue_service: ReviewQueueService = Depends(get_queue_service),
    reviewer_service: ReviewerService = Depends(get_reviewer_service),
):
    """
    Release a claim back to queue without deciding.

    Useful for lunch breaks or when handoff needed.
    """
    item = await queue_service.get_by_id(queue_id)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")

    if item.assigned_reviewer_id != reviewer.reviewer_id:
        raise HTTPException(status_code=403, detail="Not assigned to you")

    await queue_service.release(queue_id, reviewer.reviewer_id)
    await reviewer_service.update_load(reviewer.reviewer_id, delta=-1)

    return {"message": f"Claim {queue_id} released back to queue"}


@app.get("/v1/review/metrics")
async def get_metrics(
    reviewer: ReviewerAuth = Depends(get_current_reviewer),
    queue_service: ReviewQueueService = Depends(get_queue_service),
):
    """Get review system metrics."""
    if reviewer.role != "lead":
        raise HTTPException(
            status_code=403,
            detail="Only lead reviewers can access metrics",
        )

    queue_metrics = await queue_service.get_queue_metrics()
    return queue_metrics
