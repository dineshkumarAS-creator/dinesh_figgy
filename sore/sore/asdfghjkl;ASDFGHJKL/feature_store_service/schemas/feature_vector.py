from pydantic import BaseModel, validator
from datetime import datetime
from typing import Optional

class FeatureVector(BaseModel):
    # Metadata
    worker_id: str
    minute_bucket: int
    feature_pipeline_version: str
    computed_at: datetime

    # Environmental features
    rainfall_mm_per_hr: Optional[float] = None
    rainfall_intensity_class: Optional[str] = None
    rainfall_30min_trend: Optional[str] = None
    aqi_index_current: Optional[float] = None
    aqi_stdz: Optional[float] = None
    aqi_category: Optional[str] = None
    event_severity_score: Optional[float] = None
    event_type_active: Optional[list] = None
    event_count_active: Optional[int] = None
    composite_disruption_index: Optional[float] = None
    env_feature_quality: Optional[float] = None

    # Worker behaviour features
    gps_displacement_m: Optional[float] = None
    cumulative_displacement_m: Optional[float] = None
    active_zone_minutes: Optional[int] = None
    delivery_attempt_count: Optional[int] = None
    delivery_attempt_rate_per_hr: Optional[float] = None
    motion_continuity_score: Optional[float] = None
    road_match_score: Optional[float] = None
    app_foreground_ratio: Optional[float] = None
    speed_anomaly_count: Optional[int] = None
    behaviour_feature_quality: Optional[float] = None

    # Income signal features
    expected_earnings_inr: Optional[float] = None
    actual_earnings_inr: Optional[float] = None
    income_loss_inr: Optional[float] = None
    income_loss_ratio: Optional[float] = None
    loss_plausibility_score: Optional[float] = None
    loss_plausibility_suspicious: Optional[bool] = None
    delivery_rate_vs_baseline: Optional[float] = None
    delivery_rate_suspicious: Optional[bool] = None
    earnings_consistency_score: Optional[float] = None
    cumulative_loss_session_inr: Optional[float] = None
    payout_eligible_inr: Optional[float] = None

    # Derived quality
    overall_feature_quality: Optional[float] = None
    env_complete: bool = False
    behaviour_complete: bool = False
    income_complete: bool = False

    @validator('overall_feature_quality', always=True)
    def compute_overall_quality(cls, v, values):
        env_q = values.get('env_feature_quality', 0)
        beh_q = values.get('behaviour_feature_quality', 0)
        inc_q = values.get('income_feature_quality', 0)
        return 0.3 * env_q + 0.4 * beh_q + 0.3 * inc_q

    @validator('env_complete', always=True)
    def check_env_complete(cls, v, values):
        required = ['rainfall_mm_per_hr', 'aqi_index_current', 'composite_disruption_index']
        return all(values.get(f) is not None for f in required) and values.get('env_feature_quality', 0) > 0.3

    @validator('behaviour_complete', always=True)
    def check_beh_complete(cls, v, values):
        required = ['gps_displacement_m', 'motion_continuity_score', 'road_match_score']
        return all(values.get(f) is not None for f in required) and values.get('behaviour_feature_quality', 0) > 0.3

    @validator('income_complete', always=True)
    def check_inc_complete(cls, v, values):
        required = ['expected_earnings_inr', 'income_loss_ratio', 'payout_eligible_inr']
        return all(values.get(f) is not None for f in required) and values.get('income_feature_quality', 0) > 0.3

    def validate_quality(self):
        complete_count = sum([self.env_complete, self.behaviour_complete, self.income_complete])
        if complete_count < 2:
            raise FeatureQualityError(f"Only {complete_count} feature groups complete")

class FeatureQualityError(Exception):
    pass