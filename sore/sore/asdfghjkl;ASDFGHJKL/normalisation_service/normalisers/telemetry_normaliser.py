from datetime import datetime, timezone
from typing import Dict, Any, Optional
import yaml

from normalisation_service.schemas.normalised_schemas import NormalisedTelemetryEvent


class TelemetryNormaliser:
    def __init__(self, config_path: str = "normalisation_config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)["telemetry"]

    def normalise(self, raw_event: Dict[str, Any]) -> NormalisedTelemetryEvent:
        """Normalise telemetry data."""
        worker_id = raw_event["worker_id"]
        event_type = raw_event["event_type"]
        timestamp_utc = raw_event["timestamp_utc"]
        lat = raw_event.get("lat")
        lon = raw_event.get("lon")
        accuracy_m = raw_event.get("accuracy_m")
        speed_kmh = raw_event.get("speed_kmh")
        accel_x = raw_event.get("accel_x")
        accel_y = raw_event.get("accel_y")
        accel_z = raw_event.get("accel_z")
        gyro_x = raw_event.get("gyro_x")
        gyro_y = raw_event.get("gyro_y")
        gyro_z = raw_event.get("gyro_z")
        app_state = raw_event.get("app_state")
        delivery_zone_id = raw_event.get("delivery_zone_id")
        battery_pct = raw_event.get("battery_pct")
        altitude = raw_event.get("altitude")
        heading_degrees = raw_event.get("heading_degrees")
        network_type = raw_event.get("network_type")

        # Normalise GPS
        normalised_lat, normalised_lon, out_of_bounds = self._normalise_gps(lat, lon)

        # Normalise speed
        normalised_speed, speed_valid = self._normalise_speed(speed_kmh)

        # Normalise IMU
        device_model = self._infer_device_model(worker_id)
        scale = self.config["imu_devices"].get(device_model, self.config["imu_devices"]["default"])["accel_scale"]
        normalised_accel_x = accel_x * scale if accel_x else None
        normalised_accel_y = accel_y * scale if accel_y else None
        normalised_accel_z = accel_z * scale if accel_z else None

        return NormalisedTelemetryEvent(
            worker_id=worker_id,
            event_type=event_type,
            timestamp_utc=timestamp_utc,
            lat=lat,
            lon=lon,
            accuracy_m=accuracy_m,
            speed_kmh=speed_kmh,
            accel_x=accel_x,
            accel_y=accel_y,
            accel_z=accel_z,
            gyro_x=gyro_x,
            gyro_y=gyro_y,
            gyro_z=gyro_z,
            app_state=app_state,
            delivery_zone_id=delivery_zone_id,
            battery_pct=battery_pct,
            altitude=altitude,
            heading_degrees=heading_degrees,
            network_type=network_type,
            normalised_lat=normalised_lat,
            normalised_lon=normalised_lon,
            out_of_bounds=out_of_bounds,
            normalised_speed_kmh=normalised_speed,
            speed_valid=speed_valid,
            normalised_accel_x_ms2=normalised_accel_x,
            normalised_accel_y_ms2=normalised_accel_y,
            normalised_accel_z_ms2=normalised_accel_z,
            normalised_at=datetime.now(timezone.utc),
            device_model=device_model,
        )

    def _normalise_gps(self, lat: Optional[float], lon: Optional[float]) -> tuple[Optional[float], Optional[float], bool]:
        """Clip GPS to India bbox."""
        if lat is None or lon is None:
            return lat, lon, False

        bbox = self.config["india_bbox"]
        clipped_lat = max(bbox["lat_min"], min(bbox["lat_max"], lat))
        clipped_lon = max(bbox["lon_min"], min(bbox["lon_max"], lon))
        out_of_bounds = (clipped_lat != lat) or (clipped_lon != lon)

        return clipped_lat, clipped_lon, out_of_bounds

    def _normalise_speed(self, speed_kmh: Optional[float]) -> tuple[Optional[float], bool]:
        """Cap speed at 200 km/h."""
        if speed_kmh is None:
            return speed_kmh, True

        if speed_kmh > self.config["speed_cap_kmh"]:
            return self.config["speed_cap_kmh"], False

        return speed_kmh, True

    def _infer_device_model(self, worker_id: str) -> str:
        """Infer device model from worker_id."""
        return self.config["worker_id_to_device"].get(worker_id, "default")