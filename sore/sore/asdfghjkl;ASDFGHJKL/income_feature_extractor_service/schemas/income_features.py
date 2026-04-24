from pydantic import BaseModel
from datetime import datetime

class IncomeSignalFeatures(BaseModel):
    worker_id: str
    minute_bucket: int

    expected_earnings_inr: float
    actual_earnings_inr: float
    income_loss_inr: float
    income_loss_ratio: float
    loss_plausibility_score: float
    loss_plausibility_suspicious: bool
    delivery_rate_vs_baseline: float
    delivery_rate_suspicious: bool
    earnings_consistency_score: float
    cumulative_loss_session_inr: float
    payout_eligible_inr: float

    feature_computed_at: datetime