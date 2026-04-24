from pydantic import BaseModel
from datetime import datetime

class WorkerBehaviourFeatures(BaseModel):
    worker_id: str
    minute_bucket: int

    gps_displacement_m: float
    cumulative_displacement_m: float
    active_zone_minutes: int
    delivery_attempt_count: int
    delivery_attempt_rate_per_hr: float
    motion_continuity_score: float
    road_match_score: float
    app_foreground_ratio: float
    speed_anomaly_count: int
    behaviour_feature_quality: float

    feature_computed_at: datetime