# FIGGY Telemetry Ingestion API - Design & Validation Strategy

## Overview

Production-ready FastAPI microservice for ingesting worker telemetry (GPS, IMU, app state, delivery attempts) from the FIGGY mobile app. Implements JWT authentication, rate limiting, strict validation, and anti-replay protection before publishing to Kafka.

---

## Architecture

### Core Components

1. **FastAPI Server** (`main.py`)
   - Runs on `0.0.0.0:8000` via Uvicorn
   - Middleware: structured logging, request/response timing
   - Prometheus metrics export (`/v1/metrics`)
   - Health check (`/v1/health`)

2. **Telemetry Router** (`routers/telemetry.py`)
   - Single endpoint: `POST /v1/telemetry/batch`
   - Accepts batch of ≤50 events
   - Comprehensive validation pipeline
   - Publishes valid events to Kafka

3. **Schema Layer** (`schemas/telemetry.py`)
   - Pydantic v2 models for strict validation
   - Event types: GPS, IMU, AppState, DeliveryAttempt
   - Request/response models with field constraints

4. **Authentication** (`auth/jwt_handler.py`)
   - PyJWT token validation
   - Worker ID extraction from token claims
   - Expiry enforcement (24 hours default)

5. **Kafka Producer** (`kafka/producer.py`)
   - Async producer via aiokafka
   - Topics: `worker_telemetry` (events), `worker_telemetry_dlq` (failures)
   - Graceful startup/shutdown hooks

---

## Validation Rules & Anti-Replay Protection

### Timestamp Validation (Anti-Replay ±5 minutes)

**Rule**: All events must have `timestamp_utc` within ±5 minutes of server time.

**Rationale**: 
- Protects against replay attacks (old events resubmitted)
- Catches clock skew on worker devices
- 5-minute window accommodates network latency and legitimate delays

**Implementation**:
```python
def validate_timestamp(timestamp: datetime) -> bool:
    now = datetime.now(timezone.utc)
    delta = abs((now - timestamp).total_seconds())
    return delta <= 300  # 5 minutes = 300 seconds
```

**Failure**: Event rejected, logged to DLQ with reason

---

### GPS Event Validation

**Required fields** (all must be present):
- `lat` ∈ [-90, 90] (latitude bounds)
- `lon` ∈ [-180, 180] (longitude bounds)
- `accuracy_m` ∈ [0, 500) meters

**Validation chain**:
1. Check field presence
2. Check lat/lon ranges (WGS84 standard)
3. Check accuracy < 500m (precision threshold)
4. Optional: `speed_kmh`, `battery_pct`

**Failure modes**:
- Missing any required field → rejected
- Out-of-range lat/lon → rejected
- accuracy_m ≥ 500m → rejected (poor signal scenarios)

**Example valid GPS event**:
```json
{
  "event_type": "gps",
  "timestamp_utc": "2026-04-13T10:30:00Z",
  "lat": 12.9716,
  "lon": 77.5946,
  "accuracy_m": 15.5,
  "speed_kmh": 25.3,
  "battery_pct": 85
}
```

---

### IMU Event Validation

**Required fields**:
- At least one of: `accel_x`, `accel_y`, `accel_z`, `gyro_x`, `gyro_y`, `gyro_z`

**Dead Sensor Detection**:
- If ALL accel values are exactly `0.0` → reject (indicates sensor failure or mock data)
- Gyro can be zero without rejection

**Rationale**:
- IMU data with all-zero acceleration is physically implausible (violates gravity)
- Common failure mode when sensor is unplugged or not initialized
- Prevents spurious event streams from dead hardware

**Example valid IMU event**:
```json
{
  "event_type": "imu",
  "timestamp_utc": "2026-04-13T10:30:01Z",
  "accel_x": 1.5,
  "accel_y": -2.1,
  "accel_z": 9.81,
  "gyro_x": 0.05,
  "gyro_y": 0.02,
  "gyro_z": -0.01,
  "battery_pct": 82
}
```

