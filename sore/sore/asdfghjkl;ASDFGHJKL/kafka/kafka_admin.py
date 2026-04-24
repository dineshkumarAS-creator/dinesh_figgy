#!/usr/bin/env python3
"""
Kafka Admin Script for FIGGY Layer 1 Data Pipeline

Creates all required Kafka topics with proper configurations.
Idempotent - skips creation if topic already exists.

Usage:
    python kafka_admin.py --bootstrap-servers localhost:9092
"""

import argparse
import logging
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import KafkaException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOPICS = [
    {
        "name": "weather",
        "partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": str(24 * 60 * 60 * 1000),  # 24 hours
            "cleanup.policy": "delete"
        }
    },
    {
        "name": "aqi",
        "partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": str(24 * 60 * 60 * 1000),  # 24 hours
        }
    },
    {
        "name": "events",
        "partitions": 6,
        "replication_factor": 1,
        "config": {
            "retention.ms": str(72 * 60 * 60 * 1000),  # 72 hours
        }
    },
    {
        "name": "worker_telemetry",
        "partitions": 12,
        "replication_factor": 1,
        "config": {
            "retention.ms": str(6 * 60 * 60 * 1000),  # 6 hours
        }
    },
    {
        "name": "weather_dlq",
        "partitions": 1,
        "replication_factor": 1,
        "config": {
            "retention.ms": str(7 * 24 * 60 * 60 * 1000),  # 7 days
        }
    },
    {
        "name": "aqi_dlq",
        "partitions": 1,
        "replication_factor": 1,
        "config": {
            "retention.ms": str(7 * 24 * 60 * 60 * 1000),  # 7 days
        }
    },
    {
        "name": "events_dlq",
        "partitions": 1,
        "replication_factor": 1,
        "config": {
            "retention.ms": str(7 * 24 * 60 * 60 * 1000),  # 7 days
        }
    },
    {
        "name": "worker_telemetry_dlq",
        "partitions": 1,
        "replication_factor": 1,
        "config": {
            "retention.ms": str(7 * 24 * 60 * 60 * 1000),  # 7 days
        }
    },
    # Normalised topics
    {
        "name": "weather_normalised",
        "partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": str(24 * 60 * 60 * 1000),  # 24 hours
        }
    },
    {
        "name": "aqi_normalised",
        "partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": str(24 * 60 * 60 * 1000),  # 24 hours
        }
    },
    {
        "name": "telemetry_normalised",
        "partitions": 12,
        "replication_factor": 1,
        "config": {
            "retention.ms": str(6 * 60 * 60 * 1000),  # 6 hours
        }
    },
]


def create_topics(bootstrap_servers: str):
    admin_client = AdminClient({'bootstrap.servers': bootstrap_servers})

    # Check existing topics
    cluster_metadata = admin_client.list_topics(timeout=10)
    existing_topics = set(cluster_metadata.topics.keys())

    topics_to_create = []
    for topic in TOPICS:
        if topic["name"] not in existing_topics:
            new_topic = NewTopic(
                topic["name"],
                num_partitions=topic["partitions"],
                replication_factor=topic["replication_factor"],
                config=topic["config"]
            )
            topics_to_create.append(new_topic)
            logger.info(f"Will create topic: {topic['name']}")
        else:
            logger.info(f"Topic {topic['name']} already exists, skipping")

    if not topics_to_create:
        logger.info("All topics already exist")
        return

    # Create topics
    futures = admin_client.create_topics(topics_to_create)

    for topic_name, future in futures.items():
        try:
            future.result()  # Wait for completion
            logger.info(f"Successfully created topic: {topic_name}")
        except KafkaException as e:
            logger.error(f"Failed to create topic {topic_name}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Kafka topics for FIGGY")
    parser.add_argument("--bootstrap-servers", required=True, help="Kafka bootstrap servers")
    args = parser.parse_args()

    create_topics(args.bootstrap_servers)