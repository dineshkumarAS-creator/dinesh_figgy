# FIGGY Telemetry Ingestion API

Production-ready FastAPI microservice for ingesting worker telemetry data (GPS, IMU, app state, delivery events) with JWT authentication, rate limiting, validation, and Kafka integration.

## Project Structure

```
telemetry_api/
├── main.py                      # FastAPI application, middleware, health/metrics endpoints
├── routers/
│   └── telemetry.py            # POST /v1/telemetry/batch endpoint + validation logic
├── schemas/
│   └── telemetry.py            # Pydantic v2 models for events and requests
├── auth/
│   └── jwt_handler.py          # JWT token creation, validation, worker_id extraction
├── kafka/
│   └── producer.py             # Async Kafka producer initialization & event publishing
├── tests/
│   └── test_telemetry_api.py   # Comprehensive pytest test suite
├── docker-compose.yml          # Kafk, Zookeeper, Redis, API services
├── Dockerfile                  # Production container image
├── requirements.txt            # Python dependencies
├── DESIGN.md                   # Architecture & validation design document
└── README.md                   # This file
```

## Quick Start

### Prerequisites

- Docker & Docker Compose (for full stack)
- Python 3.12+ (for development)

### 1. Run with Docker Compose

```bash
# Start all services (Kafka, Zookeeper, Redis, API)
docker-compose up -d

# API available at http://localhost:8000
# Kafka available at localhost:9092
# Redis available at localhost:6379

# Health check
curl http://localhost:8000/v1/health

# Shutdown
docker-compose down
```

### 2. Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export JWT_SECRET="dev-secret-12345"
export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"

# Run API server
python -m uvicorn telemetry_api.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
pytest telemetry_api/tests/ -v
```

## API Endpoints

### POST /v1/telemetry/batch

Ingest batch of up to 50 telemetry events.

**Authentication**: JWT Bearer token (worker_id embedded in token)

**Rate Limit**: 100 requests/min per worker_id

**Request Body**:
```json
{
  "events": [
    {
      "event_type": "gps",
      "timestamp_utc": "2026-04-13T10:30:00Z",
      "lat": 12.9716,
      "lon": 77.5946,
      "accuracy_m": 15.5,
      "speed_kmh": 25.3,
      "battery_pct": 85
    },
    {
      "event_type": "imu",
      "timestamp_utc": "2026-04-13T10:30:01Z",
      "accel_x": 1.5,
      "accel_y": -2.1,
      "accel_z": 9.81,
      "gyro_x": 0.05,
      "battery_pct": 82
    }
  ]
}
```

**Response** (HTTP 202 Accepted):
```json
{
  "message": "Batch accepted",
  "total_events": 2,
  "accepted_count": 2,
  "rejected_count": 0
}
```

**Error Responses**:
- `401 Unauthorized` - Missing or invalid JWT token
- `422 Unprocessable Entity` - >80% of events failed validation
- `429 Too Many Requests` - Rate limit exceeded (>100 req/min per worker)

### GET /v1/health

Health check endpoint.

**Response** (HTTP 200):
```json
{
  "status": "healthy",
  "timestamp_utc": "2026-04-13T10:30:00Z"
}
```

### GET /v1/metrics

Prometheus-compatible metrics endpoint.

**Response** (HTTP 200):
```json
{
  "active_connections": 5,
  "events_per_sec": 125.3,
  "validation_failure_rate": 0.02
}
```

## JWT Token Usage

### Create Token (CLI)

```bash
python -c "
from telemetry_api.auth.jwt_handler import create_jwt_token
token = create_jwt_token('worker_123')
print(token)
"
```

### Use Token in API Request

```bash
TOKEN="<jwt_token_from_above>"
curl -X POST http://localhost:8000/v1/telemetry/batch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "event_type": "gps",
        "timestamp_utc": "2026-04-13T10:30:00Z",
        "lat": 12.9716,
        "lon": 77.5946,
        "accuracy_m": 15.5
      }
    ]
  }'
