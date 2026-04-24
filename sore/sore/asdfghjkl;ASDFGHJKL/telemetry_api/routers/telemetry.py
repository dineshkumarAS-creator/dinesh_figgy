from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import ValidationError
from slowapi import Limiter
from slowapi.util import get_remote_address

from telemetry_api.auth.jwt_handler import extract_bearer_token, verify_jwt_token
from telemetry_api.kafka.producer import publish_dlq_event, publish_telemetry_event
from telemetry_api.schemas.telemetry import TelemetryBatchRequest, TelemetryEventRequest

logger = structlog.get_logger()

limiter = Limiter(key_func=lambda request: rate_limit_key(request))
router = APIRouter(prefix="/v1/telemetry", tags=["telemetry"])

# Metrics tracking
_events_published = 0
_events_failed = 0
_batches_received = 0
_start_time = datetime.now(timezone.utc)


def rate_limit_key(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            return verify_jwt_token(token)
        except HTTPException:
            pass
    return get_remote_address(request)


def get_worker_id(authorization: str | None = Header(None)) -> str:
    """Extract and validate worker_id from JWT token."""
    if authorization is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing Authorization header")
    token = extract_bearer_token(authorization)
    return verify_jwt_token(token)


def validate_timestamp(timestamp: datetime) -> bool:
    """Check if timestamp is within ±5 minutes of server time (anti-replay)."""
    now = datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    delta = abs((now - timestamp).total_seconds())
    return delta <= 300


def validate_gps_event(event: TelemetryEventRequest) -> tuple[bool, str | None]:
    """Validate GPS event fields."""
    if event.event_type != "gps":
        return True, None
    if event.lat is None or event.lon is None or event.accuracy_m is None:
        return False, "GPS event missing required fields: lat, lon, accuracy_m"
    if not (-90 <= event.lat <= 90):
        return False, f"lat out of range: {event.lat}"
    if not (-180 <= event.lon <= 180):
        return False, f"lon out of range: {event.lon}"
    if event.accuracy_m >= 500:
        return False, f"accuracy_m too large: {event.accuracy_m}m"
    return True, None


def validate_imu_event(event: TelemetryEventRequest) -> tuple[bool, str | None]:
    """Validate IMU event fields. Reject if all accel values are exactly 0.0."""
    if event.event_type != "imu":
        return True, None
    accel_values = [v for v in (event.accel_x, event.accel_y, event.accel_z) if v is not None]
    if accel_values and all(v == 0.0 for v in accel_values):
        return False, "Dead sensor: all accel values are 0.0"
    return True, None


def validate_app_state_event(event: TelemetryEventRequest) -> tuple[bool, str | None]:
    """Validate app state event."""
    if event.event_type != "app_state":
        return True, None
    if event.app_state is None:
        return False, "app_state event missing required field: app_state"
    return True, None


def validate_delivery_attempt_event(event: TelemetryEventRequest) -> tuple[bool, str | None]:
    """Validate delivery attempt event."""
    if event.event_type != "delivery_attempt":
        return True, None
    if event.delivery_zone_id is None:
        return False, "delivery_attempt event missing required field: delivery_zone_id"
    return True, None


def validate_telemetry_event(event: TelemetryEventRequest) -> tuple[bool, str | None]:
    """Comprehensive validation for a single telemetry event."""
    # Check timestamp anti-replay
    if not validate_timestamp(event.timestamp_utc):
        return False, f"Timestamp outside ±5min window: {event.timestamp_utc}"

    # Event-type specific validation
    validators = [
        validate_gps_event,
        validate_imu_event,
        validate_app_state_event,
        validate_delivery_attempt_event,
    ]
    for validator in validators:
        is_valid, reason = validator(event)
        if not is_valid:
            return False, reason

    return True, None


@router.post("/batch", status_code=202)
@limiter.limit("100/minute")
async def ingest_telemetry_batch(
    request: Request,
    batch: TelemetryBatchRequest,
    worker_id: str = Depends(get_worker_id),
) -> dict[str, Any]:
    """
    Ingest batch of up to 50 telemetry events.
    
    - JWT bearer token required (worker_id extracted from token)
    - Rate limited: 100 requests/min per worker
    - Validates each event; rejects batch if >80% fail validation
    - Publishes valid events to Kafka
    - Returns 202 Accepted (async processing)
    """
    global _events_published, _events_failed, _batches_received
    _batches_received += 1

    if not batch.events:
        logger.warning("empty_batch", worker_id=worker_id)
        return {"message": "Empty batch", "accepted_count": 0}

    valid_events = []
    invalid_events = []

    for idx, event in enumerate(batch.events):
        is_valid, reason = validate_telemetry_event(event)
        if is_valid:
            valid_events.append(event)
        else:
            invalid_events.append((idx, reason))
            logger.warning(
                "telemetry_event_invalid",
                worker_id=worker_id,
                event_idx=idx,
                event_type=event.event_type,
                reason=reason,
            )
            _events_failed += 1

    # Check if >80% of events failed
    failure_rate = len(invalid_events) / len(batch.events) if batch.events else 0
    if failure_rate > 0.8:
        logger.error(
            "batch_rejected_high_failure_rate",
            worker_id=worker_id,
            total_events=len(batch.events),
            invalid_count=len(invalid_events),
            failure_rate=failure_rate,
        )
        # Publish to DLQ
        await publish_dlq_event(
            worker_id,
            "High failure rate (>80%)",
            {"total": len(batch.events), "invalid": len(invalid_events), "failure_rate": failure_rate},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Batch rejected: {failure_rate:.0%} of events failed validation",
        )

    # Publish valid events to Kafka
    for event in valid_events:
        payload = event.model_dump()
        payload["worker_id"] = worker_id
        await publish_telemetry_event(worker_id, payload)
        _events_published += 1

    # If some events failed but <80%, publish to DLQ for observability
    if invalid_events:
        await publish_dlq_event(
            worker_id,
            f"{len(invalid_events)} events failed validation but batch accepted (failure_rate={failure_rate:.0%})",
            {
                "total": len(batch.events),
                "valid": len(valid_events),
                "invalid": len(invalid_events),
                "invalid_details": [{"idx": idx, "reason": reason} for idx, reason in invalid_events],
            },
        )

    logger.info(
        "batch_ingested",
        worker_id=worker_id,
        total_events=len(batch.events),
        valid_count=len(valid_events),
        invalid_count=len(invalid_events),
    )

    return {
        "message": "Batch accepted",
        "total_events": len(batch.events),
        "accepted_count": len(valid_events),
        "rejected_count": len(invalid_events),
    }


def get_metrics() -> dict[str, float]:
    elapsed_seconds = max((datetime.now(timezone.utc) - _start_time).total_seconds(), 1.0)
    total_events = _events_published + _events_failed
    return {
        "events_per_sec": _events_published / elapsed_seconds,
        "validation_failure_rate": (_events_failed / total_events) if total_events else 0.0,
    }