**Example invalid IMU event** (rejected):
```json
{
  "event_type": "imu",
  "timestamp_utc": "2026-04-13T10:30:01Z",
  "accel_x": 0.0,
  "accel_y": 0.0,
  "accel_z": 0.0
}
```

---

### App State Event Validation

**Required fields**:
- `app_state` ∈ {`"foreground"`, `"background"`, `"offline"`}

**Rationale**:
- Tracks worker app lifecycle for session correlation
- Foreground/background distinguish active usage from passive monitoring
- Offline state indicates loss of connectivity

---

### Delivery Attempt Event Validation

**Required fields**:
- `delivery_zone_id` (non-empty string)

**Rationale**:
- Correlates events to delivery zones
- Non-empty constraint prevents accidental empty zone IDs

---

## Batch Rejection Logic

### High Failure Rate Threshold (>80%)

**Rule**: If more than 80% of events in a batch fail validation, reject the entire batch and publish to DLQ.

**Rationale**:
- Indicates systemic client error (clock skew, corrupted sensor stream, app bug)
- Prevents partial acceptance of likely-bad data
- Forces client to pause and retry

**Response**: 
- HTTP 422 Unprocessable Entity
- JSON body: `{"detail": "Batch rejected: 85% of events failed validation"}`

**Example scenario** (batch of 10 events):
- 9 events fail timestamp check (old timestamps)
- 1 event passes
- Failure rate = 90% → batch rejected
- DLQ record created with reason and failure breakdown

### Partial Batch Acceptance (<80% failure)

**Rule**: If ≤80% fail, accept valid events and publish failed ones to DLQ for observability.

**Response**: 
- HTTP 202 Accepted
- JSON body: `{"message": "Batch accepted", "total_events": 10, "accepted_count": 8, "rejected_count": 2}`

**Logging**:
- Valid events: published to `worker_telemetry` Kafka topic
- Invalid events: details logged to structlog (event_idx, reason)
- Batch summary: published to DLQ for audit trail

---

## Rate Limiting

**Rule**: 100 requests/min per `worker_id`

**Implementation**: slowapi library with per-key tracking

**Mechanism**:
1. Extract worker_id from JWT token
2. Use slowapi limiter keyed by worker_id
3. Return 429 Too Many Requests if exceeded

**Configuration** (via environment or code):
```python
limiter = Limiter(key_func=lambda request: get_worker_id_from_request(request))
```

---

## Kafka Publishing

### Valid Event Flow

1. Event passes all validation checks
2. Worker ID added to payload (from JWT token)
3. Published to `worker_telemetry` topic with key=worker_id
4. Partition assignment ensures per-worker ordering
5. Downstream Layer 2 consumers process events

**Topic**: `worker_telemetry`

**Key**: `worker_id` (ensures ordering per worker)

**Example Kafka message**:
```json
{
  "worker_id": "worker_123",
  "event_type": "gps",
  "timestamp_utc": "2026-04-13T10:30:00Z",
  "lat": 12.9716,
  "lon": 77.5946,
  "accuracy_m": 15.5,
  "speed_kmh": 25.3,
  "battery_pct": 85
}
```

### Invalid Event Logging

- Invalid events logged to structlog with reason (field missing, out of range, etc.)
- Event index and worker_id included for tracing
- Logged to stderr/log aggregator (not published to Kafka)

### Dead-Letter Queue (DLQ)

**Topic**: `worker_telemetry_dlq`

**Triggers**:
1. Batch-level failure (>80% of events invalid)
2. Individual event validation failure (logged for audit)

**Payload**:
```json
{
  "worker_id": "worker_123",
  "error_reason": "High failure rate (>80%)",
  "batch_summary": {
    "total": 10,
    "invalid": 9,
    "failure_rate": 0.9,
    "invalid_details": [
      {"idx": 0, "reason": "Timestamp too old"},
      {"idx": 1, "reason": "lat out of range"}
    ]
  }
}
```

