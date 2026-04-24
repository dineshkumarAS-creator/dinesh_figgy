"""
Appeals Flow - Handling rejected claim appeals

Worker appeals mechanism for rejected claims with priority routing.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal

import redis.asyncio as aioredis
import structlog

from manual_review.schemas import Appeal, AppealDecision
from manual_review.queue import ReviewQueueService, PriorityTier

logger = structlog.get_logger()


class AppealService:
    """Manages appeal submissions and decisions."""

    # Appeal SLA: 24 hours for resolution
    APPEAL_SLA_HOURS = 24

    def __init__(
        self,
        redis_client: aioredis.Redis,
        queue_service: ReviewQueueService,
    ):
        """Initialize appeal service."""
        self.redis = redis_client
        self.queue_service = queue_service

    async def submit_appeal(
        self,
        claim_id: str,
        worker_id: str,
        appeal_reason: str,
        evidence_urls: Optional[list[str]] = None,
    ) -> Appeal:
        """
        Submit appeal for a rejected claim.

        Validates claim is in REJECTED state, creates Appeal record,
        and enqueues for priority=1 review.

        Args:
            claim_id: Claim UUID
            worker_id: Worker UUID
            appeal_reason: Worker's reason for appeal
            evidence_urls: List of evidence URLs (photo, video, etc.)

        Returns:
            Appeal record

        Raises:
            ValueError: If claim not in REJECTED state
        """
        # Check claim status (in production: fetch from ClaimService)
        claim_status_key = f"claim:status:{claim_id}"
        claim_status = await self.redis.get(claim_status_key)

        # If not cached, assume REJECTED for this demo
        if claim_status and claim_status != "REJECTED":
            raise ValueError(
                f"Can only appeal REJECTED claims, got {claim_status}"
            )

        # Create Appeal record
        appeal_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        appeal = Appeal(
            appeal_id=appeal_id,
            claim_id=claim_id,
            worker_id=worker_id,
            appeal_reason=appeal_reason,
            evidence_urls=evidence_urls or [],
            status="pending",
            submitted_at=now,
        )

        # Store appeal in Redis
        await self.redis.set(
            f"appeal:{appeal_id}",
            appeal.model_dump_json(),
            ex=3600 * 24 * 30,  # 30 days
        )

        # Index by claim
        await self.redis.set(
            f"appeal:claim:{claim_id}",
            appeal_id,
            ex=3600 * 24 * 30,
        )

        # Transition claim state: REJECTED → APPEALED
        # (in production: use ClaimService.transition_state)
        await self.redis.set(
            f"claim:status:{claim_id}",
            "APPEALED",
            ex=3600 * 24 * 30,
        )

        # Enqueue appeal as PRIORITY=1 for immediate review
        try:
            queue_item = await self.queue_service.enqueue(
                claim_id=claim_id,
                worker_id=worker_id,
                risk_score=0.9,  # Appeals are high priority
                payout_eligible_inr=1000.0,  # Force high priority
                trust_tier="flagged",  # Force critical tier
                crowd_spike_flag=False,
                disruption_score=0.0,
            )

            appeal.queue_item_id = queue_item.queue_id

            # Update appeal with queue info
            await self.redis.set(
                f"appeal:{appeal_id}",
                appeal.model_dump_json(),
                ex=3600 * 24 * 30,
            )

        except Exception as e:
            logger.error("appeal_enqueue_error", appeal_id=appeal_id, error=str(e))
            # Appeal still created, but not in queue

        logger.info(
            "appeal_submitted",
            appeal_id=appeal_id,
            claim_id=claim_id,
            worker_id=worker_id,
            reason=appeal_reason[:50],
        )

        return appeal

    async def get_appeal(self, appeal_id: str) -> Optional[Appeal]:
        """Get appeal by ID."""
        appeal_json = await self.redis.get(f"appeal:{appeal_id}")
        if not appeal_json:
            return None
        return Appeal(**json.loads(appeal_json))

    async def get_appeal_by_claim(self, claim_id: str) -> Optional[Appeal]:
        """Get appeal for a claim (if exists)."""
        appeal_id = await self.redis.get(f"appeal:claim:{claim_id}")
        if not appeal_id:
            return None
        return await self.get_appeal(appeal_id)

    async def decide_appeal(
        self,
        appeal_id: str,
        decision: Literal["approved", "rejected"],
        reviewer_id: str,
        decision_notes: str,
    ) -> Appeal:
        """
        Decide on an appeal.

        Args:
            appeal_id: Appeal ID
            decision: "approved" or "rejected"
            reviewer_id: Reviewer making decision
            decision_notes: Notes from reviewer

        Returns:
            Updated Appeal

        Raises:
            ValueError: If appeal not found or invalid state
        """
        appeal = await self.get_appeal(appeal_id)
        if not appeal:
            raise ValueError(f"Appeal {appeal_id} not found")

        if appeal.status != "pending":
            raise ValueError(f"Cannot decide on {appeal.status} appeal")

        now = datetime.now(timezone.utc)

        # Update appeal
        appeal.status = decision
        appeal.resolved_at = now
        appeal.reviewer_id = reviewer_id
        appeal.decision_notes = decision_notes

        # Update claim state based on decision
        if decision == "approved":
            # APPEALED → PAYOUT_PROCESSING
            new_claim_state = "PAYOUT_PROCESSING"
            logger.info(
                "appeal_approved",
                appeal_id=appeal_id,
                claim_id=appeal.claim_id,
                reviewer_id=reviewer_id,
            )
        else:
            # APPEALED → APPEAL_REJECTED → EXPIRED (non-recoverable)
            new_claim_state = "APPEAL_REJECTED"
            logger.info(
                "appeal_rejected",
                appeal_id=appeal_id,
                claim_id=appeal.claim_id,
                reviewer_id=reviewer_id,
            )

        # Transition claim (in production: use ClaimService)
        await self.redis.set(
            f"claim:status:{appeal.claim_id}",
            new_claim_state,
            ex=3600 * 24 * 30,
        )

        # Update appeal record
        await self.redis.set(
            f"appeal:{appeal_id}",
            appeal.model_dump_json(),
            ex=3600 * 24 * 30,
        )

        # Publish appeal decision to Kafka (in production)
        # {
        #     "appeal_id": appeal_id,
        #     "claim_id": appeal.claim_id,
        #     "worker_id": appeal.worker_id,
        #     "decision": decision,
        #     "reviewer_id": reviewer_id,
        #     "resolved_at": now.isoformat(),
        # }

        return appeal

    async def get_pending_appeals(self, limit: int = 10) -> list[Appeal]:
        """Get pending appeals for review."""
        # Scan appeals in Redis (in production: query PostgreSQL)
        appeals = []
        keys = await self.redis.keys("appeal:*")

        for key in keys:
            if key.startswith("appeal:claim:"):
                continue  # Skip index keys

            appeal_json = await self.redis.get(key)
            if appeal_json:
                appeal = Appeal(**json.loads(appeal_json))
                if appeal.status == "pending":
                    appeals.append(appeal)

            if len(appeals) >= limit:
                break

        # Sort by submitted_at (oldest first)
        appeals.sort(key=lambda a: a.submitted_at)

        return appeals

    async def get_appeal_metrics(self) -> dict:
        """Get appeal metrics."""
        # Scan all appeals
        total_appeals = 0
        approved_appeals = 0
        rejected_appeals = 0
        overtime_appeals = 0

        keys = await self.redis.keys("appeal:*")

        for key in keys:
            if key.startswith("appeal:claim:"):
                continue

            appeal_json = await self.redis.get(key)
            if appeal_json:
                appeal = Appeal(**json.loads(appeal_json))
                total_appeals += 1

                if appeal.status == "approved":
                    approved_appeals += 1
                elif appeal.status == "rejected":
                    rejected_appeals += 1

                # Check if overdue
                if appeal.status == "pending":
                    now = datetime.now(timezone.utc)
                    sla = appeal.submitted_at + timedelta(hours=self.APPEAL_SLA_HOURS)
                    if now > sla:
                        overtime_appeals += 1

        return {
            "total_appeals": total_appeals,
            "approved": approved_appeals,
            "rejected": rejected_appeals,
            "pending": total_appeals - approved_appeals - rejected_appeals,
            "overtime": overtime_appeals,
            "overturn_rate": (
                approved_appeals / total_appeals
                if total_appeals > 0
                else 0.0
            ),  # % of rejections overturned
        }
