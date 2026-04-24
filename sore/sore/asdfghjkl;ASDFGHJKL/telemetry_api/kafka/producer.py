import json
import os
from typing import Any, Optional

import structlog
from aiokafka import AIOKafkaProducer

logger = structlog.get_logger()

_producer: Optional[AIOKafkaProducer] = None

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TELEMETRY_TOPIC = "worker_telemetry"
DLQ_TOPIC = "worker_telemetry_dlq"


async def init_producer() -> AIOKafkaProducer:
    """Initialize Kafka producer."""
    global _producer
    _producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(","))
    await _producer.start()
    logger.info("kafka_producer_started", bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    return _producer


async def close_producer() -> None:
    """Close Kafka producer."""
    global _producer
    if _producer:
        await _producer.stop()
        logger.info("kafka_producer_stopped")


def get_producer() -> AIOKafkaProducer:
    """Get the current Kafka producer instance."""
    global _producer
    if _producer is None:
        raise RuntimeError("Kafka producer not initialized. Call init_producer() first.")
    return _producer


async def publish_telemetry_event(worker_id: str, event: dict[str, Any]) -> None:
    """Publish a telemetry event to Kafka."""
    producer = get_producer()
    key = worker_id.encode("utf-8")
    value = json.dumps(event, default=str).encode("utf-8")
    try:
        await producer.send_and_wait(TELEMETRY_TOPIC, key=key, value=value)
        logger.debug("telemetry_event_published", worker_id=worker_id, event_type=event.get("event_type"))
    except Exception as exc:
        logger.error("telemetry_publish_failed", error=str(exc), worker_id=worker_id)
        raise


async def publish_dlq_event(worker_id: str, error_reason: str, batch_summary: dict[str, Any]) -> None:
    """Publish batch error to dead-letter queue."""
    producer = get_producer()
    key = worker_id.encode("utf-8")
    payload = {
        "worker_id": worker_id,
        "error_reason": error_reason,
        "batch_summary": batch_summary,
    }
    value = json.dumps(payload, default=str).encode("utf-8")
    try:
        await producer.send_and_wait(DLQ_TOPIC, key=key, value=value)
        logger.warning("dlq_event_published", worker_id=worker_id, reason=error_reason)
    except Exception as exc:
        logger.error("dlq_publish_failed", error=str(exc), worker_id=worker_id)
