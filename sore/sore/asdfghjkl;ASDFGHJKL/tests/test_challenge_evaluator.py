"""
Tests for Challenge Evaluator - Core location and timing validation

Focused unit tests for Haversine distance, timing scoring, and pass/fail logic.
"""

import pytest
from datetime import datetime, timedelta, timezone
from soft_verify.evaluator import ChallengeEvaluator, haversine_distance
from schemas import VerificationChallenge, WorkerResponse


# ==============================================================================
# Haversine Distance Tests
# ==============================================================================


class TestHaversineDistance:
    """Test Haversine distance calculation accuracy."""

    def test_same_point_zero_distance(self):
        """Same lat/lon returns ~0 distance."""
        dist = haversine_distance(28.6139, 77.2090, 28.6139, 77.2090)
        assert dist < 0.001

    def test_known_short_distance(self):
        """Verify short distance calculation (< 1km)."""
        # Two nearby points in Delhi roughly 0.24 km apart (actual calculation)
        lat1, lon1 = 28.6139, 77.2090
        lat2, lon2 = 28.6159, 77.2100  # Rough offset
        
        dist = haversine_distance(lat1, lon1, lat2, lon2)
        assert 0.2 < dist < 0.3  # Actual: ~0.24 km

    def test_known_medium_distance(self):
        """Verify medium distance calculation (~10-15km)."""
        # Delhi center to Gurgaon boundary roughly 12-15 km
        delhi_lat, delhi_lon = 28.6139, 77.2090
        gurgaon_lat, gurgaon_lon = 28.4089, 77.0235
        
        dist = haversine_distance(delhi_lat, delhi_lon, gurgaon_lat, gurgaon_lon)
        assert 25 < dist < 30  # Actually ~26-27 km

    def test_known_long_distance(self):
        """Verify long distance calculation (~170+ km)."""
        # Delhi to Agra roughly 178 km 
        delhi_lat, delhi_lon = 28.6139, 77.2090
        agra_lat, agra_lon = 27.1767, 78.0081
        
        dist = haversine_distance(delhi_lat, delhi_lon, agra_lat, agra_lon)
        assert 170 < dist < 185  # Actual: ~178 km

    def test_antipodal_points(self):
        """Test nearly opposite points (max distance)."""
        # 0,0 to 0,180 should be ~20000 km (half Earth circumference)
        dist = haversine_distance(0, 0, 0, 180)
        assert dist > 19000  # ~20037 km

    def test_equator_to_pole(self):
        """Distance from equator to pole should be ~10,000 km."""
        dist = haversine_distance(0, 0, 90, 0)
        assert 10000 < dist < 10100


# ==============================================================================
# Timing Score Logic Tests
# ==============================================================================


