"""
Soft Verification Service - FastAPI Endpoints

Endpoints for challenge responses, status queries, and admin operations.
"""

from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel

from schemas import WorkerResponse, ChallengeResult, VerificationChallenge
from soft_verify.challenge import ChallengeFactory
from soft_verify.evaluator import ChallengeEvaluator
from soft_verify.notifier import WorkerNotifier

logger = structlog.get_logger()

app = FastAPI(title="FIGGY Soft Verification API", version="1.0.0")

# Global state
challenge_factory: Optional[ChallengeFactory] = None
evaluator: Optional[ChallengeEvaluator] = None
notifier: Optional[WorkerNotifier] = None

# Rate limiting (simple in-memory counter)
response_attempts: dict[str, int] = {}


# ============================================================================
# Models
# ============================================================================


class ResponseMessage(BaseModel):
    """Success response message."""

    success: bool
    message: str
    data: Optional[dict] = None


class ChallengeDetails(BaseModel):
    """Challenge details for frontend display."""

    challenge_id: str
    claim_id: str
    challenge_type: str
    expires_at: datetime
    expected_zone_id: str
    location_tolerance_km: float


# ============================================================================
# Authentication
# ============================================================================


def verify_jwt_token(authorization: str = Header(None)) -> str:
    """
    Verify JWT token and extract worker_id.

    In production: actual JWT verification.
    For now: simple mock auth.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization[7:]
    # Mock: extract worker_id from token
    # In production: decode JWT properly
    try:
        worker_id = f"worker_{token[:10]}"  # Mock extraction
        return worker_id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


# ============================================================================
# Endpoints
# ============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow()}


@app.post("/v1/soft-verify/respond", response_model=ResponseMessage)
async def respond_to_challenge(
    response: WorkerResponse,
    authorization: str = Header(None),
) -> ResponseMessage:
    """
    Submit response to location verification challenge.

    Rate limited: 5 attempts per challenge_id.

    Args:
        response: WorkerResponse with location and timing
        authorization: JWT token

    Returns:
        ResponseMessage with evaluation result
    """
    # Verify auth
    worker_id = verify_jwt_token(authorization)

    # Check rate limit
    rate_limit_key = f"response_attempts:{response.challenge_id}"
    attempt_count = response_attempts.get(rate_limit_key, 0)
    if attempt_count >= 5:
        raise HTTPException(status_code=429, detail="Too many attempts")

    response_attempts[rate_limit_key] = attempt_count + 1

    # Get challenge
    challenge = await challenge_factory.get_challenge(response.challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    if challenge.worker_id != worker_id:
        raise HTTPException(status_code=403, detail="Challenge not for this worker")

    # Evaluate response
    result: ChallengeResult = evaluator.evaluate_response(challenge, response)

    # Update challenge status
    now = datetime.now(timezone.utc)
    await challenge_factory.update_challenge_status(
        challenge_id=challenge.challenge_id,
        status="passed" if result.passed else "failed",
        response_data={
            "response_lat": response.response_lat,
            "response_lon": response.response_lon,
            "app_foreground": response.app_foreground,
        },
        evaluated_at=now,
    )

    logger.info(
        "challenge_response_submitted",
        challenge_id=response.challenge_id,
        worker_id=worker_id,
        passed=result.passed,
        recommendation=result.recommendation,
    )

    # Determine message
    if result.passed:
        message = "✅ Location verified! Your claim will be auto-approved."
    elif result.borderline:
        message = (
            f"⚠️  Your location is {result.distance_km:.2f}km from the zone. "
            "Your claim may require manual review."
        )
    else:
        message = f"❌ Verification failed: {result.failure_reason}"

    return ResponseMessage(
        success=True,
        message=message,
        data={
            "passed": result.passed,
            "distance_km": result.distance_km,
            "timing_score": result.timing_score,
            "recommendation": result.recommendation,
            "borderline": result.borderline,
        },
    )


@app.get("/v1/soft-verify/challenge/{worker_id}", response_model=Optional[ChallengeDetails])
async def get_active_challenge(
    worker_id: str,
    authorization: str = Header(None),
) -> Optional[ChallengeDetails]:
    """
    Get active challenge for worker.

    Args:
        worker_id: Worker identifier
        authorization: JWT token

    Returns:
        ChallengeDetails if challenge pending, None otherwise
    """
    # Verify auth
    auth_worker_id = verify_jwt_token(authorization)
    if auth_worker_id != f"worker_{worker_id}":
        raise HTTPException(status_code=403, detail="Unauthorized")

    challenge = await challenge_factory.get_worker_pending_challenge(worker_id)
    if not challenge:
        return None

    return ChallengeDetails(
        challenge_id=challenge.challenge_id,
        claim_id=challenge.claim_id,
        challenge_type=challenge.challenge_type,
        expires_at=challenge.expires_at,
        expected_zone_id=challenge.expected_zone_id,
        location_tolerance_km=challenge.location_tolerance_km,
    )


@app.get("/v1/soft-verify/status/{claim_id}")
async def get_challenge_status(claim_id: str) -> dict:
    """
    Get challenge status for a claim.

    Args:
        claim_id: Claim identifier

    Returns:
        Status dictionary with challenge state
    """
    # In production: lookup challenge by claim_id
    # For now: return mock status
    return {
        "claim_id": claim_id,
        "status": "pending",
        "challenge_id": f"chall_{claim_id[:8]}",
        "time_remaining_minutes": 15,
    }


@app.post("/v1/soft-verify/admin/force-expire/{challenge_id}")
async def admin_force_expire(
    challenge_id: str,
    api_key: str = Header(None),
) -> ResponseMessage:
    """
    Admin endpoint: Force expire a challenge (for testing/support).

    Args:
        challenge_id: Challenge to expire
        api_key: Admin API key

    Returns:
        Success message
    """
    # Verify admin API key
    if api_key != "admin_key_12345":  # Mock check
        raise HTTPException(status_code=403, detail="Invalid API key")

    challenge = await challenge_factory.get_challenge(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    # Update to expired
    now = datetime.now(timezone.utc)
    await challenge_factory.update_challenge_status(
        challenge_id=challenge_id,
        status="expired",
        evaluated_at=now,
    )

    logger.warning(
        "admin_force_expire",
        challenge_id=challenge_id,
        worker_id=challenge.worker_id,
    )

    return ResponseMessage(
        success=True,
        message=f"Challenge {challenge_id} has been expired",
    )


# ============================================================================
# Metrics
# ============================================================================


@app.get("/v1/metrics")
async def get_metrics() -> dict:
    """Get service metrics."""
    return {
        "challenge_factory": challenge_factory,  # Would return actual metrics
        "evaluator": evaluator,
        "notifier": notifier.get_metrics() if notifier else {},
    }
