"""
Publisher

Publishes composite claim scores and routing decisions to Kafka and Redis.
"""

import json
from typing import Optional

import aioredis
import structlog
from aiokafka import AIOKafkaProducer

from schemas import CompositeClaimScore, RoutingDecision

logger = structlog.get_logger()


class ScorePublisher:
    """Publishes scores and decisions to Kafka and Redis."""

    def __init__(self, kafka_bootstrap_servers: str, redis_url: str):
        """
        Initialize publisher.

        Args:
            kafka_bootstrap_servers: Kafka bootstrap servers
            redis_url: Redis connection URL
        """
        self.kafka_servers = kafka_bootstrap_servers.split(",")
        self.redis_url = redis_url

        self.producer: Optional[AIOKafkaProducer] = None
        self.redis: Optional[aioredis.Redis] = None

        # Metrics
        self.composite_scores_published = 0
        self.routing_decisions_published = 0

    async def start(self) -> None:
        """Connect to Kafka and Redis."""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.kafka_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        await self.producer.start()

        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
        logger.info("ScorePublisher started")

    async def stop(self) -> None:
        """Disconnect from Kafka and Redis."""
        if self.producer:
            await self.producer.stop()
        if self.redis:
            await self.redis.close()
        logger.info("ScorePublisher stopped")

    async def publish_composite_score(self, score: CompositeClaimScore) -> None:
        """
        Publish composite claim score to Kafka and Redis.

        Kafka topic: "composite_scores"
        Redis key: composite_score:latest:{worker_id}, TTL 30 min
        """
        # Publish to Kafka
        await self.producer.send_and_wait(
            "composite_scores",
            score.model_dump(),
        )

        # Store in Redis
        redis_key = f"composite_score:latest:{score.worker_id}"
        await self.redis.setex(
            redis_key,
            1800,  # 30 minutes
            score.model_dump_json(),
        )

        self.composite_scores_published += 1
        logger.info(
            "composite_score_published",
            worker_id=score.worker_id,
            minute_bucket=score.minute_bucket,
            composite_claim_score=score.composite_claim_score,
            confidence_level=score.confidence_level,
        )

    async def publish_routing_decision(self, decision: RoutingDecision) -> None:
        """
        Publish routing decision to Kafka and Redis.

        Kafka topic: "routing_decisions"
        Redis key: routing_decision:latest:{worker_id}, TTL 30 min
        """
        # Publish to Kafka
        await self.producer.send_and_wait(
            "routing_decisions",
            decision.model_dump(),
        )

        # Store in Redis
        redis_key = f"routing_decision:latest:{decision.worker_id}"
        await self.redis.setex(
            redis_key,
            1800,  # 30 minutes
            decision.model_dump_json(),
        )

        self.routing_decisions_published += 1
        logger.info(
            "routing_decision_published",
            worker_id=decision.worker_id,
            minute_bucket=decision.minute_bucket,
            route=decision.route,
            routing_reason=decision.routing_reason,
        )

    def get_metrics(self) -> dict:
        """Return publishing metrics."""
        return {
            "composite_scores_published": self.composite_scores_published,
            "routing_decisions_published": self.routing_decisions_published,
        }
