"""
Manual Review System - Schemas and Models

Models for review queue, reviewers, claims context, appeals.
"""

from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
import json


# ==============================================================================
# Review Queue Models
# ==============================================================================


class ReviewQueueItem(BaseModel):
    """Item in manual review queue."""
    
    queue_id: str = Field(default_factory=lambda: str(uuid4()))
    claim_id: str
    worker_id: str
    priority: int  # 1=critical, 2=high, 3=normal
    risk_score: float  # 0.0-1.0
    assigned_reviewer_id: Optional[str] = None
    assigned_at: Optional[datetime] = None
    sla_deadline: datetime
    status: Literal["pending", "assigned", "in_review", "decided", "escalated"]
    created_at: datetime
    decided_at: Optional[datetime] = None
    payout_eligible_inr: float
    trust_tier: str  # "new", "trusted", "flagged"


class ManualReviewDecision(BaseModel):
    """Decision made by reviewer on a claim."""
    
    queue_id: str
    claim_id: str
    reviewer_id: str
    decision: Literal["approve", "reject", "request_more_info"]
    rejection_reason: Optional[str] = None
    payout_override_inr: Optional[float] = None
    notes: Optional[str] = None
    confidence: int = Field(ge=1, le=5)  # 1-5
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==============================================================================
# Reviewer Models
# ==============================================================================


class ReviewerProfile(BaseModel):
    """Reviewer profile and stats."""
    
    reviewer_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    email: str
    role: Literal["junior", "senior", "lead"]
    active: bool = True
    current_load: int = 0
    max_load: int  # junior=5, senior=10, lead=15
    specialisation: list[str] = []  # e.g. ["chennai", "rain_claims"]
    total_decided: int = 0
    approval_rate: float = 0.5
    avg_decision_time_min: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReviewerStats(BaseModel):
    """Reviewer statistics for today."""
    
    reviewer_id: str
    name: str
    role: str
    decisions_today: int = 0
    approval_rate: float = 0.5
    avg_decision_time_min: float = 0.0
    current_load: int
    max_load: int


# ==============================================================================
# Claim Context Models
# ==============================================================================


class FeatureVector(BaseModel):
    """Feature snapshot at time of claim."""
    
    motion_continuity: float
    road_match_score: float
    app_foreground_duration_pct: float
    gps_accuracy_meters: float
    speed_variance: float
    stop_detection: bool
    timestamp: datetime


class RiskSignal(BaseModel):
    """Individual risk signal with explanation."""
    
    feature: str
    value: float
    shap_value: float  # SHAP importance
    direction: Literal["positive", "negative"]  # positive = risky
    description: str


class MLExplanations(BaseModel):
    """ML model explanations for the claim."""
    
    lstm_attention_weights: list[float]  # 30 timesteps
    if_top_signals: list[RiskSignal]
    gbm_top_signals: list[RiskSignal]
    human_readable_summary: str  # Claude-generated


class TrustProfile(BaseModel):
    """Worker's historical trust profile."""
    
    worker_id: str
    total_claims: int
    approved_claims: int
    rejected_claims: int
    approval_rate: float
    avg_claim_value_inr: float
    is_new_worker: bool
    flagged_reasons: list[str] = []


class CrowdValidationResult(BaseModel):
    """Crowd validation for the disruption event."""
    
    crowd_size: int
    validation_rate: float  # % of crowd that validated
    consensus_confidence: float
    crowd_spike_flag: bool  # unusual crowd size for zone/time


class ReviewContext(BaseModel):
    """Full context package shown to reviewer."""
    
    claim_id: str
    queue_id: str
    claim: dict  # Full claim record (from ClaimService)
    claim_history: list[dict]  # State transitions
    feature_snapshot: FeatureVector
    risk_breakdown: dict  # From Layer 5 soft verify
    ml_explanations: MLExplanations
    worker_trust_profile: TrustProfile
    crowd_validation: CrowdValidationResult
    similar_past_claims: list[dict]  # Last 5 claims from worker
    zone_disruption_map: dict  # % workers by city block
    recommended_action: str
    risk_score: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==============================================================================
# Appeal Models
# ==============================================================================


class Appeal(BaseModel):
    """Appeal of a rejected claim."""
    
    appeal_id: str = Field(default_factory=lambda: str(uuid4()))
    claim_id: str
    worker_id: str
    appeal_reason: str
    evidence_urls: list[str] = []
    status: Literal["pending", "under_review", "approved", "rejected"]
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    reviewer_id: Optional[str] = None
    decision_notes: Optional[str] = None
    queue_item_id: Optional[str] = None  # Links to review queue appeal item


class AppealDecision(BaseModel):
    """Decision on an appeal."""
    
    appeal_id: str
    decision: Literal["approved", "rejected"]
    reviewer_id: str
    decision_notes: str
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
