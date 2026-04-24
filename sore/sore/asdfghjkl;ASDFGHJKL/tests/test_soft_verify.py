"""
Tests for Soft Verification Service

Tests location validation, timing validation, and challenge lifecycle.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from soft_verify.evaluator import ChallengeEvaluator, haversine_distance
from soft_verify.challenge import ChallengeFactory
from schemas import VerificationChallenge, WorkerResponse


@pytest.fixture
def evaluator():
    """Create evaluator instance."""
    return ChallengeEvaluator()


@pytest.fixture
def challenge_at_zone_center():
    """Create challenge with zone at known coordinates."""
    now = datetime.now(timezone.utc)
    return VerificationChallenge(
        challenge_id="test_challenge_1",
        claim_id="claim_123",
        worker_id="worker_456",
        challenge_type="location_ping",
        issued_at=now,
        expires_at=now + timedelta(minutes=30),
        expected_zone_id="DL-CENTRAL-01",
        expected_lat_range=(28.60, 28.65),
        expected_lon_range=(77.20, 77.25),
        location_tolerance_km=2.0,
        status="pending",
    )


# ==============================================================================
# Haversine Distance Tests
# ==============================================================================


def test_haversine_same_point():
    """Distance between same point is 0."""
    dist = haversine_distance(28.6139, 77.2090, 28.6139, 77.2090)
    assert dist < 0.001


def test_haversine_known_distance():
    """Test known distance (Delhi center to Noida ~16km)."""
    delhi_lat, delhi_lon = 28.6139, 77.2090
    noida_lat, noida_lon = 28.5921, 77.0460

    dist = haversine_distance(delhi_lat, delhi_lon, noida_lat, noida_lon)
    # Actual distance: ~16 km
    assert 15 < dist < 17


# ==============================================================================
# Location Validation Tests
# ==============================================================================


def test_location_within_tolerance(evaluator, challenge_at_zone_center):
    """Worker location within tolerance → location_match = True."""
    now = datetime.now(timezone.utc)
    response = WorkerResponse(
        challenge_id=challenge_at_zone_center.challenge_id,
        worker_id=challenge_at_zone_center.worker_id,
        response_lat=28.6139,  # Zone centroid
        response_lon=77.2090,
        response_timestamp=now + timedelta(minutes=5),
        app_foreground=True,
    )

    result = evaluator.evaluate_response(challenge_at_zone_center, response)

    assert result.passed is True
    assert result.distance_km < 2.0
    assert result.recommendation == "approve"


def test_location_exactly_at_tolerance_boundary(
    evaluator, challenge_at_zone_center
):
    """Worker just inside tolerance boundary (1.99 km) → should pass."""
    now = datetime.now(timezone.utc)

    # Calculate point just inside 2 km tolerance
    # 1.99 km ≈ 0.0179 degrees latitude (slightly less)
    offset_lat = 0.0179
    response = WorkerResponse(
        challenge_id=challenge_at_zone_center.challenge_id,
        worker_id=challenge_at_zone_center.worker_id,
        response_lat=28.6139 + offset_lat,
        response_lon=77.2090,
        response_timestamp=now + timedelta(minutes=5),
        app_foreground=True,
    )

    result = evaluator.evaluate_response(challenge_at_zone_center, response)

    # Should be within tolerance
    assert result.distance_km < 2.0
    assert result.passed is True


def test_location_just_outside_tolerance_borderline(
    evaluator, challenge_at_zone_center
):
    """Location just outside tolerance (2.2 km) → borderline, manual review."""
    now = datetime.now(timezone.utc)

    # Calculate point ~2.2 km away
    offset_lat = 0.020
    response = WorkerResponse(
        challenge_id=challenge_at_zone_center.challenge_id,
        worker_id=challenge_at_zone_center.worker_id,
        response_lat=28.6139 + offset_lat,
        response_lon=77.2090,
        response_timestamp=now + timedelta(minutes=5),
        app_foreground=True,
    )

    result = evaluator.evaluate_response(challenge_at_zone_center, response)

    assert result.passed is False
    assert result.borderline is True
    assert result.recommendation == "manual_review"
    assert "just outside tolerance" in (result.failure_reason or "").lower()


def test_location_far_outside_tolerance_reject(
    evaluator, challenge_at_zone_center
):
    """Location far outside tolerance (5 km) → reject."""
    now = datetime.now(timezone.utc)

    # Calculate point ~5 km away
    offset_lat = 0.045
    response = WorkerResponse(
        challenge_id=challenge_at_zone_center.challenge_id,
        worker_id=challenge_at_zone_center.worker_id,
        response_lat=28.6139 + offset_lat,
        response_lon=77.2090,
        response_timestamp=now + timedelta(minutes=5),
        app_foreground=True,
    )

    result = evaluator.evaluate_response(challenge_at_zone_center, response)

    assert result.passed is False
    assert result.borderline is False
    assert result.recommendation == "reject"
    assert result.distance_km > 4.0


# ==============================================================================
# Timing Validation Tests
# ==============================================================================


def test_timing_responded_early_score_1_0(evaluator, challenge_at_zone_center):
    """Responded within 10 minutes → timing_score = 1.0."""
    now = datetime.now(timezone.utc)
    response = WorkerResponse(
        challenge_id=challenge_at_zone_center.challenge_id,
        worker_id=challenge_at_zone_center.worker_id,
        response_lat=28.6139,
        response_lon=77.2090,
        response_timestamp=challenge_at_zone_center.issued_at + timedelta(minutes=5),
        app_foreground=True,
    )

    result = evaluator.evaluate_response(challenge_at_zone_center, response)

    assert result.timing_score == 1.0
    assert result.passed is True


def test_timing_responded_mid_window_score_0_7(
    evaluator, challenge_at_zone_center
):
    """Responded at 15 minutes → timing_score = 0.7."""
    response = WorkerResponse(
        challenge_id=challenge_at_zone_center.challenge_id,
        worker_id=challenge_at_zone_center.worker_id,
        response_lat=28.6139,
        response_lon=77.2090,
        response_timestamp=challenge_at_zone_center.issued_at + timedelta(minutes=15),
        app_foreground=True,
    )

    result = evaluator.evaluate_response(challenge_at_zone_center, response)

    assert result.timing_score == 0.7
    assert result.passed is True  # Location OK + timing OK


def test_timing_responded_late_score_0_4(evaluator, challenge_at_zone_center):
    """Responded at 25 minutes → timing_score = 0.4."""
    response = WorkerResponse(
        challenge_id=challenge_at_zone_center.challenge_id,
        worker_id=challenge_at_zone_center.worker_id,
        response_lat=28.6139,
        response_lon=77.2090,
        response_timestamp=challenge_at_zone_center.issued_at + timedelta(minutes=25),
        app_foreground=True,
    )

    result = evaluator.evaluate_response(challenge_at_zone_center, response)

    assert result.timing_score == 0.4
    assert result.passed is True  # Still acceptable


def test_timing_responded_at_boundary_29_59_minutes(
    evaluator, challenge_at_zone_center
):
    """Responded at 29:59 (just before expiry) → should pass."""
    response = WorkerResponse(
        challenge_id=challenge_at_zone_center.challenge_id,
        worker_id=challenge_at_zone_center.worker_id,
        response_lat=28.6139,
        response_lon=77.2090,
        response_timestamp=challenge_at_zone_center.issued_at
        + timedelta(minutes=29, seconds=59),
        app_foreground=True,
    )

    result = evaluator.evaluate_response(challenge_at_zone_center, response)

    assert result.timing_score > 0.0
    assert result.passed is True


def test_timing_responded_after_expiry():
    """Responded after 30 minutes → timing_score = 0, fail."""
    now = datetime.now(timezone.utc)
    challenge = VerificationChallenge(
        challenge_id="test_challenge_expired",
        claim_id="claim_123",
        worker_id="worker_456",
        challenge_type="location_ping",
        issued_at=now - timedelta(minutes=31),  # Issued 31 min ago
        expires_at=now - timedelta(minutes=1),  # Expired 1 min ago
        expected_zone_id="DL-CENTRAL-01",
        expected_lat_range=(28.60, 28.65),
        expected_lon_range=(77.20, 77.25),
        location_tolerance_km=2.0,
        status="pending",
    )

    response = WorkerResponse(
        challenge_id=challenge.challenge_id,
        worker_id=challenge.worker_id,
        response_lat=28.6139,
        response_lon=77.2090,
        response_timestamp=now,  # Responding now (too late)
        app_foreground=True,
    )

    evaluator = ChallengeEvaluator()
    result = evaluator.evaluate_response(challenge, response)

    assert result.passed is False
    assert "expired" in (result.failure_reason or "").lower()


# ==============================================================================
# Combined Location + Timing Tests
# ==============================================================================


def test_good_location_good_timing_passes(evaluator, challenge_at_zone_center):
    """Good location + good timing → PASS."""
    response = WorkerResponse(
        challenge_id=challenge_at_zone_center.challenge_id,
        worker_id=challenge_at_zone_center.worker_id,
        response_lat=28.6139,
        response_lon=77.2090,
        response_timestamp=challenge_at_zone_center.issued_at + timedelta(minutes=8),
        app_foreground=True,
    )

    result = evaluator.evaluate_response(challenge_at_zone_center, response)

    assert result.passed is True
    assert result.recommendation == "approve"
    assert result.timing_score == 1.0


def test_bad_location_good_timing_fails(evaluator, challenge_at_zone_center):
    """Bad location + good timing → FAIL."""
    offset_lat = 0.045  # ~5 km away
    response = WorkerResponse(
        challenge_id=challenge_at_zone_center.challenge_id,
        worker_id=challenge_at_zone_center.worker_id,
        response_lat=28.6139 + offset_lat,
        response_lon=77.2090,
        response_timestamp=challenge_at_zone_center.issued_at + timedelta(minutes=5),
        app_foreground=True,
    )

    result = evaluator.evaluate_response(challenge_at_zone_center, response)

    assert result.passed is False
    assert result.recommendation == "reject"
    assert "location mismatch" in (result.failure_reason or "").lower()


def test_good_location_bad_timing_fails(evaluator, challenge_at_zone_center):
    """Good location + bad timing (after expiry) → FAIL."""
    response = WorkerResponse(
        challenge_id=challenge_at_zone_center.challenge_id,
        worker_id=challenge_at_zone_center.worker_id,
        response_lat=28.6139,
        response_lon=77.2090,
        response_timestamp=challenge_at_zone_center.expires_at
        + timedelta(minutes=1),  # 1 min after expiry
        app_foreground=True,
    )

    result = evaluator.evaluate_response(challenge_at_zone_center, response)

    assert result.passed is False


# ==============================================================================
# Challenge State Validation Tests
# ==============================================================================


def test_challenge_already_responded():
    """Challenge already responded → reject new response."""
    now = datetime.now(timezone.utc)
    challenge = VerificationChallenge(
        challenge_id="test_responded",
        claim_id="claim_123",
        worker_id="worker_456",
        challenge_type="location_ping",
        issued_at=now,
        expires_at=now + timedelta(minutes=30),
        expected_zone_id="DL-CENTRAL-01",
        expected_lat_range=(28.60, 28.65),
        expected_lon_range=(77.20, 77.25),
        location_tolerance_km=2.0,
        status="responded",  # Already responded
        response_data={"lat": 28.6139, "lon": 77.2090},
    )

    response = WorkerResponse(
        challenge_id=challenge.challenge_id,
        worker_id=challenge.worker_id,
        response_lat=28.6139,
        response_lon=77.2090,
        response_timestamp=now + timedelta(minutes=5),
        app_foreground=True,
    )

    evaluator = ChallengeEvaluator()
    result = evaluator.evaluate_response(challenge, response)

    assert result.passed is False
    assert "not pending" in (result.failure_reason or "").lower()


def test_worker_id_mismatch():
    """Worker ID doesn't match challenge → reject."""
    now = datetime.now(timezone.utc)
    challenge = VerificationChallenge(
        challenge_id="test_worker_mismatch",
        claim_id="claim_123",
        worker_id="worker_456",
        challenge_type="location_ping",
        issued_at=now,
        expires_at=now + timedelta(minutes=30),
        expected_zone_id="DL-CENTRAL-01",
        expected_lat_range=(28.60, 28.65),
        expected_lon_range=(77.20, 77.25),
        location_tolerance_km=2.0,
        status="pending",
    )

    response = WorkerResponse(
        challenge_id=challenge.challenge_id,
        worker_id="wrong_worker_789",  # Different worker
        response_lat=28.6139,
        response_lon=77.2090,
        response_timestamp=now + timedelta(minutes=5),
        app_foreground=True,
    )

    evaluator = ChallengeEvaluator()
    result = evaluator.evaluate_response(challenge, response)

    assert result.passed is False
    assert "mismatch" in (result.failure_reason or "").lower()
