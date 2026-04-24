"""
Centralized Kafka Configuration for FIGGY

Loads configuration from environment variables with sensible defaults.
"""

import os
from typing import Dict, Any


class KafkaConfig:
    def __init__(self):
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.schema_registry_url = os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081")

        # Topic names
        self.topics = {
            "weather": "weather",
            "aqi": "aqi",
            "events": "events",
            "worker_telemetry": "worker_telemetry",
            "weather_dlq": "weather_dlq",
            "aqi_dlq": "aqi_dlq",
            "events_dlq": "events_dlq",
            "worker_telemetry_dlq": "worker_telemetry_dlq",
        }

    def get_producer_config(self) -> Dict[str, Any]:
        return {
            "bootstrap.servers": self.bootstrap_servers,
            "acks": "all",
            "retries": 3,
            "retry.backoff.ms": 100,
            "enable.idempotence": True,
        }

    def get_consumer_config(self, group_id: str) -> Dict[str, Any]:
        return {
            "bootstrap.servers": self.bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
            "auto.commit.interval.ms": 1000,
        }


# Global config instance
config = KafkaConfig()