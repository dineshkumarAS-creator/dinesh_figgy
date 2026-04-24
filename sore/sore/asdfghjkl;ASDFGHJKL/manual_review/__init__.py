"""
Manual Review System for FIGGY

Handles high-risk claims (TIER_3) requiring human verification before payout.

Modules:
- schemas: Pydantic models for type safety
- queue: ReviewQueueService for priority-based queue management
- reviewers: ReviewerService for auto-assignment and load balancing
- context_builder: ClaimContextBuilder for aggregating ML + worker + crowd signals
- api: FastAPI endpoints for reviewer workflow
- appeals: AppealService for REJECTED claim appeals

Key Concepts:
- Priority tiers: 1=CRITICAL (2h SLA), 2=HIGH (4h SLA), 3=NORMAL (8h SLA)
- Auto-assignment: Role-based (junior/senior/lead) + load balancing
- Claude integration: Human-readable summaries of ML signals
- Appeals: Workers can appeal rejections with 24-hour resolution SLA
"""

__version__ = "1.0.0"
__all__ = [
    "schemas",
    "queue",
    "reviewers",
    "context_builder",
    "api",
    "appeals",
]
