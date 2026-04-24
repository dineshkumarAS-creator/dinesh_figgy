"""
Tests for Claim Router

Tests routing logic, thresholds, and decision paths.
"""

import pytest
from datetime import datetime, timezone

from layer4_orchestrator.router import ClaimRouter
from schemas import CompositeClaimScore, RoutingDecision


@pytest.fixture
def router():
    """Claim router instance with default thresholds."""
    return ClaimRouter(
        low_risk_threshold=0.65,
        high_risk_threshold=0.30,
    )


# ==============================================================================
# Auto-Payout Routing Tests
# ==============================================================================


def test_auto_payout_high_score_high_confidence(router):
    """Score >= 0.65 AND confidence='high' → auto_payout."""
    score = CompositeClaimScore(
        worker_id="worker_1",
        minute_bucket=1,
        composite_claim_score=0.78,
        disruption_score=0.9,
        pow_confidence=0.92,
        fraud_probability=0.15,
        fraud_risk_score_if=0.12,
        anti_spoofing_flag=False,
        confidence_level="high",
        trigger_types_active=["curfew"],
    )

    decision = router.route(score)

    assert decision.route == "auto_payout"
    assert decision.routing_reason == "high_confidence_genuine"
    assert decision.requires_live_check is False


def test_auto_payout_threshold_boundary(router):
    """Score exactly at threshold with high confidence → auto_payout."""
    score = CompositeClaimScore(
        worker_id="worker_1",
        minute_bucket=1,
        composite_claim_score=0.65,  # Exactly at threshold
        disruption_score=0.9,
        pow_confidence=0.8,
        fraud_probability=0.2,
        fraud_risk_score_if=0.2,
        anti_spoofing_flag=False,
        confidence_level="high",
        trigger_types_active=["curfew"],
    )

    decision = router.route(score)

    assert decision.route == "auto_payout"


def test_auto_payout_medium_confidence_high_score(router):
    """Score >= 0.65 AND confidence='medium' → auto_payout."""
    score = CompositeClaimScore(
        worker_id="worker_1",
        minute_bucket=1,
        composite_claim_score=0.72,
        disruption_score=0.8,
        pow_confidence=0.9,
        fraud_probability=0.1,
        fraud_risk_score_if=0.1,
        anti_spoofing_flag=False,
        confidence_level="medium",  # Medium OK
        trigger_types_active=["curfew"],
    )

    decision = router.route(score)

    assert decision.route == "auto_payout"


# ==============================================================================
# Manual Flag Routing Tests
# ==============================================================================


def test_manual_flag_high_fraud_risk(router):
    """Score < 0.30 → manual_flag (high fraud risk)."""
    score = CompositeClaimScore(
        worker_id="worker_1",
        minute_bucket=1,
        composite_claim_score=0.20,  # Below high_risk_threshold
        disruption_score=0.9,
        pow_confidence=0.5,
        fraud_probability=0.8,
        fraud_risk_score_if=0.75,
        anti_spoofing_flag=False,
        confidence_level="medium",
        trigger_types_active=["protest"],
    )

    decision = router.route(score)

    assert decision.route == "manual_flag"
    assert decision.routing_reason == "high_fraud_risk"
    assert decision.requires_live_check is True


def test_manual_flag_fraud_risk_threshold_boundary(router):
    """Score just below threshold → manual_flag."""
    score = CompositeClaimScore(
        worker_id="worker_1",
        minute_bucket=1,
        composite_claim_score=0.299,  # Just below 0.30
        disruption_score=0.9,
        pow_confidence=0.5,
        fraud_probability=0.8,
        fraud_risk_score_if=0.75,
        anti_spoofing_flag=False,
        confidence_level="medium",
        trigger_types_active=["strike"],
    )

    decision = router.route(score)

    assert decision.route == "manual_flag"
    assert decision.routing_reason == "high_fraud_risk"


def test_manual_flag_spoofing_override(router):
    """Anti-spoofing flag=True → manual_flag (override all other rules)."""
    # Even though score is high and confidence is high
    score = CompositeClaimScore(
        worker_id="worker_1",
        minute_bucket=1,
        composite_claim_score=0.95,  # Very high score
        disruption_score=0.99,
        pow_confidence=0.99,
        fraud_probability=0.01,
        fraud_risk_score_if=0.01,
        anti_spoofing_flag=True,  # SPOOFING DETECTED - override
        confidence_level="high",
        trigger_types_active=["curfew"],
    )

    decision = router.route(score)

    assert decision.route == "manual_flag"
    assert decision.routing_reason == "spoofing_detected"
    assert decision.requires_live_check is True


# ==============================================================================
# Soft Verify Routing Tests
# ==============================================================================


def test_soft_verify_insufficient_confidence(router):
    """Confidence='insufficient' → soft_verify (regardless of score)."""
    score = CompositeClaimScore(
        worker_id="worker_1",
        minute_bucket=1,
        composite_claim_score=0.50,
        disruption_score=0.7,
        pow_confidence=0.5,
        fraud_probability=0.5,
        fraud_risk_score_if=0.5,
        anti_spoofing_flag=False,
        confidence_level="insufficient",  # No confidence
        trigger_types_active=[],
    )

    decision = router.route(score)

    assert decision.route == "soft_verify"
    assert decision.routing_reason == "insufficient_data"
    assert decision.requires_live_check is False