**Consumer action** (downstream):
- Alert engineering on systematic failures
- Analyze batch patterns to detect client bugs
- Trigger retries for transient failures

---

## Anti-Replay Protection (Detailed)

### Threat Model

**Attacker**: Compromised or malicious worker device sends duplicate telemetry

**Scenario**: GPS event from 2026-04-13 10:30:00 resent multiple times to inflate trip distance or battery drain

### Defense Mechanisms

1. **Timestamp Window (±5 min)**
   - Events from >5 min in past rejected
   - Events from >5 min in future rejected
   - Narrow window prevents replay of stale events

2. **Server-Side Clock Enforcement**
   - Comparison done on server (canonical clock)
   - Client clock skew ≤5 min tolerated

3. **Kafka Downstream Deduplication** (optional, Layer 2)
   - Can implement event ID + timestamp deduplication in consumer
   - Redis cache of (worker_id, event_id, timestamp) tuples
   - TTL matches 6-hour storage in Layer 2

4. **Event Ordering per Worker**
   - Kafka partitioning by worker_id ensures FIFO delivery
   - Layer 2 can detect out-of-order events (monotonic timestamp check)

### Limitations

- Does NOT prevent attack within ±5 min window
- Mitigated by: app-side event ID uniqueness (future enhancement)
- Or: consumer-side deduplication (event hash cache)

---

## Testing Strategy

### Unit Tests (`tests/test_telemetry_api.py`)

1. **Authentication**
   - Missing auth header → 403
   - Expired token → 401
   - Invalid token signature → 401
   - Valid token → 200/202

2. **GPS Event Validation**
   - Valid event → accepted
   - lat out of range [-90,90] → rejected
   - lon out of range [-180,180] → rejected
   - accuracy_m ≥ 500 → rejected
   - Missing lat/lon/accuracy → rejected

3. **IMU Event Validation**
   - Valid event with mixed accel/gyro → accepted
   - All accel values = 0.0 → rejected
   - One accel value ≠ 0.0 → accepted

4. **Timestamp Validation**
   - Current time ±300s → accepted
   - >300s in past → rejected (old)
   - >300s in future → rejected (future)

5. **Batch Rejection**
   - 90% failure rate (9 invalid, 1 valid) → rejected with 422
   - 70% failure rate (3 invalid, 7 valid) → accepted with 202

6. **Rate Limiting**
   - >100 requests/min per worker → 429

### Integration Tests

- Full batch ingestion with Kafka publishing
- DLQ event creation on batch failure  
- Prometheus metrics emission (events/sec, failure rate)

---

## Deployment & Scaling

### Docker Compose (Development)

```bash
docker-compose up -d
# Services: Kafka, Zookeeper, Redis, Telemetry API
```

### Production Considerations

1. **Kafka** → Use managed service (AWS MSK, Confluent Cloud) or HA cluster
2. **Authentication** → Use real JWT secret from secret manager
3. **Rate Limiting** → Backend by distributed cache (Redis) for multi-instance scaling
4. **Metrics** → Prometheus scraper + Grafana dashboards
5. **Logging** → Route structlog JSON to Datadog/Splunk/CloudWatch
6. **Auto-scaling** → Horizontal scaling behind load balancer (stateless API)

---

## API Endpoints Summary

```
POST /v1/telemetry/batch           202 | 422 | 401 | 429     (Batch ingestion, rate limited)
GET  /v1/health                    200                        (Health check)
GET  /v1/metrics                   200                        (Prometheus metrics)
```

---

## Future Enhancements

1. **Event Deduplication**: Client-side event IDs with server-side cache
2. **Batch Compression**: gzip support for large batches
3. **Circuit Breaker**: Graceful degradation if Kafka is unhealthy
4. **Custom Metrics**: Counters for event type distribution, worker accuracy distribution
5. **Replay Attestation**: Digital signatures for security-sensitive events
