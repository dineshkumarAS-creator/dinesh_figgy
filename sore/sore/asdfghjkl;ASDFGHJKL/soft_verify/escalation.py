"""
Challenge Escalation Manager

Handles scheduled escalation of expired unresponded challenges to manual review.
"""

import json
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis
import structlog
from aiokafka import AIOKafkaProducer

from schemas import SoftVerifyResult
from soft_verify.challenge import ChallengeFactory

logger = structlog.get_logger()


class EscalationManager:
    """Manages escalation of unresponded challenges to manual review."""

    def __init__(
        self,
        redis_url: str,
        kafka_bootstrap_servers: str,
        challenge_factory: ChallengeFactory,
    ):
        """
        Initialize escalation manager.

        Args:
            redis_url: Redis connection URL
            kafka_bootstrap_servers: Kafka bootstrap servers
            challenge_factory: Challenge factory instance for lookups
        """
        self.redis_url = redis_url
        self.kafka_servers = kafka_bootstrap_servers.split(",")
        self.challenge_factory = challenge_factory

        self.redis: Optional[aioredis.Redis] = None
        self.producer: Optional[AIOKafkaProducer] = None

        # Metrics
        self.challenges_escalated = 0
        self.reminders_sent = 0

    async def initialize(self) -> None:
        """Initialize connections."""
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.kafka_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        await self.producer.start()
        logger.info("EscalationManager initialized")

    async def shutdown(self) -> None:
        """Shutdown connections."""
        if self.producer:
            await self.producer.stop()
        if self.redis:
            await self.redis.close()

    async def escalate_expired_challenges(self) -> None:
        """
        Scan for expired challenges without responses and escalate to manual review.

        Runs every 2 minutes (scheduled via APScheduler).

        Steps:
        1. Scan Redis keys: worker_pending_challenge:*
        2. For each, check if challenge expired and not responded
        3. Mark status = "expired"
        4. Publish SoftVerifyResult with recommendation = "manual_review"
        5. Log escalation
        """
        pattern = "worker_pending_challenge:*"
        cursor = 0
        expired_count = 0

        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)

            for key in keys:
                try:
                    challenge_id = await self.redis.get(key)
                    if not challenge_id:
                        continue

                    challenge = await self.challenge_factory.get_challenge(challenge_id)
                    if not challenge:
                        continue

                    now = datetime.now(timezone.utc)
                    if challenge.status == "pending" and now > challenge.expires_at:
                        # Escalate this challenge
                        await self._escalate_challenge(challenge)
                        expired_count += 1

                except Exception as e:
                    logger.error("escalation_check_error", error=str(e), key=key)

            if cursor == 0:
                break

        if expired_count > 0:
            logger.info(
                "escalation_cycle_complete",
                expired_count=expired_count,
            )

    async def _escalate_challenge(self, challenge) -> None:
        """Escalate single expired challenge to manual review."""
        now = datetime.now(timezone.utc)

        # Update challenge status
        await self.challenge_factory.update_challenge_status(
            challenge_id=challenge.challenge_id,
            status="expired",
            evaluated_at=now,
        )

        # Publish escalation event
        result = SoftVerifyResult(
            claim_id=challenge.claim_id,
            worker_id=challenge.worker_id,
            challenge_id=challenge.challenge_id,
            passed=False,
            recommendation="manual_review",
            distance_km=0.0,
            timing_score=0.0,
            responded_at=None,
            evaluated_at=now,
        )

        await self.producer.send_and_wait(
            "soft_verify_results",
            result.model_dump(),
        )

        self.challenges_escalated += 1

        logger.warning(
            "challenge_escalated",
            challenge_id=challenge.challenge_id,
            worker_id=challenge.worker_id,
            claim_id=challenge.claim_id,
            reason="no_response",
        )

    async def send_reminder_notification(
        self, challenge_id: str, notifier
    ) -> bool:
        """
        Send reminder notification at 20-minute mark.

        Only sent once per challenge (tracked in Redis).

        Args:
            challenge_id: Challenge to remind for
            notifier: WorkerNotifier instance

        Returns:
            True if reminder sent
        """
        # Check if already sent
        reminder_key = f"soft_verify_reminder_sent:{challenge_id}"
        reminder_sent = await self.redis.get(reminder_key)
        if reminder_sent:
            return False

        # Get challenge
        challenge = await self.challenge_factory.get_challenge(challenge_id)
        if not challenge or challenge.status != "pending":
            return False

        # Send reminder
        try:
            success = await notifier.send_verification_request(
                challenge.worker_id, challenge
            )

            if success:
                # Mark reminder sent
                await self.redis.setex(reminder_key, 86400, "true")
                self.reminders_sent += 1
                logger.info(
                    "reminder_sent",
                    challenge_id=challenge_id,
                    worker_id=challenge.worker_id,
                )
                return True

        except Exception as e:
            logger.error(
                "reminder_send_error",
                challenge_id=challenge_id,
                error=str(e),
            )

        return False

    def get_metrics(self) -> dict:
        """Return escalation metrics."""
        return {
            "challenges_escalated": self.challenges_escalated,
            "reminders_sent": self.reminders_sent,
        }
