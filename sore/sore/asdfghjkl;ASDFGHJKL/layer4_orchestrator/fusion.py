"""
Score Fusion

Fuses ML model scores and parametric trigger into a composite claim score.
Implements fallback logic for timeouts and explainability merging.
"""

from datetime import datetime, timezone
from typing import Any, Optional, Literal

import structlog

from schemas import (
    LSTMScore,
    IsolationForestScore,
    GBMScore,
    ParametricTriggerResult,
    CompositeClaimScore,
)

logger = structlog.get_logger()


class ScoreFuser:
    """Fuses all model scores into composite claim score."""

    def __init__(self, model_versions: Optional[dict[str, str]] = None):
        """
        Initialize fuser.

        Args:
            model_versions: Dict mapping model names to version strings
        """
        self.model_versions = model_versions or {
            "lstm": "v2.1.0",
            "isolation_forest": "v1.5.0",
            "gbm": "v3.0.1",
            "parametric_trigger": "v1.0.0",
        }

    def fuse(
        self,
        worker_id: str,
        minute_bucket: int,
        lstm_score: Optional[LSTMScore],
        if_score: Optional[IsolationForestScore],
        gbm_score: Optional[GBMScore],
        trigger_result: Optional[ParametricTriggerResult],
        feature_vector: Optional[dict[str, Any]] = None,
    ) -> CompositeClaimScore:
        """
        Fuse scores into composite claim score.

        Args:
            worker_id: Worker identifier
            minute_bucket: Minute bucket epoch
            lstm_score: LSTM model output (POW confidence)
            if_score: Isolation Forest anomaly score
            gbm_score: GBM fraud probability
            trigger_result: Parametric trigger result
            feature_vector: Feature vector for fallback heuristics

        Returns:
            CompositeClaimScore fused result
        """
        start_time = datetime.now(timezone.utc)
        feature_vector = feature_vector or {}

        # =====================================================================
        # 1. Disruption Score
        # =====================================================================
        disruption_score = (
            trigger_result.severity_score if trigger_result and trigger_result.triggered else 0.0
        )
        trigger_types_active = (
            trigger_result.trigger_types_active if trigger_result else []
        )

        # =====================================================================
        # 2. POW Confidence (LSTM)
        # =====================================================================
        if lstm_score and lstm_score.pow_confidence >= 0:
            pow_confidence = lstm_score.pow_confidence
        else:
            # Fallback: rule-based heuristic from features
            pow_confidence = self._compute_fallback_pow_confidence(feature_vector)
            logger.warning(
                "lstm_timeout_fallback",
                worker_id=worker_id,
                fallback_pow_confidence=pow_confidence,
            )

        # =====================================================================
        # 3. Fraud Probability (GBM)
        # =====================================================================
        fraud_probability = 0.5  # Default neutral

        if gbm_score and gbm_score.fraud_probability >= 0:
            fraud_probability = gbm_score.fraud_probability
        elif if_score and if_score.fraud_risk_score >= 0:
            # Fallback: use IF score as proxy
            fraud_probability = if_score.fraud_risk_score
            logger.warning(
                "gbm_timeout_fallback_to_if",
                worker_id=worker_id,
                fraud_probability=fraud_probability,
            )
        else:
            # Fallback: use loss plausibility as conservative estimate
            loss_plausibility = feature_vector.get("loss_plausibility_score", 0.5)
            fraud_probability = 1.0 - loss_plausibility
            logger.warning(
                "gbm_if_timeout_fallback_conservative",
                worker_id=worker_id,
                fraud_probability=fraud_probability,
            )

        # Keep fraud_risk_score_if for reference
        fraud_risk_score_if = (
            if_score.fraud_risk_score if if_score and if_score.fraud_risk_score >= 0 else 0.5
        )

        # =====================================================================
        # 4. Composite Claim Score
        # =====================================================================
        composite_claim_score = (
            disruption_score * pow_confidence * (1.0 - fraud_probability)
        )
        composite_claim_score = max(0.0, min(1.0, composite_claim_score))  # Clip [0, 1]

        # =====================================================================
        # 5. Anti-Spoofing Flag
        # =====================================================================
        anti_spoofing_flag = False
        if if_score and if_score.is_anomaly:
            anti_spoofing_flag = True
        if gbm_score and gbm_score.is_fraud_predicted:
            anti_spoofing_flag = True

        # =====================================================================
        # 6. Confidence Level
        # =====================================================================
        overall_feature_quality = feature_vector.get("overall_feature_quality", 0.0)
        scores_available = sum(
            [
                1 if lstm_score and lstm_score.pow_confidence >= 0 else 0,
                1 if if_score and if_score.fraud_risk_score >= 0 else 0,
                1 if gbm_score and gbm_score.fraud_probability >= 0 else 0,
            ]
        )

        confidence_level = self._compute_confidence_level(
            scores_available, overall_feature_quality, trigger_result
        )

        # =====================================================================
        # 7. Score Components (Audit Trail)
        # =====================================================================
        score_components = {
            "disruption_score": disruption_score,
            "pow_confidence": pow_confidence,
            "power_confidence_fallback": lstm_score is None or lstm_score.pow_confidence < 0,
            "fraud_probability": fraud_probability,
            "fraud_probability_fallback": (
                (gbm_score is None or gbm_score.fraud_probability < 0)
                and (if_score is None or if_score.fraud_risk_score < 0)
            ),
            "fraud_risk_score_if": fraud_risk_score_if,
            "overall_feature_quality": overall_feature_quality,
            "scores_available": scores_available,
            "trigger_fired": trigger_result.triggered if trigger_result else False,
            "anti_spoofing_flag": anti_spoofing_flag,
        }

        # =====================================================================
        # 8. Top Risk Signals (Merged Explainability)
        # =====================================================================
        top_risk_signals = self._merge_risk_signals(
            lstm_score, if_score, gbm_score
        )

        # =====================================================================
        # 9. Latency Measurement
        # =====================================================================
        fusion_latency_ms = (
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )

        # =====================================================================
        # Build Result
        # =====================================================================
        return CompositeClaimScore(
            worker_id=worker_id,
            minute_bucket=minute_bucket,
            composite_claim_score=composite_claim_score,
            disruption_score=disruption_score,
            pow_confidence=pow_confidence,
            fraud_probability=fraud_probability,
            fraud_risk_score_if=fraud_risk_score_if,
            anti_spoofing_flag=anti_spoofing_flag,
            confidence_level=confidence_level,
            score_components=score_components,
            top_risk_signals=top_risk_signals,
            trigger_types_active=trigger_types_active,
            model_versions=self.model_versions,
            fusion_latency_ms=fusion_latency_ms,
        )

    @staticmethod
    def _compute_fallback_pow_confidence(feature_vector: dict[str, Any]) -> float:
        """
        Compute POW confidence fallback when LSTM times out.

        Heuristic formula:
        fallback = 0.5 * motion_continuity_score
                 + 0.3 * road_match_score
                 + 0.2 * app_foreground_ratio
        """
        motion_continuity = feature_vector.get("motion_continuity_score", 0.5)
        road_match = feature_vector.get("road_match_score", 0.5)
        app_foreground = feature_vector.get("app_foreground_ratio", 0.5)

        fallback = (
            0.5 * motion_continuity + 0.3 * road_match + 0.2 * app_foreground
        )
        return max(0.0, min(1.0, fallback))

    @staticmethod
    def _compute_confidence_level(
        scores_available: int,
        overall_feature_quality: float,
        trigger_result: Optional[ParametricTriggerResult],
    ) -> Literal["high", "medium", "low", "insufficient"]:
        """
        Compute confidence level based on score availability and data quality.

        Rules:
        - high: all 3 scores + quality > 0.7
        - medium: 2/3 scores OR quality 0.4-0.7
        - low: 1/3 scores OR quality < 0.4
        - insufficient: 0/3 scores OR no trigger
        """
        if trigger_result is None or not trigger_result.triggered:
            return "insufficient"

        if scores_available >= 3 and overall_feature_quality > 0.7:
            return "high"
        elif scores_available >= 2 or (0.4 <= overall_feature_quality <= 0.7):
            return "medium"
        elif scores_available >= 1 or overall_feature_quality < 0.4:
            return "low"
        else:
            return "insufficient"

    @staticmethod
    def _merge_risk_signals(
        lstm_score: Optional[LSTMScore],
        if_score: Optional[IsolationForestScore],
        gbm_score: Optional[GBMScore],
    ) -> list[dict]:
        """
        Merge top risk signals from all 3 models into unified list.

        Returns:
            List of dicts: [{"source": "lstm", "signal": "...", "intensity": 0.8}, ...]
        """
        signals = []

        # LSTM suspicious timesteps
        if lstm_score and lstm_score.top_suspicious_timesteps:
            for ts_info in lstm_score.top_suspicious_timesteps[:3]:  # Top 3
                signals.append(
                    {
                        "source": "lstm",
                        "signal": f"suspicious_minute_{ts_info.get('minute', '?')}",
                        "intensity": ts_info.get("score", 0.5),
                    }
                )

        # IF anomalous features
        if if_score and if_score.top_anomalous_features:
            for feat_info in if_score.top_anomalous_features[:3]:  # Top 3
                signals.append(
                    {
                        "source": "isolation_forest",
                        "signal": f"anomaly_{feat_info.get('feature', 'unknown')}",
                        "intensity": feat_info.get("anomaly_score", 0.5),
                    }
                )

        # GBM fraud signals
        if gbm_score and gbm_score.top_fraud_signals:
            for fraud_info in gbm_score.top_fraud_signals[:3]:  # Top 3
                signals.append(
                    {
                        "source": "gbm",
                        "signal": fraud_info.get("signal", "unknown_fraud_signal"),
                        "intensity": fraud_info.get("importance", 0.3),
                    }
                )

        # Sort by intensity, return top 15
        signals.sort(key=lambda x: x["intensity"], reverse=True)
        return signals[:15]