```

## Validation Rules

### GPS Events

- **Required fields**: `lat`, `lon`, `accuracy_m`
- **Lat range**: [-90, 90]
- **Lon range**: [-180, 180]
- **Accuracy**: < 500 meters
- **Timestamp**: within ±5 minutes of server time

### IMU Events

- **At least one**: `accel_x/y/z` or `gyro_x/y/z`
- **Dead sensor rejection**: All accel values exactly 0.0 → rejected
- **Timestamp**: within ±5 minutes of server time

### App State Events

- **Required**: `app_state` in {`"foreground"`, `"background"`, `"offline"`}
- **Timestamp**: within ±5 minutes of server time

### Delivery Attempt Events

- **Required**: non-empty `delivery_zone_id`
- **Timestamp**: within ±5 minutes of server time

### Batch-Level Rules

- **Max events**: 50 per batch
- **Max failures**: 80% (if >80% fail, batch rejected with HTTP 422)
- **Valid events**: Published to Kafka topic `worker_telemetry`
- **Failed events**: Logged to structlog, optionally published to DLQ `worker_telemetry_dlq`

## Event Publishing

### Valid Events

Published to Kafka topic `worker_telemetry` with:
- **Key**: `worker_id` (ensures per-worker ordering)
- **Value**: JSON-serialized event payload with worker_id added

### Invalid Events

- Logged to structlog with reason
- Not published to Kafka
- Included in batch summary if batch is accepted

### Dead-Letter Queue (DLQ)

Published to Kafka topic `worker_telemetry_dlq` when:
- Batch >80% failure rate
- Contains: worker_id, error_reason, batch_summary with details

## Testing

### Run Test Suite

```bash
pytest telemetry_api/tests/ -v

# With coverage
pytest telemetry_api/tests/ --cov=telemetry_api
```

### Test Coverage

- ✓ Authentication (valid/expired/invalid tokens)
- ✓ GPS event validation (all fields, ranges, anti-replay)
- ✓ IMU event validation (dead sensor detection)
- ✓ Timestamp validation (±5 minute window)
- ✓ Batch rejection logic (>80% failure rate)
- ✓ Rate limiting
- ✓ Health check & metrics endpoints

## Kafka Topics

### worker_telemetry

Valid events published here for downstream processing (Layer 2).

**Schema**:
```json
{
  "worker_id": "worker_123",
  "event_type": "gps",
  "timestamp_utc": "2026-04-13T10:30:00Z",
  "lat": 12.9716,
  "lon": 77.5946,
  "accuracy_m": 15.5,
  ...
}
```

### worker_telemetry_dlq

Dead-letter events for:
- Batch-level failures (>80% invalid)
- Observability on failed batches

**Schema**:
```json
{
  "worker_id": "worker_123",
  "error_reason": "High failure rate (>80%)",
  "batch_summary": {
    "total": 10,
    "invalid": 9,
    "failure_rate": 0.9,
    "invalid_details": [...]
  }
}
```

## Configuration

### Environment Variables

```bash
# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# JWT
JWT_SECRET=your-secret-key-here

# Redis (for rate limiting, future enhancement)
REDIS_URL=redis://localhost:6379/0
```

### JWT Token Expiry

Default: 24 hours (configurable in `auth/jwt_handler.py`)

## Monitoring

### Prometheus Metrics

- Active connections
- Events published per second
- Validation failure rate
- HTTP request latency

Access at: `http://localhost:8000/metrics` (prometheus-client format)

### Structured Logging

All events logged to structlog in JSON format:
- HTTP requests (method, path, status, duration)
- Telemetry events (accepted/rejected)
- Kafka publishing status
- Errors and warnings

## Production Deployment

### Key Considerations

1. **JWT Secret**: Use long, random secret from secret manager
2. **HTTPS**: Deploy behind reverse proxy (nginx/Envoy) with TLS
3. **Rate Limiting**: Use Redis-backed limiter for multi-instance scaling
4. **Kafka**: Use managed service (AWS MSK, Confluent Cloud) or HA cluster
5. **Logging**: Route structlog JSON to log aggregator (Datadog, Splunk)
6. **Monitoring**: Set up Prometheus scrape + Grafana dashboards
7. **Auto-scaling**: Horizontal scaling behind load balancer (stateless)

### Docker Production Build

```bash
docker build -t figgy-telemetry-api:1.0 -f telemetry_api/Dockerfile .
docker push <registry>/figgy-telemetry-api:1.0

# Deploy with:
# - 3+ replicas behind load balancer
# - Health checks every 30 seconds
# - Graceful shutdown (30s drain time)
```

## Troubleshooting

### Connection to Kafka Failed

```bash
# Check Kafka health
docker ps | grep kafka
docker logs <kafka_container>

# Verify bootstrap address
echo "KAFKA_BOOTSTRAP_SERVERS: $KAFKA_BOOTSTRAP_SERVERS"
```

### JWT Token Verification Failed

```bash
# Verify JWT_SECRET is set
echo $JWT_SECRET

# Recreate token with correct secret
python -c "from telemetry_api.auth.jwt_handler import create_jwt_token; print(create_jwt_token('worker_test'))"
```

### Rate Limit Always Triggered

Ensure each unique worker_id generates unique tokens. Rate limiting is per `worker_id`, not per IP.

## Design Documentation

See [DESIGN.md](DESIGN.md) for:
- Validation rule rationale
- Anti-replay protection strategy
- Batch rejection logic
- Dead-letter queue design
- Kafka schema and publishing strategy

---

**Version**: 1.0.0  
**Last Updated**: April 13, 2026  
**Maintainer**: FIGGY Platform Team
