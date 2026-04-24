"""
Payout calculator.

Computes final payout amount with all adjustments:
- Severity multiplier
- Coverage ratio
- Data quality penalties
- Cap enforcement (daily, monthly, per-claim)
- Trust tier bonuses
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from uuid import UUID
import logging

from income_calculator.schemas import (
    DisruptionSession,
    PayoutCalculation,
    WorkerProfile,
    ClaimRiskScore,
)
from income_calculator.config import payout_config

logger = logging.getLogger(__name__)


class PayoutCalculator:
    """
    Calculates final payout amount with full audit trail.
    
    Formula:
        1. gross_loss = expected - actual
        2. adjusted_loss = gross_loss × severity_multiplier
        3. covered_amount = adjusted_loss × coverage_ratio × data_quality_adjustment
        4. final_payout = covered_amount (capped by daily/monthly/per-claim limits)
    """
    
    def __init__(self):
        """Initialize calculator."""
        self.config = payout_config
    
    async def calculate(
        self,
        session: DisruptionSession,
        worker_profile: WorkerProfile,
        claim_risk_score: ClaimRiskScore,
        daily_paid_inr: float = 0.0,
        monthly_paid_inr: float = 0.0,
    ) -> PayoutCalculation:
        """
        Calculate final payout.
        
        Args:
            session: DisruptionSession with aggregated earnings
            worker_profile: Worker's trust tier, rates, history
            claim_risk_score: ML risk assessment (for validation)
            daily_paid_inr: Amount already paid to worker today
            monthly_paid_inr: Amount already paid to worker this month
        
        Returns:
            PayoutCalculation with full breakdown
        """
        
        # Convert to Decimal for precise monetary arithmetic
        gross_loss = self._calculate_gross_loss(session)
        breakdown = {
            "step_1_gross_loss_inr": float(gross_loss),
        }
        
        # Step 2: Disruption severity adjustment
        severity_multiplier = self._calculate_severity_multiplier(session)
        adjusted_loss = gross_loss * Decimal(str(severity_multiplier))
        breakdown["step_2_severity_multiplier"] = severity_multiplier
        breakdown["step_2_adjusted_loss_inr"] = float(adjusted_loss)
        
        # Step 3: Coverage ratio
        covered_amount = adjusted_loss * Decimal(str(self.config.COVERAGE_RATIO))
        breakdown["step_3_coverage_ratio"] = self.config.COVERAGE_RATIO
        breakdown["step_3_covered_amount_inr"] = float(covered_amount)
        
        # Step 4: Data quality adjustment
        data_quality_adjustment = self._calculate_data_quality_adjustment(session)
        covered_amount *= Decimal(str(data_quality_adjustment))
        breakdown["step_4_data_completeness"] = session.data_completeness
        breakdown["step_4_data_quality_adjustment"] = data_quality_adjustment
        breakdown["step_4_after_quality_inr"] = float(covered_amount)
        
        # Step 5: Cap enforcement
        cap_applied = None
        remaining_daily = (
            Decimal(str(self.config.MAX_PAYOUT_PER_DAY_INR))
            - Decimal(str(daily_paid_inr))
        )
        remaining_monthly = (
            Decimal(str(self.config.MAX_PAYOUT_PER_MONTH_INR))
            - Decimal(str(monthly_paid_inr))
        )
        
        claim_cap = Decimal(str(self.config.MAX_PAYOUT_PER_CLAIM_INR))
        
        # Apply caps in order of priority
        if covered_amount > remaining_monthly:
            covered_amount = remaining_monthly
            cap_applied = "monthly_cap"
        
        if covered_amount > remaining_daily:
            covered_amount = remaining_daily
            cap_applied = "daily_cap"
        
        if covered_amount > claim_cap:
            covered_amount = claim_cap
            cap_applied = "claim_cap"
        
        breakdown["step_5_cap_applied"] = cap_applied or "none"
        breakdown["step_5_remaining_daily"] = float(remaining_daily)
        breakdown["step_5_remaining_monthly"] = float(remaining_monthly)
        breakdown["step_5_after_caps_inr"] = float(covered_amount)
        
        # Step 6: Trust tier adjustment
        trust_adjustment_applied = False
        final_payout = covered_amount
        
        if worker_profile.trust_tier == "flagged":
            # Flagged workers get 0 payout
            final_payout = Decimal(0)
            breakdown["step_6_flagged_worker"] = True
        elif worker_profile.trust_tier == "gold":
            # Gold workers get 5% bonus (but capped at max per claim)
            gold_bonus = final_payout * Decimal(str(self.config.GOLD_TIER_BONUS - 1.0))
            final_payout = min(
                final_payout * Decimal(str(self.config.GOLD_TIER_BONUS)),
                claim_cap
            )
            trust_adjustment_applied = True
            breakdown["step_6_gold_bonus_inr"] = float(gold_bonus)
        
        breakdown["step_6_final_after_trust_inr"] = float(final_payout)
        
        # Step 7: Minimum threshold
        below_minimum = False
        if final_payout < Decimal(str(self.config.MIN_PAYOUT_INR)):
            final_payout = Decimal(0)
            below_minimum = True
        
        breakdown["step_7_min_threshold_inr"] = self.config.MIN_PAYOUT_INR
        breakdown["step_7_below_minimum"] = below_minimum
        breakdown["step_7_final_payout_inr"] = float(final_payout)
        
        # Calculate new daily/monthly totals
        daily_total_after = Decimal(str(daily_paid_inr)) + final_payout
        monthly_total_after = Decimal(str(monthly_paid_inr)) + final_payout
        
        # Convert back to float for storage
        final_payout_float = float(
            final_payout.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )
        
        calculation = PayoutCalculation(
            claim_id=session.claim_id,
            worker_id=session.worker_id,
            gross_loss_inr=float(
                gross_loss.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ),
            adjusted_loss_inr=float(
                adjusted_loss.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ),
            covered_amount_inr=float(covered_amount),
            final_payout_inr=final_payout_float,
            coverage_ratio=self.config.COVERAGE_RATIO,
            severity_multiplier=severity_multiplier,
            data_quality_adjustment=data_quality_adjustment,
            cap_applied=cap_applied,
            below_minimum=below_minimum,
            trust_adjustment_applied=trust_adjustment_applied,
            daily_total_after_payout=float(daily_total_after),
            monthly_total_after_payout=float(monthly_total_after),
            calculation_breakdown=breakdown,
        )
        
        logger.info(
            "payout_calculated",
            claim_id=str(session.claim_id),
            worker_id=session.worker_id,
            gross_loss_inr=float(gross_loss),
            final_payout_inr=final_payout_float,
            cap_applied=cap_applied,
        )
        
        return calculation
    
    @staticmethod
    def _calculate_gross_loss(session: DisruptionSession) -> Decimal:
        """
        Calculate gross income loss (expected - actual).
        
        Never negative (floor at 0).
        """
        expected = Decimal(str(session.total_expected_earnings_inr))
        actual = Decimal(str(max(0, session.total_actual_earnings_inr)))
        loss = expected - actual
        return max(Decimal(0), loss)
    
    def _calculate_severity_multiplier(self, session: DisruptionSession) -> float:
        """
        Calculate disruption severity adjustment.
        
        Full payout (multiplier=1.0) only when avg_disruption_index >= 0.6.
        Pro-rata below that: multiplier = disruption_index / 0.6.
        
        Rationale:
        - Only extreme disruptions (40mm+ rain, AQI 400+, all-day curfew)
          have disruption_index >= 0.6
        - Moderate disruptions get partial coverage proportional to severity
        - Example: disruption_index=0.3 → multiplier=0.5 (50% loss covered)
        """
        avg_idx = session.avg_disruption_index
        threshold = self.config.DISRUPTION_SEVERITY_THRESHOLD
        
        if avg_idx >= threshold:
            return 1.0  # Full coverage for extreme disruptions
        
        # Pro-rata for moderate disruptions
        multiplier = avg_idx / threshold
        return min(1.0, max(0.0, multiplier))
    
    def _calculate_data_quality_adjustment(self, session: DisruptionSession) -> float:
        """
        Apply penalties for incomplete data.
        
        Rationale: Poor data → less confident in loss estimate → lower payout.
        - completeness < 30%: 50% penalty (very unreliable)
        - completeness < 60%: 20% penalty (missing some windows)
        - completeness >= 60%: no penalty (good data)
        """
        completeness = session.data_completeness
        
        if completeness < self.config.DATA_COMPLETENESS_CRITICAL_THRESHOLD:
            return self.config.DATA_COMPLETENESS_PENALTY_CRITICAL
        
        if completeness < self.config.DATA_COMPLETENESS_HIGH_THRESHOLD:
            return self.config.DATA_COMPLETENESS_PENALTY_HIGH
        
        return 1.0  # No penalty
