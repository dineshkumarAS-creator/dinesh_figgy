"""
Payout calculation schemas (Pydantic v2).

All monetary amounts stored as float but calculated with Decimal.
"""

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class DisruptionSession(BaseModel):
    """
    A disruption session: all consecutive 1-minute windows where
    triggers were active for a worker during a claim period.
    """
    
    claim_id: UUID
    worker_id: str
    
    session_start: datetime = Field(..., description="UTC start of disruption")
    session_end: datetime = Field(..., description="UTC end of disruption")
    
    total_duration_minutes: int = Field(..., description="Session length in minutes")
    
    trigger_types: list[str] = Field(
        default_factory=list,
        description="All triggers that fired: ['curfew', 'strike', 'bandh']"
    )
    
    avg_disruption_index: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Mean composite_disruption_index across all windows (0-1)"
    )
    peak_disruption_index: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Max composite_disruption_index in session (0-1)"
    )
    
    total_delivery_attempts: int = Field(
        default=0,
        description="Sum of delivery_attempts across windows"
    )
    
    total_expected_earnings_inr: float = Field(
        ...,
        ge=0.0,
        description="Sum of expected_earnings_inr per minute-window (INR)"
    )
    total_actual_earnings_inr: float = Field(
        ...,
        ge=-1.0,
        description="Sum of actual_earnings_inr per minute-window (INR, -1.0 = all pending)"
    )
    
    windows_with_pending_earnings: int = Field(
        default=0,
        description="Count of windows where actual_earnings = -1.0 (pending)"
    )
    
    data_completeness: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of claim period with complete feature vector data (0-1)"
    )
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PayoutCalculation(BaseModel):
    """Full payout calculation breakdown (audit trail)."""
    
    claim_id: UUID
    worker_id: str
    
    # ===== AMOUNTS (INR) =====
    gross_loss_inr: float = Field(..., ge=0.0, description="Expected - Actual earnings")
    adjusted_loss_inr: float = Field(..., ge=0.0, description="After severity adjustment")
    covered_amount_inr: float = Field(..., ge=0.0, description="After coverage ratio")
    final_payout_inr: float = Field(..., ge=0.0, description="After all caps & adjustments")
    
    # ===== MULTIPLIERS & ADJUSTMENTS =====
    coverage_ratio: float = Field(..., description="Applied coverage ratio")
    severity_multiplier: float = Field(..., description="Disruption severity factor (0-1)")
    data_quality_adjustment: float = Field(..., description="Data completeness penalty (0-1)")
    trust_adjustment_applied: bool = Field(default=False, description="Gold tier bonus applied")
    
    # ===== CAP ENFORCEMENT =====
    cap_applied: Optional[Literal["daily_cap", "monthly_cap", "claim_cap"]] = Field(
        default=None,
        description="Which cap was enforced"
    )
    below_minimum: bool = Field(
        default=False,
        description="Payout below MIN_PAYOUT_INR threshold"
    )
    
    # ===== CONTEXT =====
    daily_total_after_payout: float = Field(
        ...,
        ge=0.0,
        description="Worker's daily total post-payout"
    )
    monthly_total_after_payout: float = Field(
        ...,
        ge=0.0,
        description="Worker's monthly total post-payout"
    )
    
    # ===== AUDIT TRAIL =====
    calculation_breakdown: dict[str, Any] = Field(
        default_factory=dict,
        description="Full step-by-step calculation for audit"
    )
    calculated_by: str = Field(
        default="auto",
        description="Who calculated: 'auto' or reviewer_id"
    )
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PayoutLedgerEntry(BaseModel):
    """Single payout record (payment tracking)."""
    
    ledger_id: UUID
    claim_id: UUID
    worker_id: str
    calculation_id: UUID = Field(..., description="Foreign key to payout_calculations")
    
    payout_inr: float = Field(..., ge=0.0, description="Amount being paid")
    payment_method: str = Field(..., description="bank|upi|wallet")
    payment_ref: Optional[str] = Field(
        default=None,
        description="UPI ref, bank txn ID, etc."
    )
    
    payment_status: Literal["pending", "processing", "success", "failed", "refunded"] = Field(
        default="pending"
    )
    
    payment_initiated_at: Optional[datetime] = None
    payment_confirmed_at: Optional[datetime] = None
    
    pow_token_id: Optional[str] = Field(
        default=None,
        description="Blockchain token reference (if applicable)"
    )
    smart_contract_tx_hash: Optional[str] = Field(
        default=None,
        description="Smart contract transaction hash (if applicable)"
    )
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkerProfile(BaseModel):
    """Worker profile for payout calculations."""
    
    worker_id: str
    trust_tier: Literal["new", "silver", "gold", "flagged"] = Field(
        default="new",
        description="Worker classification"
    )
    base_hourly_rate_inr: float = Field(..., gt=0, description="Hourly rate")
    historical_avg_earnings_per_hr: float = Field(
        ...,
        ge=0,
        description="Average earnings/hour from history"
    )
    is_active: bool = Field(default=True)


class ClaimRiskScore(BaseModel):
    """ML risk assessment for claim validation."""
    
    worker_id: str
    minute_bucket: int = Field(..., description="Unix timestamp of minute window")
    composite_claim_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Composite claim fraud score (0-1)"
    )
    confidence_level: Literal["low", "medium", "high"] = Field(
        ...,
        description="Confidence in the score"
    )
    disruption_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Disruption/trigger detection score"
    )
    anti_spoofing_flag: bool = Field(
        default=False,
        description="Potential spoofing detected"
    )
    top_risk_signals: list[str] = Field(
        default_factory=list,
        description="Top contributing risk signals"
    )
    score_components: dict[str, float] = Field(
        default_factory=dict,
        description="Individual component scores"
    )
