#!/usr/bin/env python3
"""
Schema Registration Script for FIGGY Kafka Topics

Registers Avro schemas for all topics with BACKWARD compatibility.
"""

import json
import logging
from pathlib import Path
from confluent_kafka.schema_registry import SchemaRegistryClient, Schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCHEMA_REGISTRY_URL = "http://localhost:8081"
SUBJECT_STRATEGY = "TopicNameStrategy"

SCHEMAS = [
    ("weather", "weather.avsc"),
    ("aqi", "aqi.avsc"),
    ("events", "events.avsc"),
    ("worker_telemetry", "telemetry.avsc"),
]


def register_schemas():
    sr_client = SchemaRegistryClient({"url": SCHEMA_REGISTRY_URL})

    for topic, schema_file in SCHEMAS:
        schema_path = Path(__file__).parent / schema_file
        with open(schema_path, "r") as f:
            schema_str = f.read()

        schema = Schema(schema_str, "AVRO")

        subject = f"{topic}-value"

        try:
            # Check if schema already exists
            versions = sr_client.get_versions(subject)
            if versions:
                logger.info(f"Schema for {subject} already exists, skipping")
                continue

            # Register new schema
            schema_id = sr_client.register_schema(subject, schema, compatibility="BACKWARD")
            logger.info(f"Registered schema for {subject} with ID: {schema_id}")

        except Exception as e:
            logger.error(f"Failed to register schema for {subject}: {e}")


if __name__ == "__main__":
    register_schemas()