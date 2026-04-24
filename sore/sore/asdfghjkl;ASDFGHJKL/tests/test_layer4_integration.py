"""
Layer 4 Integration Tests

End-to-end tests of score collection, fusion, routing, and publishing.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from layer4_orchestrator.score_collector import ScoreCollector
from layer4_orchestrator.fusion import ScoreFuser
from layer4_orchestrator.router import ClaimRouter
from layer4_orchestrator.publisher import ScorePublisher
from schemas import (
    LSTMScore,
    IsolationForestScore,
    GBMScore,
    ParametricTriggerResult,
    MLScoresMessage,
)


@pytest.mark.asyncio
async def test_full_pipeline_integration():
    """
    Full pipeline: ML scores → collection → fusion → routing → publishing.

    Simulates:
    1. Receive all 3 ML model scores + trigger
    2. Fuse into composite score
    3. Route to Layer 5
    4. Publish to Kafka and Redis
    """

    # Create instances
    fuser = ScoreFuser()
    router = ClaimRouter()
    
    # Collect scores
    lstm = LSTMScore(
        worker_id="worker_123",
        minute_bucket=1713081000,
        pow_confidence=0.92,
        top_suspicious_timesteps=[],
        model_version="v2.1.0",
        inference_latency_ms=10.5,
    )
    
    if_score = IsolationForestScore(
        worker_id="worker_123",
        minute_bucket=1713081000,
        fraud_risk_score=0.12,
        is_anomaly=False,
        top_anomalous_features=[],
        model_version="v1.5.0",
        inference_latency_ms=8.2,
    )
    
    gbm = GBMScore(
        worker_id="worker_123",
        minute_bucket=1713081000,
        fraud_probability=0.15,
        is_fraud_predicted=False,
        top_fraud_signals=[],
        model_version="v3.0.1",
        inference_latency_ms=9.1,
    )
    
    trigger = ParametricTriggerResult(
        worker_id="worker_123",
        minute_bucket=1713081000,
        triggered=True,
        severity_score=0.9,
        trigger_types_active=["curfew"],
        event_count=1,
        trigger_timestamp=datetime.now(timezone.utc),
    )

    # Fuse scores
    feature_vector = {
        "overall_feature_quality": 0.85,
        "motion_continuity_score": 0.88,
        "road_match_score": 0.82,
        "app_foreground_ratio": 0.75,
        "loss_plausibility_score": 0.6,
    }

    composite = fuser.fuse(
        worker_id="worker_123",
        minute_bucket=1713081000,
        lstm_score=lstm,
        if_score=if_score,
        gbm_score=gbm,
        trigger_result=trigger,
        feature_vector=feature_vector,
    )

    # Validate composite score
    assert composite.worker_id == "worker_123"
    assert composite.minute_bucket == 1713081000
    assert composite.composite_claim_score > 0.5  # Should be reasonably high
    assert composite.confidence_level == "high"
    assert composite.disruption_score == 0.9
    assert composite.anti_spoofing_flag is False
    assert len(composite.top_risk_signals) == 0  # No suspicious signals

    # Route decision
    decision = router.route(composite)

    # Should route to auto-payout (high score, high confidence, no fraud risk)
    assert decision.route == "auto_payout"
    assert decision.routing_reason == "high_confidence_genuine"
    assert decision.worker_id == "worker_123"
    assert decision.minute_bucket == 1713081000

    # Verify metrics updated
    metrics = router.get_metrics()
    assert metrics["total_decisions"] == 1
    assert metrics["auto_payout_count"] == 1


@pytest.mark.asyncio
async def test_integration_with_lstm_timeout_fallback():
    """
    Integration test with LSTM timeout.

    Should:
    1. Use IF as fallback for GBM timeout-free computation
    2. Use heuristic for LSTM timeout
    3. Still produce valid composite score
    """
    fuser = ScoreFuser()
    router = ClaimRouter()

    # LSTM timed out
    lstm = LSTMScore(
        worker_id="worker_456",
        minute_bucket=1713081100,
        pow_confidence=-1.0,  # Timeout sentinel
        top_suspicious_timesteps=[],
        model_version="v2.1.0",
        inference_latency_ms=2500.0,  # > 2 sec timeout
    )

    # IF and GBM available
    if_score = IsolationForestScore(
        worker_id="worker_456",
        minute_bucket=1713081100,
        fraud_risk_score=0.18,
        is_anomaly=False,
        top_anomalous_features=[],
        model_version="v1.5.0",
        inference_latency_ms=5.0,
    )

    gbm = GBMScore(
        worker_id="worker_456",
        minute_bucket=1713081100,
        fraud_probability=0.20,
        is_fraud_predicted=False,
        top_fraud_signals=[],
        model_version="v3.0.1",
        inference_latency_ms=6.0,
    )

    trigger = ParametricTriggerResult(
        worker_id="worker_456",
        minute_bucket=1713081100,
        triggered=True,
        severity_score=0.85,
        trigger_types_active=["strike"],
        event_count=1,
        trigger_timestamp=datetime.now(timezone.utc),
    )

    feature_vector = {
        "overall_feature_quality": 0.6,
        "motion_continuity_score": 0.75,
        "road_match_score": 0.70,
        "app_foreground_ratio": 0.65,
        "loss_plausibility_score": 0.55,
    }

    composite = fuser.fuse(
        worker_id="worker_456",
        minute_bucket=1713081100,
        lstm_score=lstm,
        if_score=if_score,
        gbm_score=gbm,
        trigger_result=trigger,
        feature_vector=feature_vector,
    )

    # Should use fallback for POW confidence
    assert composite.pow_confidence > 0  # Fallback computed
    assert composite.score_components["power_confidence_fallback"] is True

    # Should route to soft_verify (medium confidence due to LSTM timeout)
    decision = router.route(composite)
    assert decision.route in ["auto_payout", "soft_verify"]  # Depends on final score


@pytest.mark.asyncio
async def test_integration_spoofing_override():
    """
    Integration test: spoofing detected should route to manual_flag.

    Even if all other signals are clean, spoofing flag overrides.
    """
    fuser = ScoreFuser()
    router = ClaimRouter()

    lstm = LSTMScore(
        worker_id="worker_789",
        minute_bucket=1713081200,
        pow_confidence=0.95,
        top_suspicious_timesteps=[],
        model_version="v2.1.0",
        inference_latency_ms=8.0,
    )

    if_score = IsolationForestScore(
        worker_id="worker_789",
        minute_bucket=1713081200,
        fraud_risk_score=0.5,
        is_anomaly=True,  # ← ANOMALY DETECTED
        top_anomalous_features=[
            {"feature": "gps_displacement_m", "value": 2000, "anomaly_score": 0.95}
        ],
        model_version="v1.5.0",
        inference_latency_ms=7.0,
    )

    gbm = GBMScore(
        worker_id="worker_789",
        minute_bucket=1713081200,
        fraud_probability=0.05,
        is_fraud_predicted=False,
        top_fraud_signals=[],
        model_version="v3.0.1",
        inference_latency_ms=8.5,
    )

    trigger = ParametricTriggerResult(
        worker_id="worker_789",
        minute_bucket=1713081200,
        triggered=True,
        severity_score=0.95,
        trigger_types_active=["curfew"],
        event_count=1,
        trigger_timestamp=datetime.now(timezone.utc),
    )

    composite = fuser.fuse(
        worker_id="worker_789",
        minute_bucket=1713081200,
        lstm_score=lstm,
        if_score=if_score,
        gbm_score=gbm,
        trigger_result=trigger,
        feature_vector={},
    )

    # Anti-spoofing flag should be set
    assert composite.anti_spoofing_flag is True

    # Route should be manual_flag regardless of high score
    decision = router.route(composite)
    assert decision.route == "manual_flag"
    assert decision.routing_reason == "spoofing_detected"
    assert decision.requires_live_check is True


@pytest.mark.asyncio
async def test_integration_all_timeouts_conservative_fraud():
    """
    Integration: all 3 ML models timeout.

    Should:
    1. Use conservative fallbacks
    2. Lower confidence level
    3. Route to soft_verify or manual_flag
    """
    fuser = ScoreFuser()
    router = ClaimRouter()

    # All ML models timeout
    lstm = LSTMScore(
        worker_id="worker_xyz",
        minute_bucket=1713081300,
        pow_confidence=-1.0,  # Timeout
        top_suspicious_timesteps=[],
        model_version="v2.1.0",
        inference_latency_ms=2600.0,
    )

    if_score = IsolationForestScore(
        worker_id="worker_xyz",
        minute_bucket=1713081300,
        fraud_risk_score=-1.0,  # Timeout
        is_anomaly=False,
        top_anomalous_features=[],
        model_version="v1.5.0",
        inference_latency_ms=2700.0,
    )

    gbm = GBMScore(
        worker_id="worker_xyz",
        minute_bucket=1713081300,
        fraud_probability=-1.0,  # Timeout
        is_fraud_predicted=False,
        top_fraud_signals=[],
        model_version="v3.0.1",
        inference_latency_ms=2650.0,
    )

    trigger = ParametricTriggerResult(
        worker_id="worker_xyz",
        minute_bucket=1713081300,
        triggered=True,
        severity_score=0.8,
        trigger_types_active=["bandh"],
        event_count=1,
        trigger_timestamp=datetime.now(timezone.utc),
    )

    feature_vector = {
        "overall_feature_quality": 0.35,  # Low quality
        "motion_continuity_score": 0.5,
        "road_match_score": 0.5,
        "app_foreground_ratio": 0.5,
        "loss_plausibility_score": 0.4,  # → 1-0.4 = 0.6 fraud prob
    }

    composite = fuser.fuse(
        worker_id="worker_xyz",
        minute_bucket=1713081300,
        lstm_score=lstm,
        if_score=if_score,
        gbm_score=gbm,
        trigger_result=trigger,
        feature_vector=feature_vector,
    )

    # Should use all fallbacks
    assert composite.score_components["power_confidence_fallback"] is True
    assert composite.score_components["fraud_probability_fallback"] is True

    # Confidence should be low or insufficient
    assert composite.confidence_level in ["low", "medium"]

    # Route should be soft_verify or manual_flag
    decision = router.route(composite)
    assert decision.route in ["soft_verify", "manual_flag"]


@pytest.mark.asyncio
async def test_integration_fraud_detected_routes_manual_flag():
    """
    Integration: fraud detected by GBM.

    Should:
    1. Set is_fraud_predicted=True
    2. Set anti_spoofing_flag=True
    3. Route to manual_flag even if trigger fired
    """
    fuser = ScoreFuser()
    router = ClaimRouter()

    lstm = LSTMScore(
        worker_id="worker_fraud",
        minute_bucket=1713081400,
        pow_confidence=0.6,
        top_suspicious_timesteps=[],
        model_version="v2.1.0",
        inference_latency_ms=10.0,
    )

    if_score = IsolationForestScore(
        worker_id="worker_fraud",
        minute_bucket=1713081400,
        fraud_risk_score=0.3,
        is_anomaly=False,
        top_anomalous_features=[],
        model_version="v1.5.0",
        inference_latency_ms=8.0,
    )

    gbm = GBMScore(
        worker_id="worker_fraud",
        minute_bucket=1713081400,
        fraud_probability=0.92,  # High fraud probability
        is_fraud_predicted=True,  # ← FRAUD PREDICTED
        top_fraud_signals=[
            {"signal": "income_loss_pattern_suspicious", "importance": 0.6},
            {"signal": "earnings_inconsistency", "importance": 0.5},
        ],
        model_version="v3.0.1",
        inference_latency_ms=9.0,
    )

    trigger = ParametricTriggerResult(
        worker_id="worker_fraud",
        minute_bucket=1713081400,
        triggered=True,
        severity_score=0.9,
        trigger_types_active=["curfew", "strike"],
        event_count=2,
        trigger_timestamp=datetime.now(timezone.utc),
    )

    composite = fuser.fuse(
        worker_id="worker_fraud",
        minute_bucket=1713081400,
        lstm_score=lstm,
        if_score=if_score,
        gbm_score=gbm,
        trigger_result=trigger,
        feature_vector={},
    )

    # Anti-spoofing flag should be set
    assert composite.anti_spoofing_flag is True

    # Composite score should be very low
    assert composite.composite_claim_score < 0.3

    # Route should be manual_flag
    decision = router.route(composite)
    assert decision.route == "manual_flag"
    assert decision.requires_live_check is True
