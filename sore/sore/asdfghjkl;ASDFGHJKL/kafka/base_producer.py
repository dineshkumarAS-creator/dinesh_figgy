"""
Base Kafka Producer for FIGGY Connectors

Async Kafka producer with schema registry support, metrics, and error handling.
"""

import asyncio
import json
import time
from abc import ABC
from typing import Any, Optional

import structlog
from aiokafka import AIOKafkaProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from prometheus_client import Counter, Histogram

logger = structlog.get_logger()

# Prometheus metrics
MESSAGES_PUBLISHED = Counter(
    "kafka_messages_published_total",
    "Total number of messages published to Kafka",
    ["topic"]
)
PUBLISH_LATENCY = Histogram(
    "kafka_publish_latency_seconds",
    "Latency of Kafka publish operations",
    ["topic"]
)


class BaseKafkaProducer(ABC):
    def __init__(self, topic: str, schema_file: str, config):
        self.topic = topic
        self.config = config
        self.producer: Optional[AIOKafkaProducer] = None
        self.schema_registry_client = SchemaRegistryClient({"url": config.schema_registry_url})
        self.avro_serializer = self._create_serializer(schema_file)

    def _create_serializer(self, schema_file: str):
        with open(schema_file, "r") as f:
            schema_str = f.read()
        return AvroSerializer(self.schema_registry_client, schema_str)

    async def __aenter__(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.config.bootstrap_servers,
            value_serializer=self.avro_serializer,
        )
        await self.producer.start()
        logger.info("Kafka producer started", topic=self.topic)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped", topic=self.topic)

    async def publish(self, key: str, value: dict) -> None:
        """Publish a message to Kafka with schema validation and metrics."""
        start_time = time.time()

        try:
            await self.producer.send_and_wait(
                self.topic,
                key=key.encode("utf-8"),
                value=value
            )

            latency = time.time() - start_time
            MESSAGES_PUBLISHED.labels(topic=self.topic).inc()
            PUBLISH_LATENCY.labels(topic=self.topic).observe(latency)

            logger.debug("Message published", topic=self.topic, key=key)

        except Exception as e:
            logger.error("Failed to publish message", topic=self.topic, key=key, error=str(e))
            raise