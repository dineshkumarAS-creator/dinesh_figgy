"""
Reviewer Management - Auto-assignment and load balancing

Handles reviewer profiles, auto-assignment logic, and statistics.
"""

import json
from datetime import datetime, timezone
from typing import Optional, Literal

import redis.asyncio as aioredis
import structlog

from manual_review.schemas import ReviewerProfile, ReviewerStats

logger = structlog.get_logger()


class ReviewerService:
    """Manages reviewer profiles and auto-assignment."""

    def __init__(self, redis_client: aioredis.Redis):
        """Initialize reviewer service."""
        self.redis = redis_client

    async def create_reviewer(
        self,
        name: str,
        email: str,
        role: Literal["junior", "senior", "lead"],
        specialisation: Optional[list[str]] = None,
    ) -> ReviewerProfile:
        """
        Create new reviewer profile.

        Args:
            name: Reviewer name
            email: Reviewer email
            role: "junior", "senior", "lead"
            specialisation: List of specialisations (e.g., ["chennai", "rain_claims"])

        Returns:
            ReviewerProfile
        """
        # Max load per role
        max_load_map = {"junior": 5, "senior": 10, "lead": 15}

        profile = ReviewerProfile(
            name=name,
            email=email,
            role=role,
            active=True,
            current_load=0,
            max_load=max_load_map[role],
            specialisation=specialisation or [],
            total_decided=0,
            approval_rate=0.5,
            avg_decision_time_min=0.0,
        )

        # Store in Redis
        await self.redis.set(
            f"reviewer:{profile.reviewer_id}",
            profile.model_dump_json(),
            ex=3600 * 24 * 365,  # 1 year
        )

        # Add to active reviewers set
        await self.redis.sadd("reviewers:active", profile.reviewer_id)

        logger.info(
            "reviewer_created",
            reviewer_id=profile.reviewer_id,
            name=name,
            role=role,
        )

        return profile

    async def get_reviewer(self, reviewer_id: str) -> Optional[ReviewerProfile]:
        """Get reviewer profile by ID."""
        profile_json = await self.redis.get(f"reviewer:{reviewer_id}")
        if not profile_json:
            return None
        return ReviewerProfile(**json.loads(profile_json))

    async def update_load(
        self,
        reviewer_id: str,
        delta: int,
    ) -> Optional[ReviewerProfile]:
        """
        Update reviewer's current load (add/subtract assignment count).

        Args:
            reviewer_id: Reviewer UUID
            delta: Change in load (typically +1 on assign, -1 on release)

        Returns:
            Updated ReviewerProfile or None if not found
        """
        profile = await self.get_reviewer(reviewer_id)
        if not profile:
            return None

        profile.current_load = max(0, profile.current_load + delta)

        await self.redis.set(
            f"reviewer:{reviewer_id}",
            profile.model_dump_json(),
            ex=3600 * 24 * 365,
        )

        return profile

    async def record_decision(
        self,
        reviewer_id: str,
        decision: Literal["approve", "reject", "request_more_info"],
        decision_time_min: float,
    ) -> Optional[ReviewerProfile]:
        """
        Record decision stats after reviewer completes a claim review.

        Args:
            reviewer_id: Reviewer UUID
            decision: Decision type
            decision_time_min: Time spent on decision

        Returns:
            Updated ReviewerProfile or None if not found
        """
        profile = await self.get_reviewer(reviewer_id)
        if not profile:
            return None

        # Update stats
        total = profile.total_decided + 1
        approved = profile.total_decided * profile.approval_rate

        if decision == "approve":
            approved += 1

        profile.total_decided = total
        profile.approval_rate = approved / total if total > 0 else 0.5

        # Update average decision time (exponential moving average)
        if profile.avg_decision_time_min == 0.0:
            profile.avg_decision_time_min = decision_time_min
        else:
            # EMA: new_avg = 0.9 * old_avg + 0.1 * new_time
            profile.avg_decision_time_min = (
                0.9 * profile.avg_decision_time_min
                + 0.1 * decision_time_min
            )

        # Decrement load
        profile.current_load = max(0, profile.current_load - 1)

        await self.redis.set(
            f"reviewer:{reviewer_id}",
            profile.model_dump_json(),
            ex=3600 * 24 * 365,
        )

        logger.info(
            "decision_recorded",
            reviewer_id=reviewer_id,
            decision=decision,
            decision_time_min=decision_time_min,
            total_decided=total,
            approval_rate=profile.approval_rate,
        )

        return profile

    async def find_best_reviewer(
        self,
        priority: int,
        specialisation: Optional[list[str]] = None,
    ) -> Optional[ReviewerProfile]:
        """
        Find best reviewer for assignment based on:
          1. Role requirements (junior can't take priority=1)
          2. Specialisation match
          3. Load balance (lowest current_load / max_load ratio)

        Args:
            priority: Claim priority (1-3)
            specialisation: Desired specialisations (optional)

        Returns:
            Best ReviewerProfile or None if all at max load
        """
        # Get all active reviewers
        reviewer_ids = await self.redis.smembers("reviewers:active")
        if not reviewer_ids:
            logger.warning("no_active_reviewers")
            return None

        candidates = []

        for reviewer_id_bytes in reviewer_ids:
            reviewer_id = reviewer_id_bytes.decode() if isinstance(reviewer_id_bytes, bytes) else reviewer_id_bytes
            profile = await self.get_reviewer(reviewer_id)
            if not profile:
                continue

            # Filter by role capability
            if priority == 1 and profile.role == "junior":
                continue  # Junior can't take critical

            # Filter by active status
            if not profile.active:
                continue

            # Filter by load capacity
            if profile.current_load >= profile.max_load:
                continue

            # Calculate load ratio
            load_ratio = profile.current_load / profile.max_load

            candidates.append((load_ratio, profile))

        if not candidates:
            logger.warning(
                "no_available_reviewers",
                priority=priority,
                specialisation=specialisation,
            )
            return None

        # Sort by load ratio (ascending) -> best is lowest load
        candidates.sort(key=lambda x: x[0])

        # Check for specialisation match
        if specialisation:
            for load_ratio, profile in candidates:
                if any(s in profile.specialisation for s in specialisation):
                    logger.info(
                        "reviewer_assigned",
                        reviewer_id=profile.reviewer_id,
                        priority=priority,
                        specialisation_match=True,
                        load_ratio=load_ratio,
                    )
                    return profile

        # No specialisation match, return lowest load reviewer
        _, best = candidates[0]
        logger.info(
            "reviewer_assigned",
            reviewer_id=best.reviewer_id,
            priority=priority,
            specialisation_match=False,
            load_ratio=candidates[0][0],
        )
        return best

    async def get_all_reviewers(self) -> list[ReviewerProfile]:
        """Get all active reviewers."""
        reviewer_ids = await self.redis.smembers("reviewers:active")
        profiles = []

        for reviewer_id_bytes in reviewer_ids:
            reviewer_id = reviewer_id_bytes.decode() if isinstance(reviewer_id_bytes, bytes) else reviewer_id_bytes
            profile = await self.get_reviewer(reviewer_id)
            if profile:
                profiles.append(profile)

        return profiles

    async def get_stats(self, reviewer_id: str) -> Optional[ReviewerStats]:
        """Get reviewer stats."""
        profile = await self.get_reviewer(reviewer_id)
        if not profile:
            return None

        return ReviewerStats(
            reviewer_id=profile.reviewer_id,
            name=profile.name,
            role=profile.role,
            decisions_today=0,  # Would need time-bucket tracking for this
            approval_rate=profile.approval_rate,
            avg_decision_time_min=profile.avg_decision_time_min,
            current_load=profile.current_load,
            max_load=profile.max_load,
        )

    async def deactivate_reviewer(self, reviewer_id: str) -> None:
        """Deactivate a reviewer (e.g., end of shift)."""
        profile = await self.get_reviewer(reviewer_id)
        if not profile:
            return

        profile.active = False

        await self.redis.set(
            f"reviewer:{reviewer_id}",
            profile.model_dump_json(),
            ex=3600 * 24 * 365,
        )

        await self.redis.srem("reviewers:active", reviewer_id)

        logger.info(
            "reviewer_deactivated",
            reviewer_id=reviewer_id,
            name=profile.name,
        )

    async def check_load_alert(self) -> dict:
        """
        Check for load alerts:
          - Critical queue > 20 items
          - All reviewers at max load

        Returns:
            {
                "queue_critical_depth": int,
                "all_reviewers_maxed": bool,
                "alert_triggered": bool,
            }
        """
        # Get critical queue depth
        critical_count = await self.redis.scard("queue:priority:1")

        # Check if all reviewers at max load
        reviewers = await self.get_all_reviewers()
        all_maxed = all(
            r.current_load >= r.max_load for r in reviewers if r.active
        )

        alert = critical_count > 20 or all_maxed

        return {
            "queue_critical_depth": critical_count,
            "all_reviewers_maxed": all_maxed,
            "alert_triggered": alert,
        }
