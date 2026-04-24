from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class NormalisedWeatherData(BaseModel):
    # Raw fields
    location: str
    timestamp: int  # timestamp-millis
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    pressure_hpa: Optional[float] = None
    description: Optional[str] = None

    # Normalised fields
    normalised_rainfall_mm_hr: Optional[float] = None
    normalised_temperature_c: Optional[float] = None
    normalised_wind_speed_ms: Optional[float] = None
    normalised_pressure_hpa: Optional[float] = None
    normalised_at: datetime
    source_quality_score: float = Field(ge=0.0, le=1.0)


class NormalisedAQIData(BaseModel):
    # Raw fields
    location: str
    timestamp: int
    aqi_value: int
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    o3: Optional[float] = None
    no2: Optional[float] = None
    so2: Optional[float] = None
    co: Optional[float] = None

    # Normalised fields
    normalised_aqi_us: int = Field(ge=0, le=500)
    normalised_pm25_ug_m3: Optional[float] = None
    normalised_pm10_ug_m3: Optional[float] = None
    normalised_no2_ug_m3: Optional[float] = None
    normalised_at: datetime
    is_hazardous: bool


class NormalisedTelemetryEvent(BaseModel):
    # Raw fields
    worker_id: str
    event_type: str
    timestamp_utc: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    accuracy_m: Optional[float] = None
    speed_kmh: Optional[float] = None
    accel_x: Optional[float] = None
    accel_y: Optional[float] = None
    accel_z: Optional[float] = None
    gyro_x: Optional[float] = None
    gyro_y: Optional[float] = None
    gyro_z: Optional[float] = None
    app_state: Optional[str] = None
    delivery_zone_id: Optional[str] = None
    battery_pct: Optional[int] = None
    altitude: Optional[float] = None
    heading_degrees: Optional[float] = None
    network_type: Optional[str] = None

    # Normalised fields
    normalised_lat: Optional[float] = None
    normalised_lon: Optional[float] = None
    out_of_bounds: bool = False
    normalised_speed_kmh: Optional[float] = None
    speed_valid: bool = True
    normalised_accel_x_ms2: Optional[float] = None
    normalised_accel_y_ms2: Optional[float] = None
    normalised_accel_z_ms2: Optional[float] = None
    normalised_at: datetime
    device_model: str