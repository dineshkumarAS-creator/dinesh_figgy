"""
Manual Review Queue - PostgreSQL + Redis backed queue management

Handles enqueuing high-risk claims, assignment, and SLA tracking.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
from enum import Enum

import redis.asyncio as aioredis
import structlog
from sqlalchemy import select, update, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from manual_review.schemas import ReviewQueueItem, ManualReviewDecision

logger = structlog.get_logger()


class PriorityTier(int, Enum):
    """Priority tier enumeration."""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3


class ReviewQueueService:
    """Manages the manual review queue."""

    # SLA hours per priority
    SLA_HOURS = {
        PriorityTier.CRITICAL: 2,
        PriorityTier.HIGH: 4,
        PriorityTier.NORMAL: 8,
    }

    def __init__(self, db_session: AsyncSession, redis_client: aioredis.Redis):
        """
        Initialize queue service.

        Args:
            db_session: SQLAlchemy async session
            redis_client: Redis async client
        """
        self.db = db_session
        self.redis = redis_client

    @staticmethod
    def calculate_priority(
        payout_eligible_inr: float,
        trust_tier: str,
        crowd_spike_flag: bool,
        disruption_score: float,
    ) -> int:
        """
        Calculate priority based on claim characteristics.

        Priority rules:
          - CRITICAL (1): payout > ₹1000 OR trust_tier=="flagged" OR crowd_spike
          - HIGH (2): payout ₹300-1000 OR (new worker AND high disruption)
          - NORMAL (3): everything else

        Args:
            payout_eligible_inr: Eligible payout amount
            trust_tier: "new", "trusted", "flagged"
            crowd_spike_flag: Unusual crowd size flag
            disruption_score: From parametric trigger (0-1)

        Returns:
            Priority tier (1-3)
        """
        # CRITICAL tier
        if (
            payout_eligible_inr >= 1000
            or trust_tier == "flagged"
            or crowd_spike_flag
        ):
            return PriorityTier.CRITICAL

        # HIGH tier
        if (
            300 <= payout_eligible_inr < 1000
            or (trust_tier == "new" and disruption_score > 0.7)
        ):
            return PriorityTier.HIGH

        # NORMAL tier (default)
        return PriorityTier.NORMAL

    async def enqueue(
        self,
        claim_id: str,
        worker_id: str,
        risk_score: float,
        payout_eligible_inr: float,
        trust_tier: str,
        crowd_spike_flag: bool = False,
        disruption_score: float = 0.0,
    ) -> ReviewQueueItem:
        """
        Enqueue a high-risk claim for manual review.

        Args:
            claim_id: Claim UUID
            worker_id: Worker UUID
            risk_score: Combined risk score (0-1)
            payout_eligible_inr: Payout amount
            trust_tier: "new", "trusted", "flagged"
            crowd_spike_flag: Unusual crowd size
            disruption_score: Parametric trigger disruption

        Returns:
            ReviewQueueItem

        Raises:
            ValueError: If claim already in queue
        """
        # Check if already queued
        existing = await self.redis.get(f"queue:claim:{claim_id}")
        if existing:
            logger.warning(
                "claim_already_queued",
                claim_id=claim_id,
                queue_id=existing,
            )
            return ReviewQueueItem(**json.loads(existing))

        # Calculate priority
        priority = self.calculate_priority(
            payout_eligible_inr=payout_eligible_inr,
            trust_tier=trust_tier,
            crowd_spike_flag=crowd_spike_flag,
            disruption_score=disruption_score,
        )

        # Create queue item
        queue_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        sla_hours = self.SLA_HOURS[priority]
        sla_deadline = now + timedelta(hours=sla_hours)

        item = ReviewQueueItem(
            queue_id=queue_id,
            claim_id=claim_id,
            worker_id=worker_id,
            priority=priority,
            risk_score=risk_score,
            assigned_reviewer_id=None,
            assigned_at=None,
            sla_deadline=sla_deadline,
            status="pending",
            created_at=now,
            payout_eligible_inr=payout_eligible_inr,
            trust_tier=trust_tier,
        )

        # Store in Redis
        await self.redis.setex(
            f"queue:claim:{claim_id}",
            3600 * 24,  # 24-hour TTL
            item.model_dump_json(),
        )

        # Store in sorted set by priority (lower = higher priority) and creation time
        score = (priority * 1000000) + now.timestamp()
        await self.redis.zadd("queue:pending", {queue_id: score})
        await self.redis.sadd(f"queue:priority:{priority}", queue_id)

        logger.info(
            "claim_enqueued",
            claim_id=claim_id,
            queue_id=queue_id,
            priority=priority,
            payout_eligible_inr=payout_eligible_inr,
        )

        return item

    async def assign_next(
        self,
        reviewer_id: str,
        reviewer_role: str,
    ) -> Optional[ReviewQueueItem]:
        """
        Assign next pending item to reviewer.

        Rules:
          - Junior reviewers CANNOT take priority=1 (critical)
          - Assign from lowest priority (highest number) first FIFO

        Args:
            reviewer_id: Reviewer UUID
            reviewer_role: "junior", "senior", "lead"

        Returns:
            ReviewQueueItem or None if queue empty
        """
        # Determine maximum priority this reviewer can take
        min_priority = 1 if reviewer_role in ["senior", "lead"] else 2

        # Scan each priority tier finding first available
        for priority in [PriorityTier.CRITICAL, PriorityTier.HIGH, PriorityTier.NORMAL]:
            if priority < min_priority:
                continue

            # Get next queue_id from sorted set for this priority
            queue_ids = await self.redis.zrange(
                f"queue:priority:{priority}", 0, 0
            )
            if not queue_ids:
                continue

            queue_id = queue_ids[0].decode() if isinstance(queue_ids[0], bytes) else queue_ids[0]

            # Load item
            item_json = await self.redis.get(f"queue:item:{queue_id}")
            if not item_json:
                # Item expired or deleted, continue
                await self.redis.zrem(f"queue:priority:{priority}", queue_id)
                continue

            item = ReviewQueueItem(**json.loads(item_json))

            # Assign to reviewer
            now = datetime.now(timezone.utc)
            item.assigned_reviewer_id = reviewer_id
            item.assigned_at = now
            item.status = "assigned"

            # Update Redis
            await self.redis.set(
                f"queue:item:{queue_id}",
                item.model_dump_json(),
                ex=3600 * 24,
            )
            await self.redis.set(
                f"reviewer:current:{reviewer_id}",
                queue_id,
                ex=3600 * 24,
            )

            logger.info(
                "claim_assigned",
                queue_id=queue_id,
                claim_id=item.claim_id,
                reviewer_id=reviewer_id,
                priority=priority,
            )

            return item

        return None

    async def get_by_id(self, queue_id: str) -> Optional[ReviewQueueItem]:
        """Get queue item by ID."""
        item_json = await self.redis.get(f"queue:item:{queue_id}")
        if not item_json:
            return None
        return ReviewQueueItem(**json.loads(item_json))

    async def get_pending_items(
        self,
        priority: Optional[int] = None,
        limit: int = 10,
    ) -> list[ReviewQueueItem]:
        """
        Get pending items, optionally filtered by priority.

        Args:
            priority: Optional priority tier (1-3)
            limit: Max items to return

        Returns:
            List of ReviewQueueItems
        """
        items = []

        if priority:
            priorities = [priority]
        else:
            priorities = [1, 2, 3]  # All priorities

        for p in priorities:
            queue_ids = await self.redis.zrange(
                f"queue:priority:{p}", 0, limit - len(items) - 1
            )

            for queue_id_bytes in queue_ids:
                queue_id = queue_id_bytes.decode() if isinstance(queue_id_bytes, bytes) else queue_id_bytes
                item = await self.get_by_id(queue_id)
                if item:
                    items.append(item)

            if len(items) >= limit:
                break

        return items[:limit]

    async def release(self, queue_id: str, reviewer_id: str) -> None:
        """
        Release claim from reviewer without decision.

        Args:
            queue_id: Queue item ID
            reviewer_id: Reviewer who is releasing
        """
        item = await self.get_by_id(queue_id)
        if not item:
            logger.warning("queue_item_not_found", queue_id=queue_id)
            return

        if item.assigned_reviewer_id != reviewer_id:
            logger.warning(
                "release_permission_denied",
                queue_id=queue_id,
                reviewer_id=reviewer_id,
            )
            return

        # Reset assignment
        item.assigned_reviewer_id = None
        item.assigned_at = None
        item.status = "pending"

        await self.redis.set(
            f"queue:item:{queue_id}",
            item.model_dump_json(),
            ex=3600 * 24,
        )
        await self.redis.delete(f"reviewer:current:{reviewer_id}")

        logger.info(
            "claim_released",
            queue_id=queue_id,
            reviewer_id=reviewer_id,
        )

    async def mark_decided(
        self,
        queue_id: str,
        decision: ManualReviewDecision,
    ) -> None:
        """
        Mark queue item as decided.

        Args:
            queue_id: Queue item ID
            decision: ReviewerDecision
        """
        item = await self.get_by_id(queue_id)
        if not item:
            logger.warning("queue_item_not_found", queue_id=queue_id)
            return

        item.status = "decided"
        item.decided_at = decision.decided_at

        # Store decision in Redis with claim mapping
        await self.redis.set(
            f"decision:{queue_id}",
            decision.model_dump_json(),
            ex=3600 * 24 * 30,  # 30 days
        )

        # Update queue item
        await self.redis.set(
            f"queue:item:{queue_id}",
            item.model_dump_json(),
            ex=3600 * 24,
        )

        # Clean up reviewer assignment
        await self.redis.delete(f"reviewer:current:{decision.reviewer_id}")

        logger.info(
            "claim_decided",
            queue_id=queue_id,
            decision=decision.decision,
            reviewer_id=decision.reviewer_id,
        )

    async def sla_breach_check(self) -> list[ReviewQueueItem]:
        """
        Find all items past SLA deadline.

        Returns immediately for items with SLA < now.

        Called periodically (e.g., every 15 min via APScheduler).

        Returns:
            List of breached items
        """
        breached = []
        now = datetime.now(timezone.utc)

        for priority in [1, 2, 3]:
            queue_ids = await self.redis.smembers(f"queue:priority:{priority}")

            for queue_id_bytes in queue_ids:
                queue_id = queue_id_bytes.decode() if isinstance(queue_id_bytes, bytes) else queue_id_bytes
                item = await self.get_by_id(queue_id)

                if item and item.sla_deadline < now and item.status == "assigned":
                    breached.append(item)

                    # Mark as escalated
                    item.status = "escalated"
                    await self.redis.set(
                        f"queue:item:{queue_id}",
                        item.model_dump_json(),
                        ex=3600 * 24,
                    )

                    logger.warning(
                        "sla_breach_detected",
                        queue_id=queue_id,
                        claim_id=item.claim_id,
                        reviewer_id=item.assigned_reviewer_id,
                        deadline=item.sla_deadline.isoformat(),
                    )

        return breached

    async def get_queue_metrics(self) -> dict:
        """
        Get queue depth metrics by priority.

        Returns:
            {
                "pending_critical": int,
                "pending_high": int,
                "pending_normal": int,
                "assigned_total": int,
                "breached_total": int,
            }
        """
        metrics = {}

        for priority in [1, 2, 3]:
            count = await self.redis.scard(f"queue:priority:{priority}")
            priority_name = {1: "critical", 2: "high", 3: "normal"}[priority]
            metrics[f"pending_{priority_name}"] = count

        # Count escalated items
        escalated = 0
        for priority in [1, 2, 3]:
            queue_ids = await self.redis.smembers(f"queue:priority:{priority}")
            for queue_id_bytes in queue_ids:
                queue_id = queue_id_bytes.decode() if isinstance(queue_id_bytes, bytes) else queue_id_bytes
                item = await self.get_by_id(queue_id)
                if item and item.status == "escalated":
                    escalated += 1

        metrics["escalated_total"] = escalated

        return metrics
