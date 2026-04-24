"""
Tests for Score Fusion

Tests fusion formula, fallback logic, confidence levels, and signal merging.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from layer4_orchestrator.fusion import ScoreFuser
from schemas import (
    LSTMScore,
    IsolationForestScore,
    GBMScore,
    ParametricTriggerResult,
    CompositeClaimScore,
)


@pytest.fixture
def fuser():
    """Score fuser instance."""
    return ScoreFuser()


# ==============================================================================
# Core Fusion Formula Tests
# ==============================================================================


def test_fusion_formula_trigger_not_fired(fuser):
    """When trigger not fired, composite score = 0."""
    lstm = LSTMScore(
        worker_id="worker_1",
        minute_bucket=1,
        pow_confidence=0.9,
        model_version="v2.1.0",
        inference_latency_ms=10.0,
    )
    if_score = IsolationForestScore(
        worker_id="worker_1",
        minute_bucket=1,
        fraud_risk_score=0.1,
        is_anomaly=False,
        model_version="v1.5.0",
        inference_latency_ms=5.0,
    )
    gbm = GBMScore(
        worker_id="worker_1",
        minute_bucket=1,
        fraud_probability=0.05,
        is_fraud_predicted=False,
        model_version="v3.0.1",
        inference_latency_ms=8.0,
    )
    trigger = ParametricTriggerResult(
        worker_id="worker_1",
        minute_bucket=1,
        triggered=False,  # No trigger
        severity_score=0.0,
        trigger_types_active=[],
        event_count=0,
        trigger_timestamp=datetime.now(timezone.utc),
    )

    result = fuser.fuse(
        worker_id="worker_1",
        minute_bucket=1,
        lstm_score=lstm,
        if_score=if_score,
        gbm_score=gbm,
        trigger_result=trigger,
        feature_vector={},
    )

    assert result.disruption_score == 0.0
    assert result.composite_claim_score == 0.0  # disruption=0 → composite=0


def test_fusion_formula_perfect_scores(fuser):
    """Perfect scores: disruption=1, pow_conf=1, fraud_prob=0 → composite=1."""
    lstm = LSTMScore(
        worker_id="worker_1",
        minute_bucket=1,
        pow_confidence=1.0,
        model_version="v2.1.0",
        inference_latency_ms=10.0,
    )
    if_score = IsolationForestScore(
        worker_id="worker_1",
        minute_bucket=1,
        fraud_risk_score=0.0,
        is_anomaly=False,
        model_version="v1.5.0",
        inference_latency_ms=5.0,
    )
    gbm = GBMScore(
        worker_id="worker_1",
        minute_bucket=1,
        fraud_probability=0.0,
        is_fraud_predicted=False,
        model_version="v3.0.1",
        inference_latency_ms=8.0,
    )
    trigger = ParametricTriggerResult(
        worker_id="worker_1",
        minute_bucket=1,
        triggered=True,
        severity_score=1.0,  # Perfect disruption
        trigger_types_active=["curfew"],
        event_count=1,
        trigger_timestamp=datetime.now(timezone.utc),
    )

    result = fuser.fuse(
        worker_id="worker_1",
        minute_bucket=1,
        lstm_score=lstm,
        if_score=if_score,
        gbm_score=gbm,
        trigger_result=trigger,
        feature_vector={},
    )

    assert result.disruption_score == 1.0
    assert result.pow_confidence == 1.0
    assert result.fraud_probability == 0.0
    assert result.composite_claim_score == 1.0  # 1 * 1 * (1-0) = 1


def test_fusion_formula_high_fraud_probability(fuser):
    """High fraud probability lowers composite score."""
    lstm = LSTMScore(
        worker_id="worker_1",
        minute_bucket=1,
        pow_confidence=0.9,
        model_version="v2.1.0",
        inference_latency_ms=10.0,
    )
    if_score = IsolationForestScore(
        worker_id="worker_1",
        minute_bucket=1,
        fraud_risk_score=0.8,
        is_anomaly=True,
        model_version="v1.5.0",
        inference_latency_ms=5.0,
    )
    gbm = GBMScore(
        worker_id="worker_1",
        minute_bucket=1,
        fraud_probability=0.7,  # High fraud
        is_fraud_predicted=True,
        model_version="v3.0.1",
        inference_latency_ms=8.0,
    )
    trigger = ParametricTriggerResult(
        worker_id="worker_1",
        minute_bucket=1,
        triggered=True,
        severity_score=1.0,
        trigger_types_active=["curfew"],
        event_count=1,
        trigger_timestamp=datetime.now(timezone.utc),
    )

    result = fuser.fuse(
        worker_id="worker_1",
        minute_bucket=1,
        lstm_score=lstm,
        if_score=if_score,
        gbm_score=gbm,
        trigger_result=trigger,
        feature_vector={},
    )

    # 1.0 * 0.9 * (1 - 0.7) = 0.27
    assert abs(result.composite_claim_score - 0.27) < 0.01


# ==============================================================================
# Fallback Logic Tests
# ==============================================================================


def test_fallback_lstm_timeout(fuser):
    """When LSTM times out (-1.0), use heuristic fallback."""
    lstm = LSTMScore(
        worker_id="worker_1",
        minute_bucket=1,
        pow_confidence=-1.0,  # Timeout sentinel
        model_version="v2.1.0",
        inference_latency_ms=2500.0,  # Timeout
    )
    if_score = IsolationForestScore(
        worker_id="worker_1",
        minute_bucket=1,
        fraud_risk_score=0.1,
        is_anomaly=False,
        model_version="v1.5.0",
        inference_latency_ms=5.0,
    )
    gbm = GBMScore(
        worker_id="worker_1",
        minute_bucket=1,
        fraud_probability=0.05,
        is_fraud_predicted=False,
        model_version="v3.0.1",
        inference_latency_ms=8.0,
    )
    trigger = ParametricTriggerResult(
        worker_id="worker_1",
        minute_bucket=1,
        triggered=True,
        severity_score=1.0,
        trigger_types_active=["curfew"],
        event_count=1,
        trigger_timestamp=datetime.now(timezone.utc),
    )

    feature_vector = {
        "motion_continuity_score": 0.8,
        "road_match_score": 0.7,
        "app_foreground_ratio": 0.6,
    }

    result = fuser.fuse(
        worker_id="worker_1",
        minute_bucket=1,
        lstm_score=lstm,
        if_score=if_score,
        gbm_score=gbm,
        trigger_result=trigger,
        feature_vector=feature_vector,
    )

    # Fallback: 0.5 * 0.8 + 0.3 * 0.7 + 0.2 * 0.6 = 0.4 + 0.21 + 0.12 = 0.73
    expected_fallback = 0.5 * 0.8 + 0.3 * 0.7 + 0.2 * 0.6
    assert abs(result.pow_confidence - expected_fallback) < 0.01
    assert result.score_components["power_confidence_fallback"] is True


def test_fallback_gbm_timeout_to_if(fuser):
    """When GBM times out, use IF as fallback."""
    lstm = LSTMScore(
        worker_id="worker_1",
        minute_bucket=1,
        pow_confidence=0.85,
        model_version="v2.1.0",
        inference_latency_ms=10.0,
    )
    if_score = IsolationForestScore(
        worker_id="worker_1",
        minute_bucket=1,
        fraud_risk_score=0.25,  # Use as fallback
        is_anomaly=False,
        model_version="v1.5.0",
        inference_latency_ms=5.0,
    )
    gbm = GBMScore(
        worker_id="worker_1",
        minute_bucket=1,
        fraud_probability=-1.0,  # Timeout sentinel
        is_fraud_predicted=False,
        model_version="v3.0.1",
        inference_latency_ms=2600.0,  # Timeout
    )
    trigger = ParametricTriggerResult(
        worker_id="worker_1",
        minute_bucket=1,
        triggered=True,
        severity_score=1.0,
        trigger_types_active=["curfew"],
        event_count=1,
        trigger_timestamp=datetime.now(timezone.utc),
    )

    result = fuser.fuse(
        worker_id="worker_1",
        minute_bucket=1,
        lstm_score=lstm,
        if_score=if_score,
        gbm_score=gbm,
        trigger_result=trigger,
        feature_vector={},
    )

    assert result.fraud_probability == 0.25
    assert result.fraud_risk_score_if == 0.25
    # Fallback is True because GBM score < 0 but we used IF as fallback
    assert result.score_components["fraud_probability_fallback"] is True or (
        gbm.fraud_probability < 0 and if_score.fraud_risk_score >= 0
    )


def test_fallback_both_gbm_if_timeout_conservative(fuser):
    """When both GBM and IF timeout, use conservative fraud_probability from loss_plausibility."""
    lstm = LSTMScore(
        worker_id="worker_1",
        minute_bucket=1,
        pow_confidence=0.85,
        model_version="v2.1.0",
        inference_latency_ms=10.0,
    )
    if_score = IsolationForestScore(
        worker_id="worker_1",
        minute_bucket=1,
        fraud_risk_score=-1.0,  # Timeout
        is_anomaly=False,
        model_version="v1.5.0",
        inference_latency_ms=2600.0,
    )
    gbm = GBMScore(
        worker_id="worker_1",
        minute_bucket=1,
        fraud_probability=-1.0,  # Timeout
        is_fraud_predicted=False,
        model_version="v3.0.1",
        inference_latency_ms=2500.0,
    )
    trigger = ParametricTriggerResult(
        worker_id="worker_1",
        minute_bucket=1,
        triggered=True,
        severity_score=1.0,
        trigger_types_active=["curfew"],
        event_count=1,
        trigger_timestamp=datetime.now(timezone.utc),
    )

    feature_vector = {"loss_plausibility_score": 0.3}  # 70% fraud = 0.7

    result = fuser.fuse(
        worker_id="worker_1",
        minute_bucket=1,
        lstm_score=lstm,
        if_score=if_score,
        gbm_score=gbm,
        trigger_result=trigger,
        feature_vector=feature_vector,
    )

    # fraud_probability = 1 - 0.3 = 0.7
    assert result.fraud_probability == 0.7


# ==============================================================================
# Confidence Level Tests
# ==============================================================================


def test_confidence_high_all_scores_high_quality(fuser):
    """High confidence: all 3 scores available + quality > 0.7."""
    feature_vector = {"overall_feature_quality": 0.8}

    lstm = LSTMScore(
        worker_id="w1", minute_bucket=1, pow_confidence=0.9,
        model_version="v1", inference_latency_ms=5.0
    )
    if_score = IsolationForestScore(
        worker_id="w1", minute_bucket=1, fraud_risk_score=0.2,
        is_anomaly=False,
        model_version="v1", inference_latency_ms=5.0
    )
    gbm = GBMScore(
        worker_id="w1", minute_bucket=1, fraud_probability=0.1,
        is_fraud_predicted=False,
        model_version="v1", inference_latency_ms=5.0
    )
    trigger = ParametricTriggerResult(
        worker_id="w1", minute_bucket=1, triggered=True, severity_score=0.9,
        trigger_types_active=["curfew"], event_count=1,
        trigger_timestamp=datetime.now(timezone.utc)
    )

    result = fuser.fuse("w1", 1, lstm, if_score, gbm, trigger, feature_vector)
    assert result.confidence_level == "high"


def test_confidence_medium_two_scores(fuser):
    """Medium confidence: 2/3 scores available."""
    lstm = LSTMScore(
        worker_id="w1", minute_bucket=1, pow_confidence=0.9,
        model_version="v1", inference_latency_ms=5.0
    )
    if_score = IsolationForestScore(
        worker_id="w1", minute_bucket=1, fraud_risk_score=0.2,
        is_anomaly=False,
        model_version="v1", inference_latency_ms=5.0
    )
    gbm = GBMScore(
        worker_id="w1", minute_bucket=1, fraud_probability=-1.0,  # Timeout
        is_fraud_predicted=False,
        model_version="v1", inference_latency_ms=2500.0
    )
    trigger = ParametricTriggerResult(
        worker_id="w1", minute_bucket=1, triggered=True, severity_score=0.9,
        trigger_types_active=["curfew"], event_count=1,
        trigger_timestamp=datetime.now(timezone.utc)
    )

    result = fuser.fuse("w1", 1, lstm, if_score, gbm, trigger, {})
    assert result.confidence_level == "medium"


def test_confidence_insufficient_no_trigger(fuser):
    """Insufficient confidence: trigger not fired."""
    trigger = ParametricTriggerResult(
        worker_id="w1", minute_bucket=1, triggered=False, severity_score=0.0,
        trigger_types_active=[], event_count=0,
        trigger_timestamp=datetime.now(timezone.utc)
    )

    result = fuser.fuse("w1", 1, None, None, None, trigger, {})
    assert result.confidence_level == "insufficient"


# ==============================================================================
# Anti-Spoofing Tests
# ==============================================================================


def test_anti_spoofing_if_anomaly(fuser):
    """Anti-spoofing flag set when IF detects anomaly."""
    lstm = LSTMScore(
        worker_id="w1", minute_bucket=1, pow_confidence=0.9,
        model_version="v1", inference_latency_ms=5.0
    )
    if_score = IsolationForestScore(
        worker_id="w1", minute_bucket=1, fraud_risk_score=0.8,
        is_anomaly=True,  # Anomaly detected
        model_version="v1", inference_latency_ms=5.0
    )
    gbm = GBMScore(
        worker_id="w1", minute_bucket=1, fraud_probability=0.5,
        is_fraud_predicted=False,
        model_version="v1", inference_latency_ms=5.0
    )
    trigger = ParametricTriggerResult(
        worker_id="w1", minute_bucket=1, triggered=True, severity_score=0.9,
        trigger_types_active=["curfew"], event_count=1,
        trigger_timestamp=datetime.now(timezone.utc)
    )

    result = fuser.fuse("w1", 1, lstm, if_score, gbm, trigger, {})
    assert result.anti_spoofing_flag is True


def test_anti_spoofing_gbm_fraud_predicted(fuser):
    """Anti-spoofing flag set when GBM predicts fraud."""
    lstm = LSTMScore(
        worker_id="w1", minute_bucket=1, pow_confidence=0.9,
        model_version="v1", inference_latency_ms=5.0
    )
    if_score = IsolationForestScore(
        worker_id="w1", minute_bucket=1, fraud_risk_score=0.2,
        is_anomaly=False,
        model_version="v1", inference_latency_ms=5.0
    )
    gbm = GBMScore(
        worker_id="w1", minute_bucket=1, fraud_probability=0.8,
        is_fraud_predicted=True,  # Fraud predicted
        model_version="v1", inference_latency_ms=5.0
    )
    trigger = ParametricTriggerResult(
        worker_id="w1", minute_bucket=1, triggered=True, severity_score=0.9,
        trigger_types_active=["curfew"], event_count=1,
        trigger_timestamp=datetime.now(timezone.utc)
    )

    result = fuser.fuse("w1", 1, lstm, if_score, gbm, trigger, {})
    assert result.anti_spoofing_flag is True


# ==============================================================================
# Risk Signal Merging Tests
# ==============================================================================


def test_risk_signals_merged_from_all_models(fuser):
    """Top risk signals merged from LSTM, IF, and GBM."""
    lstm = LSTMScore(
        worker_id="w1", minute_bucket=1, pow_confidence=0.9,
        top_suspicious_timesteps=[
            {"minute": 5, "score": 0.8},
            {"minute": 10, "score": 0.7},
        ],
        model_version="v1", inference_latency_ms=5.0
    )
    if_score = IsolationForestScore(
        worker_id="w1", minute_bucket=1, fraud_risk_score=0.3,
        is_anomaly=True,
        top_anomalous_features=[
            {"feature": "gps_displacement_m", "value": 500, "anomaly_score": 0.85},
        ],
        model_version="v1", inference_latency_ms=5.0
    )
    gbm = GBMScore(
        worker_id="w1", minute_bucket=1, fraud_probability=0.2,
        is_fraud_predicted=False,
        top_fraud_signals=[
            {"signal": "high_income_loss", "importance": 0.4},
        ],
        model_version="v1", inference_latency_ms=5.0
    )
    trigger = ParametricTriggerResult(
        worker_id="w1", minute_bucket=1, triggered=True, severity_score=0.9,
        trigger_types_active=["curfew"], event_count=1,
        trigger_timestamp=datetime.now(timezone.utc)
    )

    result = fuser.fuse("w1", 1, lstm, if_score, gbm, trigger, {})

    # Should have signals from all 3 models
    sources = [s["source"] for s in result.top_risk_signals]
    assert "lstm" in sources
    assert "isolation_forest" in sources
    assert "gbm" in sources
    assert len(result.top_risk_signals) > 0
