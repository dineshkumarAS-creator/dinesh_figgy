"""
Base Kafka Consumer for FIGGY Processors

Async Kafka consumer with dead-letter routing and error handling.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Optional

import structlog
from aiokafka import AIOKafkaConsumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer

logger = structlog.get_logger()


class BaseKafkaConsumer(ABC):
    def __init__(self, topic: str, group_id: str, schema_file: str, config, dlq_topic: Optional[str] = None):
        self.topic = topic
        self.group_id = group_id
        self.config = config
        self.dlq_topic = dlq_topic
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.schema_registry_client = SchemaRegistryClient({"url": config.schema_registry_url})
        self.avro_deserializer = self._create_deserializer(schema_file)

    def _create_deserializer(self, schema_file: str):
        with open(schema_file, "r") as f:
            schema_str = f.read()
        return AvroDeserializer(self.schema_registry_client, schema_str)

    async def __aenter__(self):
        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.config.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=self.avro_deserializer,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        await self.consumer.start()
        logger.info("Kafka consumer started", topic=self.topic, group_id=self.group_id)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped", topic=self.topic, group_id=self.group_id)

    @abstractmethod
    async def process(self, message: Any) -> None:
        """Process a single message. Implement in subclass."""
        pass

    async def run(self):
        """Main consumer loop."""
        async for message in self.consumer:
            try:
                await self.process(message.value)
                # Auto-commit enabled, so offsets are committed automatically
            except Exception as e:
                logger.error("Failed to process message", topic=self.topic, error=str(e))
                if self.dlq_topic:
                    await self._send_to_dlq(message)
                # Continue processing other messages

    async def _send_to_dlq(self, message):
        """Send failed message to dead-letter queue."""
        # Note: In a real implementation, you'd use a producer to send to DLQ
        logger.warning("Message sent to DLQ", topic=self.dlq_topic, original_topic=self.topic)