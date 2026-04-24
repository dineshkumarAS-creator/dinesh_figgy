"""
Payout calculator configuration.

All monetary thresholds, coverage ratios, and severity multiplier settings.
"""

import os
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

class PayoutConfig(BaseSettings):
    """Payout calculation configuration."""
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )
    
    # ======================================================================
    # COVERAGE & LOSS ADJUSTMENT
    # ======================================================================
    
    COVERAGE_RATIO: float = 0.67
    """
    Fraction of verified income loss that's covered by insurance.
    
    Rationale: 67% ensures workers share risk (not 100% payouts)
    while providing substantial income protection. Workers not covered
    for 33% incentivizes them to diversify income sources and avoid
    over-reliance on disruption events.
    """
    
    DISRUPTION_SEVERITY_THRESHOLD: float = 0.6
    """
    Disruption index above which payout is 100%.
    
    Rationale: Only extreme disruptions (40mm+ rain, AQI 400+, all-day
    curfew) trigger full coverage. Moderate disruptions (20mm rain,
    AQI 250) get pro-rata coverage based on actual income impact.
    """
    
    # ======================================================================
    # DATA QUALITY PENALTIES
    # ======================================================================
    
    DATA_COMPLETENESS_HIGH_THRESHOLD: float = 0.6
    """If completeness < 60%, apply 20% penalty."""
    
    DATA_COMPLETENESS_PENALTY_HIGH: float = 0.8
    """Multiply payout by 0.8 (20% penalty) for low completeness."""
    
    DATA_COMPLETENESS_CRITICAL_THRESHOLD: float = 0.3
    """If completeness < 30%, apply 50% penalty."""
    
    DATA_COMPLETENESS_PENALTY_CRITICAL: float = 0.5
    """Multiply payout by 0.5 (50% penalty) for critical data gaps."""
    
    # ======================================================================
    # PAYOUT LIMITS (ALL INR)
    # ======================================================================
    
    MIN_PAYOUT_INR: float = 50.0
    """Minimum worth paying out. Below this → $0 payout."""
    
    MAX_PAYOUT_PER_CLAIM_INR: float = 2000.0
    """Hard cap per-claim. No claim exceeds this."""
    
    MAX_PAYOUT_PER_DAY_INR: float = 3000.0
    """Daily cap per worker (UTC day). Prevents abuse from multiple false claims."""
    
    MAX_PAYOUT_PER_MONTH_INR: float = 15000.0
    """Monthly cap per worker (UTC month). Prevents excess payouts."""
    
    # ======================================================================
    # TRUST TIER ADJUSTMENTS
    # ======================================================================
    
    GOLD_TIER_BONUS: float = 1.05
    """Multiply payout by 1.05 (5% loyalty bonus) for gold-tier workers."""
    
    # ======================================================================
    # PENDING EARNINGS ESTIMATION
    # ======================================================================
    
    PENDING_EARNINGS_ESTIMATE_CONSERVATIVE: float = 0.7
    """
    When actual_earnings = -1.0 (pending), estimate as:
      historical_avg_earnings × (1 - avg_disruption_index) × 0.7
    
    The 0.7 multiplier is conservative — assumes even "normal" hour rates
    are reduced 30% during disruptions (e.g., fewer rides available).
    """
    
    # ======================================================================
    # ENVIRONMENT
    # ======================================================================
    
    config_file: str = "payout_config.yaml"


# Singleton instance
payout_config = PayoutConfig()
