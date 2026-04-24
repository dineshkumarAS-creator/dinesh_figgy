"""
Verification Challenge Factory and Models

Creates and manages location-based verification challenges for workers.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import redis.asyncio as aioredis
import structlog

from schemas import VerificationChallenge
from soft_verify import get_zone_config

logger = structlog.get_logger()


class ChallengeFactory:
    """Creates and stores verification challenges."""

    def __init__(self, redis_url: str, timeout_minutes: int = 30):
        """
        Initialize challenge factory.

        Args:
            redis_url: Redis connection URL
            timeout_minutes: Challenge expiry time (default 30 min)
        """
        self.redis_url = redis_url
        self.timeout_minutes = timeout_minutes
        self.redis: Optional[aioredis.Redis] = None
        self.zone_config = get_zone_config()

    async def initialize(self) -> None:
        """Initialize Redis connection."""
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
        logger.info("ChallengeFactory initialized")

    async def shutdown(self) -> None:
        """Shutdown Redis connection."""
        if self.redis:
            await self.redis.close()

    async def create_location_challenge(
        self,
        claim_id: str,
        worker_id: str,
        zone_id: str,
        location_tolerance_km: float = 2.0,
    ) -> VerificationChallenge:
        """
        Create a location ping challenge.

        Args:
            claim_id: Associated claim ID
            worker_id: Worker to challenge
            zone_id: Expected zone ID
            location_tolerance_km: Tolerance radius in km

        Returns:
            VerificationChallenge instance
        """
        challenge_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self.timeout_minutes)

        # Get zone bounds from config
        try:
            lat_range, lon_range = self.zone_config.get_zone_bounds(zone_id)
        except ValueError:
            logger.error("zone_not_found", zone_id=zone_id)
            raise

        challenge = VerificationChallenge(
            challenge_id=challenge_id,
            claim_id=claim_id,
            worker_id=worker_id,
            challenge_type="location_ping",
            issued_at=now,
            expires_at=expires_at,
            expected_zone_id=zone_id,
            expected_lat_range=lat_range,
            expected_lon_range=lon_range,
            location_tolerance_km=location_tolerance_km,
            status="pending",
        )

        # Store in Redis
        await self._store_challenge(challenge)

        logging_dict = challenge.model_dump()
        logging_dict["expires_at"] = expires_at.isoformat()
        logging_dict["issued_at"] = now.isoformat()

        logger.info(
            "challenge_created",
            challenge_id=challenge_id,
            worker_id=worker_id,
            claim_id=claim_id,
            zone_id=zone_id,
        )

        return challenge

    async def _store_challenge(self, challenge: VerificationChallenge) -> None:
        """Store challenge in Redis with TTL."""
        redis_key = f"soft_verify_challenge:{challenge.challenge_id}"
        ttl_seconds = int((challenge.expires_at - challenge.issued_at).total_seconds()) + 300  # +5 min buffer

        challenge_json = challenge.model_dump_json()
        await self.redis.setex(redis_key, ttl_seconds, challenge_json)

        # Also index by worker for quick lookup
        worker_key = f"worker_pending_challenge:{challenge.worker_id}"
        await self.redis.setex(worker_key, ttl_seconds, challenge.challenge_id)

        logger.debug(
            "challenge_stored_redis",
            challenge_id=challenge.challenge_id,
            ttl_seconds=ttl_seconds,
        )

    async def get_challenge(self, challenge_id: str) -> Optional[VerificationChallenge]:
        """Retrieve challenge from Redis."""
        redis_key = f"soft_verify_challenge:{challenge_id}"
        challenge_json = await self.redis.get(redis_key)

        if not challenge_json:
            logger.warning("challenge_not_found", challenge_id=challenge_id)
            return None

        try:
            challenge_dict = json.loads(challenge_json)
            return VerificationChallenge(**challenge_dict)
        except Exception as e:
            logger.error("challenge_deserialize_error", error=str(e))
            return None

    async def get_worker_pending_challenge(
        self, worker_id: str
    ) -> Optional[VerificationChallenge]:
        """Get active pending challenge for a worker."""
        worker_key = f"worker_pending_challenge:{worker_id}"
        challenge_id = await self.redis.get(worker_key)

        if not challenge_id:
            return None

        return await self.get_challenge(challenge_id)

    async def update_challenge_status(
        self,
        challenge_id: str,
        status: str,
        response_data: Optional[dict] = None,
        evaluated_at: Optional[datetime] = None,
    ) -> Optional[VerificationChallenge]:
        """Update challenge status and store response."""
        challenge = await self.get_challenge(challenge_id)
        if not challenge:
            return None

        # Update challenge
        challenge.status = status
        if response_data:
            challenge.response_data = response_data
        if evaluated_at:
            challenge.evaluated_at = evaluated_at

        # Re-store in Redis (with reduced TTL if completed)
        redis_key = f"soft_verify_challenge:{challenge.challenge_id}"
        if status in ["passed", "failed", "expired"]:
            # Keep for 24 hours for audit
            await self.redis.setex(
                redis_key, 86400, challenge.model_dump_json()
            )
        else:
            # Extend TTL if still pending
            ttl_seconds = int(
                (challenge.expires_at - challenge.issued_at).total_seconds()
            ) + 300
            await self.redis.setex(redis_key, ttl_seconds, challenge.model_dump_json())

        logger.info(
            "challenge_status_updated",
            challenge_id=challenge_id,
            status=status,
        )

        return challenge