def test_soft_verify_medium_risk(router):
    """Score in medium range (0.30-0.65) with medium confidence → soft_verify."""
    score = CompositeClaimScore(
        worker_id="worker_1",
        minute_bucket=1,
        composite_claim_score=0.45,  # In medium range
        disruption_score=0.8,
        pow_confidence=0.7,
        fraud_probability=0.35,
        fraud_risk_score_if=0.3,
        anti_spoofing_flag=False,
        confidence_level="medium",
        trigger_types_active=["bandh"],
    )

    decision = router.route(score)

    assert decision.route == "soft_verify"
    assert decision.routing_reason == "medium_risk"


def test_soft_verify_high_score_low_confidence(router):
    """Even high score with low confidence → soft_verify."""
    score = CompositeClaimScore(
        worker_id="worker_1",
        minute_bucket=1,
        composite_claim_score=0.70,  # High score
        disruption_score=0.9,
        pow_confidence=0.6,
        fraud_probability=0.2,
        fraud_risk_score_if=0.2,
        anti_spoofing_flag=False,
        confidence_level="low",  # But low confidence
        trigger_types_active=["curfew"],
    )

    decision = router.route(score)

    assert decision.route == "soft_verify"
    # High score but low confidence prevents auto_payout


# ==============================================================================
# Routing Metrics Tests
# ==============================================================================


def test_router_tracks_metrics(router):
    """Router tracks decision counts."""
    scores = [
        CompositeClaimScore(
            worker_id=f"worker_{i}", minute_bucket=i,
            composite_claim_score=0.8, disruption_score=0.9, pow_confidence=0.9,
            fraud_probability=0.1, fraud_risk_score_if=0.1,
            anti_spoofing_flag=False, confidence_level="high",
            trigger_types_active=["curfew"]
        )
        for i in range(3)  # 3 auto-payouts
    ]

    for score in scores:
        router.route(score)

    # Add some manual flags
    for i in range(2):
        fraud_score = CompositeClaimScore(
            worker_id=f"fraud_{i}", minute_bucket=100 + i,
            composite_claim_score=0.15, disruption_score=0.9, pow_confidence=0.5,
            fraud_probability=0.85, fraud_risk_score_if=0.8,
            anti_spoofing_flag=False, confidence_level="medium",
            trigger_types_active=["protest"]
        )
        router.route(fraud_score)

    metrics = router.get_metrics()

    assert metrics["total_decisions"] == 5
    assert metrics["auto_payout_count"] == 3
    assert metrics["manual_flag_count"] == 2
    assert abs(metrics["auto_payout_rate_percent"] - 60.0) < 0.1


def test_auto_payout_rate_calculation(router):
    """Auto-payout rate correctly calculated."""
    # 4 auto-payouts, 1 manual flag = 80%
    for i in range(4):
        score = CompositeClaimScore(
            worker_id=f"worker_{i}", minute_bucket=i,
            composite_claim_score=0.75, disruption_score=0.9, pow_confidence=0.85,
            fraud_probability=0.15, fraud_risk_score_if=0.1,
            anti_spoofing_flag=False, confidence_level="high",
            trigger_types_active=["curfew"]
        )
        router.route(score)

    fraud_score = CompositeClaimScore(
        worker_id="fraud_1", minute_bucket=100,
        composite_claim_score=0.1, disruption_score=0.8, pow_confidence=0.4,
        fraud_probability=0.95, fraud_risk_score_if=0.9,
        anti_spoofing_flag=False, confidence_level="low",
        trigger_types_active=[]
    )
    router.route(fraud_score)

    metrics = router.get_metrics()
    assert metrics["total_decisions"] == 5
    assert abs(metrics["auto_payout_rate_percent"] - 80.0) < 0.1


# ==============================================================================
# Confidence Level Boundary Tests
# ==============================================================================


def test_auto_payout_not_triggered_by_low_confidence(router):
    """Low confidence score doesn't trigger auto_payout even if score is high."""
    score = CompositeClaimScore(
        worker_id="worker_1",
        minute_bucket=1,
        composite_claim_score=0.90,  # Excellent score
        disruption_score=0.95,
        pow_confidence=0.95,
        fraud_probability=0.05,
        fraud_risk_score_if=0.05,
        anti_spoofing_flag=False,
        confidence_level="low",  # But low confidence
        trigger_types_active=["curfew"],
    )

    decision = router.route(score)

    assert decision.route == "soft_verify"  # Not auto_payout


# ==============================================================================
# Decision Reason Validation
# ==============================================================================


def test_decision_reasons_are_set(router):
    """All routing decisions have proper reason strings."""
    test_cases = [
        (
            CompositeClaimScore(
                worker_id="w1", minute_bucket=1,
                composite_claim_score=0.8, disruption_score=0.9, pow_confidence=0.9,
                fraud_probability=0.1, fraud_risk_score_if=0.1,
                anti_spoofing_flag=False, confidence_level="high",
                trigger_types_active=["curfew"]
            ),
            "high_confidence_genuine",
        ),
        (
            CompositeClaimScore(
                worker_id="w2", minute_bucket=1,
                composite_claim_score=0.2, disruption_score=0.8, pow_confidence=0.5,
                fraud_probability=0.8, fraud_risk_score_if=0.75,
                anti_spoofing_flag=False, confidence_level="medium",
                trigger_types_active=["strike"]
            ),
            "high_fraud_risk",
        ),
        (
            CompositeClaimScore(
                worker_id="w3", minute_bucket=1,
                composite_claim_score=0.8, disruption_score=0.9, pow_confidence=0.9,
                fraud_probability=0.1, fraud_risk_score_if=0.1,
                anti_spoofing_flag=True, confidence_level="high",
                trigger_types_active=["curfew"]
            ),
            "spoofing_detected",
        ),
    ]

    for score, expected_reason in test_cases:
        decision = router.route(score)
        assert decision.routing_reason == expected_reason
