from pydantic import BaseModel
from typing import Optional

class FilteredTelemetryEvent(BaseModel):
    worker_id: str
    timestamp: float
    smoothed_lat: float
    smoothed_lon: float
    estimated_speed_ms: float
    position_uncertainty_m: float
    smoothed_accel_x: float
    smoothed_accel_y: float
    smoothed_accel_z: float
    is_stationary: bool

class FilteredWeatherData(BaseModel):
    city: str
    timestamp: float
    smoothed_rainfall_mm_per_hr: float