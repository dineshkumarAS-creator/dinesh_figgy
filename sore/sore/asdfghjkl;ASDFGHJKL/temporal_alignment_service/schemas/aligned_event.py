from pydantic import BaseModel
from typing import Optional, List

class AlignedEvent(BaseModel):
    worker_id: str
    minute_bucket: int  # Unix timestamp floored to minute
    timestamp_utc: float  # Window start time

    # Telemetry aggregates
    avg_smoothed_lat: float
    avg_smoothed_lon: float
    max_speed_ms: float
    sum_delivery_attempts: int
    majority_app_state: Optional[str]
    stationary_pct: float  # 0-1
    avg_data_quality_score: float

    # Weather (latest in window)
    weather_city: Optional[str]
    latest_rainfall_mm_per_hr: Optional[float]
    weather_is_trigger: bool
    weather_data_quality_score: Optional[float]

    # AQI (latest in window)
    aqi_city: Optional[str]
    latest_aqi_index: Optional[float]
    aqi_is_trigger: bool
    aqi_data_quality_score: Optional[float]

    # Events (any overlapping)
    active_events: List[str]  # List of event types
    event_trigger: bool

    # Composite
    any_trigger_active: bool

    # Metadata
    window_complete: bool
    telemetry_count: int
    server_received_at: float