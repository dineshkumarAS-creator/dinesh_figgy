from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from telemetry_api.auth.jwt_handler import create_jwt_token
from telemetry_api.main import app


async def _noop_async(*args, **kwargs):
    return None


@pytest.fixture(autouse=True)
def patch_kafka_dependencies(monkeypatch):
    """Patch Kafka producer initialization and publishing so tests run without Kafka."""
    monkeypatch.setattr("telemetry_api.main.init_producer", lambda: None)
    monkeypatch.setattr("telemetry_api.main.close_producer", lambda: None)
    monkeypatch.setattr("telemetry_api.routers.telemetry.publish_telemetry_event", _noop_async)
    monkeypatch.setattr("telemetry_api.routers.telemetry.publish_dlq_event", _noop_async)
    yield


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def valid_token(request):
    """Valid JWT token for testing with a unique worker_id per test."""
    worker_id = f"worker_{request.node.name}"
    return create_jwt_token(worker_id)


@pytest.fixture
def expired_token():
    """Expired JWT token."""
    import jwt
    import os

    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
    payload = {
        "worker_id": "worker_123",
        "iat": datetime.now(timezone.utc) - timedelta(hours=25),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


class TestHealthAndMetrics:
    def test_health_check(self, client):
        response = client.get("/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert "timestamp_utc" in response.json()

    def test_metrics_endpoint(self, client):
        response = client.get("/v1/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data
        assert "events_per_sec" in data
        assert "validation_failure_rate" in data


class TestAuthentication:
    def test_missing_auth_header(self, client):
        response = client.post(
            "/v1/telemetry/batch",
            json={"events": []},
        )
        assert response.status_code == 403

    def test_invalid_auth_header(self, client):
        response = client.post(
            "/v1/telemetry/batch",
            json={"events": []},
            headers={"Authorization": "InvalidToken"},
        )
        assert response.status_code == 401

    def test_expired_token(self, client, expired_token):
        response = client.post(
            "/v1/telemetry/batch",
            json={"events": []},
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    def test_valid_token(self, client, valid_token):
        response = client.post(
            "/v1/telemetry/batch",
            json={"events": []},
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        # Empty batch is accepted
        assert response.status_code == 202

    def test_rate_limit_per_worker(self, client, valid_token):
        now = datetime.now(timezone.utc)
        event = {
            "event_type": "gps",
            "timestamp_utc": now.isoformat(),
            "lat": 12.9716,
            "lon": 77.5946,
            "accuracy_m": 10.5,
        }
        for _ in range(100):
            response = client.post(
                "/v1/telemetry/batch",
                json={"events": [event]},
                headers={"Authorization": f"Bearer {valid_token}"},
            )
            assert response.status_code in (202, 429)

        response = client.post(
            "/v1/telemetry/batch",
            json={"events": [event]},
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 429


class TestGPSEventValidation:
    def test_gps_event_valid(self, client, valid_token):
        now = datetime.now(timezone.utc)
        event = {
            "event_type": "gps",
            "timestamp_utc": now.isoformat(),
            "lat": 12.9716,
            "lon": 77.5946,
            "accuracy_m": 10.5,
            "speed_kmh": 25.3,
        }
        response = client.post(
            "/v1/telemetry/batch",
            json={"events": [event]},
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["accepted_count"] == 1
        assert data["rejected_count"] == 0

    def test_gps_event_lat_out_of_range(self, client, valid_token):
        now = datetime.now(timezone.utc)
        event = {
            "event_type": "gps",
            "timestamp_utc": now.isoformat(),
            "lat": 95.0,
            "lon": 77.5946,
            "accuracy_m": 10.5,
        }
        response = client.post(
            "/v1/telemetry/batch",
            json={"events": [event]},
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_gps_event_accuracy_too_large(self, client, valid_token):
        now = datetime.now(timezone.utc)
        event = {
            "event_type": "gps",
            "timestamp_utc": now.isoformat(),
            "lat": 12.9716,
            "lon": 77.5946,
            "accuracy_m": 500.0,
        }
        response = client.post(
            "/v1/telemetry/batch",
            json={"events": [event]},
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_gps_event_missing_fields(self, client, valid_token):
        now = datetime.now(timezone.utc)
        event = {
            "event_type": "gps",
            "timestamp_utc": now.isoformat(),
            "lat": 12.9716,
        }
        response = client.post(
            "/v1/telemetry/batch",
            json={"events": [event]},
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestIMUEventValidation:
    def test_imu_event_valid(self, client, valid_token):
        now = datetime.now(timezone.utc)
        event = {
            "event_type": "imu",
            "timestamp_utc": now.isoformat(),
            "accel_x": 1.5,
            "accel_y": -2.1,
            "accel_z": 9.8,
            "gyro_x": 0.1,
            "gyro_y": 0.2,
            "gyro_z": 0.3,
        }
        response = client.post(
            "/v1/telemetry/batch",
            json={"events": [event]},
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["accepted_count"] == 1

    def test_imu_event_dead_sensor(self, client, valid_token):
        """Reject IMU if all accel values are exactly 0.0."""
        now = datetime.now(timezone.utc)
        event = {
            "event_type": "imu",
            "timestamp_utc": now.isoformat(),
            "accel_x": 0.0,
            "accel_y": 0.0,
            "accel_z": 0.0,
        }
        response = client.post(
            "/v1/telemetry/batch",
            json={"events": [event]},
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestTimestampValidation:
    def test_timestamp_too_old(self, client, valid_token):
        """Timestamp >5 minutes in past should be rejected."""
        old_time = datetime.now(timezone.utc) - timedelta(minutes=6)
        event = {
            "event_type": "gps",
            "timestamp_utc": old_time.isoformat(),
            "lat": 12.9716,
            "lon": 77.5946,
            "accuracy_m": 10.5,
        }
        response = client.post(
            "/v1/telemetry/batch",
            json={"events": [event]},
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_timestamp_in_future(self, client, valid_token):
        """Timestamp >5 minutes in future should be rejected."""
        future_time = datetime.now(timezone.utc) + timedelta(minutes=6)
        event = {
            "event_type": "gps",
            "timestamp_utc": future_time.isoformat(),
            "lat": 12.9716,
            "lon": 77.5946,
            "accuracy_m": 10.5,
        }
        response = client.post(
            "/v1/telemetry/batch",
            json={"events": [event]},
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestBatchRejection:
    def test_batch_rejected_high_failure_rate(self, client, valid_token):
        """Batch rejected if >80% of events fail validation."""
        now = datetime.now(timezone.utc)
        events = []
        # Add 9 invalid events (90% failure rate)
        for i in range(9):
            events.append({
                "event_type": "gps",
                "timestamp_utc": (now - timedelta(minutes=10)).isoformat(),  # Too old
                "lat": 12.9716,
                "lon": 77.5946,
                "accuracy_m": 10.5,
            })
        # Add 1 valid event
        events.append({
            "event_type": "gps",
            "timestamp_utc": now.isoformat(),
            "lat": 12.9716,
            "lon": 77.5946,
            "accuracy_m": 10.5,
        })
        response = client.post(
            "/v1/telemetry/batch",
            json={"events": events},
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 422
