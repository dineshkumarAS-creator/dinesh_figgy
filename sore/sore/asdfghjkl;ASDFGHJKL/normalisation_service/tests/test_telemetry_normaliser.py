import pytest
from datetime import datetime, timezone
from normalisation_service.normalisers.telemetry_normaliser import TelemetryNormaliser


class TestTelemetryNormaliser:
    @pytest.fixture
    def normaliser(self):
        return TelemetryNormaliser("normalisation_config.yaml")

    def test_normalise_gps_within_bounds(self, normaliser):
        raw_event = {
            "worker_id": "worker_1",
            "event_type": "gps",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "lat": 28.6139,  # Delhi
            "lon": 77.2090,
            "accuracy_m": 10.0
        }

        result = normaliser.normalise(raw_event)

        assert result.normalised_lat == 28.6139
        assert result.normalised_lon == 77.2090
        assert not result.out_of_bounds

    def test_normalise_gps_out_of_bounds(self, normaliser):
        raw_event = {
            "worker_id": "worker_1",
            "event_type": "gps",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "lat": 40.0,  # Outside India
            "lon": 100.0,
        }

        result = normaliser.normalise(raw_event)

        assert result.normalised_lat == 35.5  # Clipped to max
        assert result.normalised_lon == 97.5  # Clipped to max
        assert result.out_of_bounds

    def test_normalise_speed_valid(self, normaliser):
        raw_event = {
            "worker_id": "worker_1",
            "event_type": "gps",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "speed_kmh": 50.0
        }

        result = normaliser.normalise(raw_event)

        assert result.normalised_speed_kmh == 50.0
        assert result.speed_valid

    def test_normalise_speed_capped(self, normaliser):
        raw_event = {
            "worker_id": "worker_1",
            "event_type": "imu",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "speed_kmh": 250.0  # Above cap
        }

        result = normaliser.normalise(raw_event)

        assert result.normalised_speed_kmh == 200.0  # Capped
        assert not result.speed_valid

    def test_normalise_imu_conversion(self, normaliser):
        raw_event = {
            "worker_id": "worker_1",  # Maps to device_abc, scale 0.001
            "event_type": "imu",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "accel_x": 1000.0,  # ADC value
            "accel_y": 2000.0,
            "accel_z": 3000.0
        }

        result = normaliser.normalise(raw_event)

        assert result.normalised_accel_x_ms2 == 1000.0 * 0.001
        assert result.normalised_accel_y_ms2 == 2000.0 * 0.001
        assert result.normalised_accel_z_ms2 == 3000.0 * 0.001
        assert result.device_model == "device_abc"

    def test_infer_device_model(self, normaliser):
        assert normaliser._infer_device_model("worker_1") == "device_abc"
        assert normaliser._infer_device_model("unknown") == "default"