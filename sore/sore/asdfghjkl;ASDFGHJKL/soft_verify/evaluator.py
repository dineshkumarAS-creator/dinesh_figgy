"""
Challenge Response Evaluator

Evaluates worker responses to location/timing challenges using Haversine distance.
"""

import math
from datetime import datetime, timezone
from typing import Optional

import structlog

from schemas import VerificationChallenge, WorkerResponse, ChallengeResult
from soft_verify import get_zone_config

logger = structlog.get_logger()


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance in km between two lat/lon points using Haversine formula.

    Args:
        lat1, lon1: First point
        lat2, lon2: Second point

    Returns:
        Distance in km
    """
    R = 6371.0  # Earth radius in km

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return R * c


class ChallengeEvaluator:
    """Evaluates worker responses to challenges."""

    def __init__(self):
        """Initialize evaluator."""
        self.zone_config = get_zone_config()

    def evaluate_response(
        self, challenge: VerificationChallenge, response: WorkerResponse
    ) -> ChallengeResult:
        """
        Evaluate worker's response to location challenge.

        Evaluation steps:
        1. Validate challenge + response integrity
        2. Compute distance from zone centroid
        3. Calculate timing score based on response time
        4. Determine pass/fail + recommendation

        Args:
            challenge: The challenge to evaluate against
            response: Worker's response

        Returns:
            ChallengeResult with pass/fail and recommendation
        """
        # Validation checks
        if challenge.status != "pending":
            return ChallengeResult(
                passed=False,
                distance_km=0.0,
                timing_score=0.0,
                failure_reason=f"Challenge not pending (status={challenge.status})",
                borderline=False,
                recommendation="reject",
            )

        now = datetime.now(timezone.utc)
        if now > challenge.expires_at:
            return ChallengeResult(
                passed=False,
                distance_km=0.0,
                timing_score=0.0,
                failure_reason="Challenge expired",
                borderline=False,
                recommendation="reject",
            )

        if challenge.worker_id != response.worker_id:
            return ChallengeResult(
                passed=False,
                distance_km=0.0,
                timing_score=0.0,
                failure_reason="Worker ID mismatch",
                borderline=False,
                recommendation="reject",
            )

        if response.response_timestamp > challenge.expires_at:
            return ChallengeResult(
                passed=False,
                distance_km=0.0,
                timing_score=0.0,
                failure_reason="Response submitted after expiry",
                borderline=False,
                recommendation="reject",
            )

        # =====================================================================
        # Location Validation (Haversine distance from zone centroid)
        # =====================================================================
        zone_centroid = self.zone_config.get_zone_centroid(challenge.expected_zone_id)
        distance_km = haversine_distance(
            zone_centroid[0],
            zone_centroid[1],
            response.response_lat,
            response.response_lon,
        )

        location_match = distance_km <= challenge.location_tolerance_km
        borderline = (
            distance_km > challenge.location_tolerance_km
            and distance_km <= challenge.location_tolerance_km + 0.5  # 0.5km buffer
        )

        logger.info(
            "location_evaluated",
            challenge_id=challenge.challenge_id,
            distance_km=distance_km,
            tolerance_km=challenge.location_tolerance_km,
            location_match=location_match,
            borderline=borderline,
        )

        # =====================================================================
        # Timing Validation
        # =====================================================================
        time_elapsed = (
            response.response_timestamp - challenge.issued_at
        ).total_seconds() / 60.0  # Convert to minutes

        total_window = challenge.expires_at - challenge.issued_at
        total_minutes = total_window.total_seconds() / 60.0

        # Timing score: 1.0 if responded < 10 min, linear decay after
        if time_elapsed < 10:
            timing_score = 1.0
        elif time_elapsed < 20:
            timing_score = 0.7 + (20 - time_elapsed) / 100  # Linear 0.7 to 0.7
            timing_score = 0.7
        elif time_elapsed < total_minutes:
            timing_score = 0.4
        else:
            timing_score = 0.0  # Too late

        logger.info(
            "timing_evaluated",
            challenge_id=challenge.challenge_id,
            time_elapsed_minutes=time_elapsed,
            timing_score=timing_score,
        )

        # =====================================================================
        # Pass/Fail Decision
        # =====================================================================
        passed = location_match and timing_score >= 0.4

        # Determine recommendation
        if borderline:
            # Borderline location - needs manual review
            recommendation = "manual_review"
            failure_reason = (
                f"Location just outside tolerance: {distance_km:.2f}km "
                f"(tolerance: {challenge.location_tolerance_km}km)"
            )
        elif not location_match:
            recommendation = "reject"
            failure_reason = (
                f"Location mismatch: {distance_km:.2f}km outside "
                f"tolerance of {challenge.location_tolerance_km}km"
            )
        elif timing_score < 0.4:
            recommendation = "reject"
            failure_reason = (
                f"Responded too late: {time_elapsed:.1f}min "
                f"(window: {total_minutes:.0f}min)"
            )
        elif passed:
            recommendation = "approve"
            failure_reason = None
        else:
            recommendation = "manual_review"
            failure_reason = "Inconclusive evaluation"

        logger.info(
            "challenge_evaluated",
            challenge_id=challenge.challenge_id,
            passed=passed,
            recommendation=recommendation,
        )

        return ChallengeResult(
            passed=passed,
            distance_km=distance_km,
            timing_score=timing_score,
            failure_reason=failure_reason,
            borderline=borderline,
            recommendation=recommendation,
        )

    def compute_distance(
        self, challenge: VerificationChallenge, lat: float, lon: float
    ) -> float:
        """Compute distance from zone centroid."""
        zone_centroid = self.zone_config.get_zone_centroid(challenge.expected_zone_id)
        return haversine_distance(zone_centroid[0], zone_centroid[1], lat, lon)
