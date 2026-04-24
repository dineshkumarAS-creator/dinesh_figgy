from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GPSEvent(BaseModel):
    event_type: Literal["gps"] = "gps"
    timestamp_utc: datetime
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    accuracy_m: float = Field(..., ge=0, lt=500)
    speed_kmh: Optional[float] = Field(default=None, ge=0)
    battery_pct: Optional[int] = Field(default=None, ge=0, le=100)


class IMUEvent(BaseModel):
    event_type: Literal["imu"] = "imu"
    timestamp_utc: datetime
    accel_x: Optional[float] = None
    accel_y: Optional[float] = None
    accel_z: Optional[float] = None
    gyro_x: Optional[float] = None
    gyro_y: Optional[float] = None
    gyro_z: Optional[float] = None
    battery_pct: Optional[int] = Field(default=None, ge=0, le=100)

    @field_validator("accel_x", "accel_y", "accel_z", "gyro_x", "gyro_y", "gyro_z", mode="before")
    def validate_not_all_zero_accel(cls, v):
        return v


class AppStateEvent(BaseModel):
    event_type: Literal["app_state"] = "app_state"
    timestamp_utc: datetime
    app_state: Literal["foreground", "background", "offline"]
    battery_pct: Optional[int] = Field(default=None, ge=0, le=100)


class DeliveryAttemptEvent(BaseModel):
    event_type: Literal["delivery_attempt"] = "delivery_attempt"
    timestamp_utc: datetime
    delivery_zone_id: str
    battery_pct: Optional[int] = Field(default=None, ge=0, le=100)


class TelemetryEventRequest(BaseModel):
    event_type: Literal["gps", "imu", "app_state", "delivery_attempt"]
    timestamp_utc: datetime
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
    app_state: Optional[Literal["foreground", "background", "offline"]] = None
    delivery_zone_id: Optional[str] = None
    battery_pct: Optional[int] = None


class TelemetryBatchRequest(BaseModel):
    events: list[TelemetryEventRequest] = Field(..., max_length=50)


class TelemetryEventPayload(BaseModel):
    model_config = ConfigDict(strict=True)
    worker_id: str
    event_type: Literal["gps", "imu", "app_state", "delivery_attempt"]
    timestamp_utc: datetime
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
    app_state: Optional[Literal["foreground", "background", "offline"]] = None
    delivery_zone_id: Optional[str] = None
    battery_pct: Optional[int] = None


class HealthCheckResponse(BaseModel):
    status: str
    timestamp_utc: datetime


class MetricsResponse(BaseModel):
    active_connections: int
    events_per_sec: float
    validation_failure_rate: float
