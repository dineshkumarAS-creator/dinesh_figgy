from pydantic import BaseModel
from typing import Optional

class CleanTelemetryEvent(BaseModel):
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
    # Outlier fields
    is_outlier: bool
    outlier_method: Optional[str]
    outlier_field: Optional[str]
    outlier_z_score: Optional[float]
    imputed: bool
    imputed_value: Optional[float]
    data_quality_score: float

class CleanWeatherData(BaseModel):
    city: str
    timestamp: float
    smoothed_rainfall_mm_per_hr: float
    # Assume other fields
    temperature_c: Optional[float] = None
    is_government_verified: Optional[bool] = None
    # Outlier fields
    is_outlier: bool
    outlier_method: Optional[str]
    outlier_field: Optional[str]
    outlier_z_score: Optional[float]
    imputed: bool
    imputed_value: Optional[float]
    data_quality_score: float

class CleanAQIData(BaseModel):
    city: str
    timestamp: float
    aqi_index_current: float
    is_government_verified: Optional[bool] = None
    # Outlier fields
    is_outlier: bool
    outlier_method: Optional[str]
    outlier_field: Optional[str]
    outlier_z_score: Optional[float]
    imputed: bool
    imputed_value: Optional[float]
    data_quality_score: float