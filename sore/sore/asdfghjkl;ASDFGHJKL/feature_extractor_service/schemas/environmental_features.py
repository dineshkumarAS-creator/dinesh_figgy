from pydantic import BaseModel
from typing import Literal, List
from datetime import datetime

class EnvironmentalFeatures(BaseModel):
    worker_id: str
    city: str
    minute_bucket: int

    rainfall_mm_per_hr: float
    rainfall_intensity_class: Literal["none", "light", "moderate", "heavy", "extreme"]
    rainfall_30min_trend: Literal["stable", "increasing", "decreasing", "spike"]

    aqi_index_current: float
    aqi_stdz: float
    aqi_category: Literal["good", "moderate", "unhealthy_sensitive", "unhealthy", "very_unhealthy", "hazardous"]

    event_severity_score: float
    event_type_active: List[str]
    event_count_active: int

    composite_disruption_index: float
    env_feature_quality: float

    feature_computed_at: datetime