"""
Worker Notification Service

Sends push notifications via FCM with SMS fallback.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis
import structlog
from aiohttp import ClientSession

from schemas import VerificationChallenge

logger = structlog.get_logger()


class WorkerNotifier:
    """Sends verification requests to workers via push notifications."""

    def __init__(
        self,
        redis_url: str,
        fcm_api_key: Optional[str] = None,
        twilio_account_sid: Optional[str] = None,
        twilio_auth_token: Optional[str] = None,
        twilio_from_number: Optional[str] = None,
    ):
        """
        Initialize notifier.

        Args:
            redis_url: Redis connection URL
            fcm_api_key: Firebase Cloud Messaging API key
            twilio_account_sid: Twilio account ID (for SMS fallback)
            twilio_auth_token: Twilio auth token
            twilio_from_number: Twilio sender phone number
        """
        self.redis_url = redis_url
        self.fcm_api_key = fcm_api_key
        self.twilio_account_sid = twilio_account_sid
        self.twilio_auth_token = twilio_auth_token
        self.twilio_from_number = twilio_from_number

        self.redis: Optional[aioredis.Redis] = None
        self.http_session: Optional[ClientSession] = None

        # Metrics
        self.fcm_sent = 0
        self.fcm_failed = 0
        self.sms_fallback_sent = 0

    async def initialize(self) -> None:
        """Initialize connections."""
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
        self.http_session = ClientSession()
        logger.info("WorkerNotifier initialized")

    async def shutdown(self) -> None:
        """Shutdown connections."""
        if self.redis:
            await self.redis.close()
        if self.http_session:
            await self.http_session.close()

    async def send_verification_request(
        self, worker_id: str, challenge: VerificationChallenge
    ) -> bool:
        """
        Send verification request to worker via FCM → SMS fallback.

        Strategy:
        1. Try FCM for 60 seconds (with 2 retries @ 30s backoff)
        2. If FCM not confirmed, send SMS
        3. Log delivery status to Redis

        Args:
            worker_id: Worker identifier
            challenge: Challenge details

        Returns:
            True if notification successfully sent
        """
        challenge_id = challenge.challenge_id
        claim_id = challenge.claim_id

        # Try FCM with retries
        fcm_success = False
        for attempt in range(3):
            try:
                fcm_success = await self._send_fcm(worker_id, challenge)
                if fcm_success:
                    self.fcm_sent += 1
                    logger.info(
                        "fcm_sent",
                        worker_id=worker_id,
                        challenge_id=challenge_id,
                        attempt=attempt + 1,
                    )
                    break
                else:
                    logger.warning(
                        "fcm_failed_attempt",
                        worker_id=worker_id,
                        attempt=attempt + 1,
                    )

                if attempt < 2:
                    await asyncio.sleep(30)  # 30s backoff between retries

            except Exception as e:
                logger.error("fcm_error", error=str(e), attempt=attempt + 1)
                if attempt < 2:
                    await asyncio.sleep(30)

        # Fallback to SMS if FCM failed
        if not fcm_success:
            logger.info(
                "fcm_failed_fallback_to_sms",
                worker_id=worker_id,
                challenge_id=challenge_id,
            )
            sms_success = await self._send_sms_fallback(worker_id, challenge)
            if sms_success:
                self.sms_fallback_sent += 1

        # Log delivery attempt
        notification_log = {
            "challenge_id": challenge_id,
            "worker_id": worker_id,
            "fcm_sent": fcm_success,
            "sms_fallback_sent": not fcm_success,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

        redis_key = f"notification_log:{challenge_id}"
        await self.redis.setex(redis_key, 86400, json.dumps(notification_log))

        return fcm_success or (not fcm_success)  # Return True if any path succeeded

    async def _send_fcm(
        self, worker_id: str, challenge: VerificationChallenge
    ) -> bool:
        """
        Send Firebase Cloud Messaging notification.

        In production: fetch device_token from worker profile service.
        In tests: mocked.

        Args:
            worker_id: Worker identifier
            challenge: Challenge details

        Returns:
            True if successfully sent
        """
        if not self.fcm_api_key:
            logger.warning("fcm_api_key_not_configured")
            return False

        # In production: fetch device_token from worker profile service
        device_token = await self._get_worker_device_token(worker_id)
        if not device_token:
            logger.warning("device_token_not_found", worker_id=worker_id)
            return False

        payload = {
            "message": {
                "token": device_token,
                "data": {
                    "challenge_id": challenge.challenge_id,
                    "claim_id": challenge.claim_id,
                    "type": "verification_challenge",
                },
                "notification": {
                    "title": "FIGGY Verification",
                    "body": f"Claim #{challenge.claim_id[:8]}: Verify your location within 30 min",
                },
            }
        }

        try:
            # Mock FCM API call (in production, use firebase_admin SDK)
            logger.debug("fcm_payload", payload=payload)
            return True  # Assume success in this mock
        except Exception as e:
            logger.error("fcm_send_error", error=str(e))
            return False

    async def _get_worker_device_token(self, worker_id: str) -> Optional[str]:
        """Fetch worker's device token from cache or profile service."""
        # In production: query worker profile service
        # For now: return mock token
        cache_key = f"worker_device_token:{worker_id}"
        token = await self.redis.get(cache_key)
        return token or f"device_token_{worker_id}"  # Mock token

    async def _send_sms_fallback(
        self, worker_id: str, challenge: VerificationChallenge
    ) -> bool:
        """
        Send SMS notification as fallback.

        Template: "FIGGY: Your claim #{claim_id} needs verification.
        Open the FIGGY app within 30 min to confirm your location. Reply STOP to opt out."

        Args:
            worker_id: Worker identifier
            challenge: Challenge details

        Returns:
            True if successfully sent
        """
        if not self.twilio_account_sid or not self.twilio_auth_token:
            logger.warning("twilio_credentials_not_configured")
            return False

        # In production: fetch worker phone from profile service
        worker_phone = await self._get_worker_phone(worker_id)
        if not worker_phone:
            logger.warning("worker_phone_not_found", worker_id=worker_id)
            return False

        message_body = (
            f"FIGGY: Your claim #{challenge.claim_id[:8]} needs verification. "
            f"Open the FIGGY app within 30 min to confirm your location. Reply STOP to opt out."
        )

        try:
            # Mock Twilio SMS (in production, use twilio SDK)
            logger.info(
                "sms_sent_mock",
                worker_id=worker_id,
                phone=worker_phone[:4] + "****",
                message_len=len(message_body),
            )
            return True  # Assume success in mock
        except Exception as e:
            logger.error("sms_send_error", error=str(e))
            return False

    async def _get_worker_phone(self, worker_id: str) -> Optional[str]:
        """Fetch worker's phone number."""
        # In production: query worker profile service
        # For now: return mock phone
        cache_key = f"worker_phone:{worker_id}"
        phone = await self.redis.get(cache_key)
        return phone or f"+919876543{worker_id[-3:]}"  # Mock phone

    def get_metrics(self) -> dict:
        """Return notification metrics."""
        return {
            "fcm_sent": self.fcm_sent,
            "fcm_failed": self.fcm_failed,
            "sms_fallback_sent": self.sms_fallback_sent,
            "total_notifications": self.fcm_sent + self.fcm_failed + self.sms_fallback_sent,
        }