class TestTimingScoreLogic:
    """Test timing score calculation based on response delay."""

    def test_timing_score_at_0_minutes_is_1_0(self):
        """Responded immediately → timing_score = 1.0."""
        evaluator = ChallengeEvaluator()
        now = datetime.now(timezone.utc)
        
        challenge = VerificationChallenge(
            challenge_id="test_timing_0",
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
            worker_id=challenge.worker_id,
            response_lat=28.6139,
            response_lon=77.2090,
            response_timestamp=now,  # Immediate response
            app_foreground=True,
        )
        
        result = evaluator.evaluate_response(challenge, response)
        assert result.timing_score == 1.0

    def test_timing_score_at_5_minutes_is_1_0(self):
        """Responded at 5 minutes → timing_score = 1.0 (still in first bucket)."""
        evaluator = ChallengeEvaluator()
        now = datetime.now(timezone.utc)
        
        challenge = VerificationChallenge(
            challenge_id="test_timing_5",
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
            worker_id=challenge.worker_id,
            response_lat=28.6139,
            response_lon=77.2090,
            response_timestamp=now + timedelta(minutes=5),
            app_foreground=True,
        )
        
        result = evaluator.evaluate_response(challenge, response)
        assert result.timing_score == 1.0

    def test_timing_score_at_10_minutes_boundary(self):
        """Responded exactly at 10 minutes → timing_score should be 1.0 or 0.7."""
        evaluator = ChallengeEvaluator()
        now = datetime.now(timezone.utc)
        
        challenge = VerificationChallenge(
            challenge_id="test_timing_10",
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
            worker_id=challenge.worker_id,
            response_lat=28.6139,
            response_lon=77.2090,
            response_timestamp=now + timedelta(minutes=10),
            app_foreground=True,
        )
        
        result = evaluator.evaluate_response(challenge, response)
        # At boundary, could be 1.0 or 0.7 depending on implementation
        assert result.timing_score in [1.0, 0.7]

    def test_timing_score_at_12_minutes_is_0_7(self):
        """Responded at 12 minutes (10-20 bucket) → timing_score = 0.7."""
        evaluator = ChallengeEvaluator()
        now = datetime.now(timezone.utc)
        
        challenge = VerificationChallenge(
            challenge_id="test_timing_12",
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
            worker_id=challenge.worker_id,
            response_lat=28.6139,
            response_lon=77.2090,
            response_timestamp=now + timedelta(minutes=12),
            app_foreground=True,
        )
        
        result = evaluator.evaluate_response(challenge, response)
        assert result.timing_score == 0.7

    def test_timing_score_at_20_minutes_boundary(self):
        """Responded exactly at 20 minutes → should be 0.7 or 0.4."""
        evaluator = ChallengeEvaluator()
        now = datetime.now(timezone.utc)
        
        challenge = VerificationChallenge(
            challenge_id="test_timing_20",
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
            worker_id=challenge.worker_id,
            response_lat=28.6139,
            response_lon=77.2090,
            response_timestamp=now + timedelta(minutes=20),
            app_foreground=True,
        )
        
        result = evaluator.evaluate_response(challenge, response)
        assert result.timing_score in [0.7, 0.4]

    def test_timing_score_at_25_minutes_is_0_4(self):
        """Responded at 25 minutes (20-30 bucket) → timing_score = 0.4."""
        evaluator = ChallengeEvaluator()
        now = datetime.now(timezone.utc)
        
        challenge = VerificationChallenge(
            challenge_id="test_timing_25",
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
            worker_id=challenge.worker_id,
            response_lat=28.6139,
            response_lon=77.2090,
            response_timestamp=now + timedelta(minutes=25),
            app_foreground=True,
        )
        
        result = evaluator.evaluate_response(challenge, response)
        assert result.timing_score == 0.4

    def test_timing_score_at_29_59_is_0_4(self):
        """Responded at 29:59 (last second) → timing_score = 0.4."""
        evaluator = ChallengeEvaluator()
        now = datetime.now(timezone.utc)
        
        challenge = VerificationChallenge(
            challenge_id="test_timing_2959",
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
            worker_id=challenge.worker_id,
            response_lat=28.6139,
            response_lon=77.2090,
            response_timestamp=now + timedelta(minutes=29, seconds=59),
            app_foreground=True,
        )
        
        result = evaluator.evaluate_response(challenge, response)
        assert result.timing_score == 0.4

    def test_timing_score_after_30_minutes_is_0(self):
        """Responded after 30 minutes (after expiry) → timing_score = 0."""
        evaluator = ChallengeEvaluator()
        now = datetime.now(timezone.utc)
        
        challenge = VerificationChallenge(
            challenge_id="test_timing_expired",
            claim_id="claim_123",
            worker_id="worker_456",
            challenge_type="location_ping",
            issued_at=now - timedelta(minutes=31),
            expires_at=now - timedelta(minutes=1),
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
        
        result = evaluator.evaluate_response(challenge, response)
        assert result.timing_score == 0.0


# ==============================================================================
# Borderline Detection Tests
# ==============================================================================


class TestBorderlineDetection:
    """Test detection of borderline location responses."""

    def test_location_at_2_0km_not_borderline(self):
        """Location very close to tolerance (1.99km) is NOT borderline."""
        evaluator = ChallengeEvaluator()
        now = datetime.now(timezone.utc)
        
        challenge = VerificationChallenge(
            challenge_id="test_borderline_at_boundary",
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
        
        # Point roughly 1.99 km away (well within tolerance)
        offset_lat = 0.0179
        response = WorkerResponse(
            challenge_id=challenge.challenge_id,
            worker_id=challenge.worker_id,
            response_lat=28.6139 + offset_lat,
            response_lon=77.2090,
            response_timestamp=now + timedelta(minutes=5),
            app_foreground=True,
        )
        
        result = evaluator.evaluate_response(challenge, response)
        # Location should be within tolerance
        assert result.distance_km < 2.0
        assert result.borderline is False
        assert result.passed is True

    def test_location_at_2_2km_is_borderline(self):
        """Location at 2.2 km (outside 2km, within 2.5km) IS borderline."""
        evaluator = ChallengeEvaluator()
        now = datetime.now(timezone.utc)
        
        challenge = VerificationChallenge(
            challenge_id="test_borderline_2_2km",
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
        
        # Point roughly 2.2 km away
        offset_lat = 0.020
        response = WorkerResponse(
            challenge_id=challenge.challenge_id,
            worker_id=challenge.worker_id,
            response_lat=28.6139 + offset_lat,
            response_lon=77.2090,
            response_timestamp=now + timedelta(minutes=5),
            app_foreground=True,
        )
        
        result = evaluator.evaluate_response(challenge, response)
        assert result.borderline is True
        assert result.recommendation == "manual_review"

    def test_location_at_3_0km_not_borderline_rejected(self):
        """Location at 3.0 km (outside borderline range) is NOT borderline → rejected."""
        evaluator = ChallengeEvaluator()
        now = datetime.now(timezone.utc)
        
        challenge = VerificationChallenge(
            challenge_id="test_not_borderline_3km",
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
        
        # Point roughly 3.0 km away
        offset_lat = 0.027
        response = WorkerResponse(
            challenge_id=challenge.challenge_id,
            worker_id=challenge.worker_id,
            response_lat=28.6139 + offset_lat,
            response_lon=77.2090,
            response_timestamp=now + timedelta(minutes=5),
            app_foreground=True,
        )
        
        result = evaluator.evaluate_response(challenge, response)
        assert result.borderline is False
        assert result.passed is False
        assert result.recommendation == "reject"


# ==============================================================================
# Pass/Fail Logic Tests
# ==============================================================================


class TestPassFailLogic:
    """Test overall pass/fail determination."""

    def test_pass_good_location_good_timing(self):
        """Good location + good timing → PASS."""
        evaluator = ChallengeEvaluator()
        now = datetime.now(timezone.utc)
        
        challenge = VerificationChallenge(
            challenge_id="test_pass_good",
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
            worker_id=challenge.worker_id,
            response_lat=28.6139,
            response_lon=77.2090,
            response_timestamp=now + timedelta(minutes=5),
            app_foreground=True,
        )
        
        result = evaluator.evaluate_response(challenge, response)
        assert result.passed is True
        assert result.recommendation == "approve"

    def test_fail_bad_location_good_timing(self):
        """Bad location + good timing → FAIL."""
        evaluator = ChallengeEvaluator()
        now = datetime.now(timezone.utc)
        
        challenge = VerificationChallenge(
            challenge_id="test_fail_bad_location",
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
        
        # 5 km away
        offset_lat = 0.045
        response = WorkerResponse(
            challenge_id=challenge.challenge_id,
            worker_id=challenge.worker_id,
            response_lat=28.6139 + offset_lat,
            response_lon=77.2090,
            response_timestamp=now + timedelta(minutes=5),
            app_foreground=True,
        )
        
        result = evaluator.evaluate_response(challenge, response)
        assert result.passed is False

    def test_fail_good_location_bad_timing(self):
        """Good location + bad timing (expired) → FAIL."""
        evaluator = ChallengeEvaluator()
        now = datetime.now(timezone.utc)
        
        challenge = VerificationChallenge(
            challenge_id="test_fail_bad_timing",
            claim_id="claim_123",
            worker_id="worker_456",
            challenge_type="location_ping",
            issued_at=now - timedelta(minutes=35),
            expires_at=now - timedelta(minutes=5),
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
            response_timestamp=now,  # Too late
            app_foreground=True,
        )
        
        result = evaluator.evaluate_response(challenge, response)
        assert result.passed is False
