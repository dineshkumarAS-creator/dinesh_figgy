"""
Claim Router

Routes composite claim scores to Layer 5 with decisions:
- auto_payout: High confidence genuine disruption
- soft_verify: Medium risk or insufficient data
- manual_flag: Fraud risk or spoofing detected
"""

from typing import Literal, Optional

import structlog

from schemas import CompositeClaimScore, RoutingDecision

logger = structlog.get_logger()


class ClaimRouter:
    """Routes claims based on composite score and thresholds."""

    def __init__(
        self,
        low_risk_threshold: float = 0.65,
        high_risk_threshold: float = 0.30,
    ):
        """
        Initialize router with thresholds.

        Args:
            low_risk_threshold: Score >= this → auto_payout (if high confidence)
            high_risk_threshold: Score < this → manual_flag (fraud risk)
        """
        self.low_risk_threshold = low_risk_threshold
        self.high_risk_threshold = high_risk_threshold

        # Metrics
        self.total_decisions = 0
        self.decision_breakdown = {
            "auto_payout": 0,
            "soft_verify": 0,
            "manual_flag": 0,
        }

    def route(self, composite_score: CompositeClaimScore) -> RoutingDecision:
        """
        Route claim to Layer 5.

        Routing rules:
        1. If anti_spoofing_flag=True → manual_flag (override)
        2. If confidence_level="insufficient" → soft_verify
        3. If composite_score >= LOW_RISK_THRESHOLD AND confidence in ["high","medium"]
           → auto_payout
        4. If composite_score < HIGH_RISK_THRESHOLD → manual_flag
        5. Else → soft_verify (medium risk)

        Args:
            composite_score: CompositeClaimScore to route

        Returns:
            RoutingDecision with route, reason, and metadata
        """
        self.total_decisions += 1

        # Rule 1: Anti-spoofing override
        if composite_score.anti_spoofing_flag:
            route = "manual_flag"
            routing_reason = "spoofing_detected"
            logger.warning(
                "spoofing_flagged",
                worker_id=composite_score.worker_id,
                minute_bucket=composite_score.minute_bucket,
            )
            self.decision_breakdown["manual_flag"] += 1
            return RoutingDecision(
                worker_id=composite_score.worker_id,
                minute_bucket=composite_score.minute_bucket,
                route=route,
                routing_reason=routing_reason,
                composite_claim_score=composite_score.composite_claim_score,
                confidence_level=composite_score.confidence_level,
                requires_live_check=True,
            )

        # Rule 2: Insufficient confidence
        if composite_score.confidence_level == "insufficient":
            route = "soft_verify"
            routing_reason = "insufficient_data"
            logger.info(
                "insufficient_confidence",
                worker_id=composite_score.worker_id,
                minute_bucket=composite_score.minute_bucket,
            )
            self.decision_breakdown["soft_verify"] += 1
            return RoutingDecision(
                worker_id=composite_score.worker_id,
                minute_bucket=composite_score.minute_bucket,
                route=route,
                routing_reason=routing_reason,
                composite_claim_score=composite_score.composite_claim_score,
                confidence_level=composite_score.confidence_level,
                requires_live_check=False,
            )

        # Rule 3: Auto-payout (high confidence genuine)
        if (
            composite_score.composite_claim_score >= self.low_risk_threshold
            and composite_score.confidence_level in ["high", "medium"]
        ):
            route = "auto_payout"
            routing_reason = "high_confidence_genuine"
            logger.info(
                "auto_payout_approved",
                worker_id=composite_score.worker_id,
                minute_bucket=composite_score.minute_bucket,
                composite_score=composite_score.composite_claim_score,
            )
            self.decision_breakdown["auto_payout"] += 1
            return RoutingDecision(
                worker_id=composite_score.worker_id,
                minute_bucket=composite_score.minute_bucket,
                route=route,
                routing_reason=routing_reason,
                composite_claim_score=composite_score.composite_claim_score,
                confidence_level=composite_score.confidence_level,
                requires_live_check=False,
            )

        # Rule 4: Fraud risk
        if composite_score.composite_claim_score < self.high_risk_threshold:
            route = "manual_flag"
            routing_reason = "high_fraud_risk"
            logger.warning(
                "fraud_risk_flagged",
                worker_id=composite_score.worker_id,
                minute_bucket=composite_score.minute_bucket,
                composite_score=composite_score.composite_claim_score,
            )
            self.decision_breakdown["manual_flag"] += 1
            return RoutingDecision(
                worker_id=composite_score.worker_id,
                minute_bucket=composite_score.minute_bucket,
                route=route,
                routing_reason=routing_reason,
                composite_claim_score=composite_score.composite_claim_score,
                confidence_level=composite_score.confidence_level,
                requires_live_check=True,
            )

        # Rule 5: Default to soft-verify (medium risk)
        route = "soft_verify"
        routing_reason = "medium_risk"
        logger.info(
            "soft_verify_medium_risk",
            worker_id=composite_score.worker_id,
            minute_bucket=composite_score.minute_bucket,
            composite_score=composite_score.composite_claim_score,
        )
        self.decision_breakdown["soft_verify"] += 1
        return RoutingDecision(
            worker_id=composite_score.worker_id,
            minute_bucket=composite_score.minute_bucket,
            route=route,
            routing_reason=routing_reason,
            composite_claim_score=composite_score.composite_claim_score,
            confidence_level=composite_score.confidence_level,
            requires_live_check=False,
        )

    def get_metrics(self) -> dict:
        """Return routing statistics."""
        auto_payout_rate = (
            (self.decision_breakdown["auto_payout"] / self.total_decisions * 100)
            if self.total_decisions > 0
            else 0
        )
        return {
            "total_decisions": self.total_decisions,
            "auto_payout_count": self.decision_breakdown["auto_payout"],
            "soft_verify_count": self.decision_breakdown["soft_verify"],
            "manual_flag_count": self.decision_breakdown["manual_flag"],
            "auto_payout_rate_percent": auto_payout_rate,
        }
