import time
from datetime import datetime, timezone

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from telemetry_api.kafka.producer import close_producer, init_producer
from telemetry_api.routers import telemetry
from telemetry_api.schemas.telemetry import HealthCheckResponse, MetricsResponse

logger = structlog.get_logger()

# Initialize FastAPI app
app = FastAPI(
    title="FIGGY Telemetry Ingestion API",
    description="Worker telemetry data ingestion service",
    version="1.0.0",
)

# Rate limiter is defined in the telemetry router for worker_id keying
app.state.limiter = telemetry.limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    logger.warning("rate_limit_exceeded", client=get_remote_address(request))
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Max 100 requests/min per worker."},
    )


active_requests = 0

# Structured logging middleware and active connection tracking
@app.middleware("http")
async def log_requests(request: Request, call_next):
    global active_requests
    active_requests += 1
    start_time = time.time()
    try:
        response = await call_next(request)
    finally:
        active_requests -= 1
    duration = time.time() - start_time
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=int(duration * 1000),
    )
    return response


# Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Include routers
app.include_router(telemetry.router)


@app.on_event("startup")
async def startup():
    logger.info("telemetry_api_startup")
    await init_producer()


@app.on_event("shutdown")
async def shutdown():
    logger.info("telemetry_api_shutdown")
    await close_producer()


@app.get("/v1/health")
async def health_check() -> HealthCheckResponse:
    """Health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        timestamp_utc=datetime.now(timezone.utc),
    )


@app.get("/v1/metrics")
async def get_metrics() -> MetricsResponse:
    """Prometheus-style metrics endpoint."""
    metrics = telemetry.get_metrics()
    return MetricsResponse(
        active_connections=active_requests,
        events_per_sec=metrics["events_per_sec"],
        validation_failure_rate=metrics["validation_failure_rate"],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
