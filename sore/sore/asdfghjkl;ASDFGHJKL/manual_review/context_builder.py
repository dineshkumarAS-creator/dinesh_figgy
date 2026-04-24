"""
Claim Context Builder - Assembles full review context for reviewers

Combines claim data, ML explanations, and generates human-readable summaries via Claude API.
"""

import json
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis
import structlog
from anthropic import Anthropic

from manual_review.schemas import (
    ReviewContext,
    FeatureVector,
    MLExplanations,
    RiskSignal,
    TrustProfile,
    CrowdValidationResult,
)

logger = structlog.get_logger()


class ClaimContextBuilder:
    """Builds complete review context for claims."""

    def __init__(
        self,
        redis_client: aioredis.Redis,
        anthropic_api_key: Optional[str] = None,
    ):
        """
        Initialize context builder.

        Args:
            redis_client: Redis async client for caching
            anthropic_api_key: Anthropic API key (can be None in artifact context)
        """
        self.redis = redis_client
        self.anthropic = Anthropic(api_key=anthropic_api_key) if anthropic_api_key else None

    async def build_review_context(
        self,
        claim_id: str,
        claim_data: dict,
        claim_history: list[dict],
        feature_snapshot: dict,
        risk_breakdown: dict,
        lstm_attention_weights: list[float],
        if_top_signals: list[dict],
        gbm_top_signals: list[dict],
        worker_id: str,
        worker_trust_data: dict,
        crowd_validation_result: dict,
        similar_past_claims: list[dict],
        zone_disruption_map: dict,
        queue_id: str,
        risk_score: float,
    ) -> ReviewContext:
        """
        Build complete review context.

        Args:
            claim_id: Claim UUID
            claim_data: Full claim record
            claim_history: State transition history
            feature_snapshot: Feature vector at time of claim
            risk_breakdown: Risk tier and scores from ML
            lstm_attention_weights: 30 timestep attention weights
            if_top_signals: Top isolation forest signals
            gbm_top_signals: Top GBM signals
            worker_id: Worker UUID
            worker_trust_data: Historical trust profile
            crowd_validation_result: Crowd validation data
            similar_past_claims: Last 5 claims from worker
            zone_disruption_map: % workers by city block
            queue_id: Review queue item ID
            risk_score: Combined risk score

        Returns:
            ReviewContext
        """
        # Check cache first
        cache_key = f"review_context:{claim_id}"
        cached_json = await self.redis.get(cache_key)
        if cached_json:
            logger.info("review_context_cache_hit", claim_id=claim_id)
            return ReviewContext(**json.loads(cached_json))

        # Parse features
        feature_vector = FeatureVector(
            motion_continuity=feature_snapshot.get("motion_continuity", 0.0),
            road_match_score=feature_snapshot.get("road_match_score", 0.0),
            app_foreground_duration_pct=feature_snapshot.get("app_foreground_duration_pct", 0.0),
            gps_accuracy_meters=feature_snapshot.get("gps_accuracy_meters", 50.0),
            speed_variance=feature_snapshot.get("speed_variance", 0.0),
            stop_detection=feature_snapshot.get("stop_detection", False),
            timestamp=datetime.now(timezone.utc),
        )

        # Parse risk signals
        if_signals = [
            RiskSignal(
                feature=s.get("feature", "unknown"),
                value=s.get("value", 0.0),
                shap_value=s.get("shap_value", 0.0),
                direction="positive" if s.get("shap_value", 0) > 0 else "negative",
                description=s.get("description", ""),
            )
            for s in if_top_signals[:5]  # Top 5
        ]

        gbm_signals = [
            RiskSignal(
                feature=s.get("feature", "unknown"),
                value=s.get("value", 0.0),
                shap_value=s.get("shap_value", 0.0),
                direction="positive" if s.get("shap_value", 0) > 0 else "negative",
                description=s.get("description", ""),
            )
            for s in gbm_top_signals[:5]  # Top 5
        ]

        # Generate human-readable summary via Claude
        human_summary = await self._generate_summary(
            if_signals=if_signals,
            gbm_signals=gbm_signals,
            claim_data=claim_data,
        )

        # ML explanations
        ml_explanations = MLExplanations(
            lstm_attention_weights=lstm_attention_weights[:30],
            if_top_signals=if_signals,
            gbm_top_signals=gbm_signals,
            human_readable_summary=human_summary,
        )

        # Worker trust profile
        worker_profile = TrustProfile(
            worker_id=worker_id,
            total_claims=worker_trust_data.get("total_claims", 0),
            approved_claims=worker_trust_data.get("approved_claims", 0),
            rejected_claims=worker_trust_data.get("rejected_claims", 0),
            approval_rate=worker_trust_data.get("approval_rate", 0.5),
            avg_claim_value_inr=worker_trust_data.get("avg_claim_value_inr", 0.0),
            is_new_worker=worker_trust_data.get("is_new_worker", True),
            flagged_reasons=worker_trust_data.get("flagged_reasons", []),
        )

        # Crowd validation
        crowd_result = CrowdValidationResult(
            crowd_size=crowd_validation_result.get("crowd_size", 0),
            validation_rate=crowd_validation_result.get("validation_rate", 0.0),
            consensus_confidence=crowd_validation_result.get("consensus_confidence", 0.0),
            crowd_spike_flag=crowd_validation_result.get("crowd_spike_flag", False),
        )

        # Recommendation based on risk tier and signals
        recommended_action = self._generate_recommendation(
            risk_score=risk_score,
            risk_breakdown=risk_breakdown,
            is_new_worker=worker_profile.is_new_worker,
            approval_rate=worker_profile.approval_rate,
            crowd_spike=crowd_result.crowd_spike_flag,
        )

        # Assemble full context
        context = ReviewContext(
            claim_id=claim_id,
            queue_id=queue_id,
            claim=claim_data,
            claim_history=claim_history,
            feature_snapshot=feature_vector,
            risk_breakdown=risk_breakdown,
            ml_explanations=ml_explanations,
            worker_trust_profile=worker_profile,
            crowd_validation=crowd_result,
            similar_past_claims=similar_past_claims,
            zone_disruption_map=zone_disruption_map,
            recommended_action=recommended_action,
            risk_score=risk_score,
        )

        # Cache for 10 minutes
        await self.redis.setex(
            cache_key,
            600,  # 10 minutes
            context.model_dump_json(),
        )

        logger.info(
            "review_context_built",
            claim_id=claim_id,
            queue_id=queue_id,
            risk_score=risk_score,
        )

        return context

    async def _generate_summary(
        self,
        if_signals: list[RiskSignal],
        gbm_signals: list[RiskSignal],
        claim_data: dict,
    ) -> str:
        """
        Generate human-readable summary via Claude API.

        Args:
            if_signals: Top isolation forest signals with SHAP values
            gbm_signals: Top GBM signals with SHAP values
            claim_data: Claim information

        Returns:
            Human-readable summary (2-3 sentences)
        """
        if not self.anthropic:
            # Fallback if no API key
            return "Unable to generate summary: API not configured. Review ML signals directly."

        try:
            # Format signals for prompt
            signals_text = "Key Risk Signals:\n"
            signals_text += "Isolation Forest:\n"
            for sig in if_signals[:3]:
                signals_text += f"  - {sig.feature}: {sig.value:.3f} (SHAP: {sig.shap_value:.3f})\n"

            signals_text += "GBM Model:\n"
            for sig in gbm_signals[:3]:
                signals_text += f"  - {sig.feature}: {sig.value:.3f} (SHAP: {sig.shap_value:.3f})\n"

            signals_text += f"\nClaim Amount: ₹{claim_data.get('payout_eligible_inr', 0):.0f}\n"
            signals_text += f"Worker: {'New' if claim_data.get('is_new_worker') else 'Established'}\n"

            # Call Claude
            message = self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                system=(
                    "You are a fraud analyst assistant for insurance claims. "
                    "Summarise the key risk signals in 2-3 plain English sentences. "
                    "Be factual, concise, and focus on actionable insights. "
                    "Do not use technical jargon."
                ),
                messages=[
                    {
                        "role": "user",
                        "content": signals_text,
                    }
                ],
            )

            summary = message.content[0].text

            logger.info(
                "claude_summary_generated",
                claim_id=claim_data.get("claim_id"),
                summary_length=len(summary),
            )

            return summary

        except Exception as e:
            logger.error(
                "claude_api_error",
                error=str(e),
                claim_id=claim_data.get("claim_id"),
            )
            # Fallback summary
            return (
                f"Anomalies detected: {if_signals[0].feature if if_signals else 'unknown'} "
                f"and {gbm_signals[0].feature if gbm_signals else 'unknown'} show unusual patterns. "
                f"Manual review recommended."
            )

    @staticmethod
    def _generate_recommendation(
        risk_score: float,
        risk_breakdown: dict,
        is_new_worker: bool,
        approval_rate: float,
        crowd_spike: bool,
    ) -> str:
        """Generate recommendation based on risk profile."""
        recommendation_parts = []

        # Risk score assessment
        if risk_score > 0.8:
            recommendation_parts.append("HIGH RISK: Strong indicators of potential fraud.")
        elif risk_score > 0.6:
            recommendation_parts.append("MEDIUM-HIGH RISK: Several concerning signals present.")
        elif risk_score > 0.4:
            recommendation_parts.append("MEDIUM RISK: Some anomalies detected, but not conclusive.")
        else:
            recommendation_parts.append("Low risk profile overall, but manual verification recommended.")

        # Worker history
        if is_new_worker:
            recommendation_parts.append("Worker is new (first claim)—heightened verification needed.")
        elif approval_rate < 0.3:
            recommendation_parts.append("Worker has poor claim history (approval rate < 30%).")

        # Crowd signals
        if crowd_spike:
            recommendation_parts.append("Unusual crowd activity detected—zone is anomalous.")

        # Final recommendation
        if risk_score > 0.7 or (is_new_worker and risk_score > 0.5):
            recommendation_parts.append("\n**RECOMMENDED ACTION: REJECT or REQUEST MORE INFO**")
        elif risk_score > 0.4:
            recommendation_parts.append("\n**RECOMMENDED ACTION: REQUEST SOFT VERIFICATION** (if not already done)")
        else:
            recommendation_parts.append("\n**RECOMMENDED ACTION: APPROVE** (if manual review confirms)")

        return " ".join(recommendation_parts)
