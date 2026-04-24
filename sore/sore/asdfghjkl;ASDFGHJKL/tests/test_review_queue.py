"""
Tests for Manual Review Queue and Reviewer Assignment

Tests priority calculation, auto-assignment, load balancing, and SLA tracking.
"""

import pytest
from datetime import datetime, timedelta, timezone
from manual_review.queue import ReviewQueueService, PriorityTier
from manual_review.reviewers import ReviewerService
from unittest.mock import AsyncMock, MagicMock


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    return AsyncMock()


@pytest.fixture
def queue_service(mock_redis):
    """Create queue service with mocked dependencies."""
    return ReviewQueueService(db_session=None, redis_client=mock_redis)


@pytest.fixture
def reviewer_service(mock_redis):
    """Create reviewer service with mocked Redis."""
    return ReviewerService(redis_client=mock_redis)


# ==============================================================================
# Priority Calculation Tests
# ==============================================================================


class TestPriorityCalculation:
    """Test priority tier assignment logic."""

    def test_priority_critical_high_payout(self):
        """Payout > ₹1000 → CRITICAL."""
        priority = ReviewQueueService.calculate_priority(
            payout_eligible_inr=1500.0,
            trust_tier="trusted",
            crowd_spike_flag=False,
            disruption_score=0.0,
        )
        assert priority == PriorityTier.CRITICAL

    def test_priority_critical_flagged_worker(self):
        """trust_tier == 'flagged' → CRITICAL."""
        priority = ReviewQueueService.calculate_priority(
            payout_eligible_inr=200.0,
            trust_tier="flagged",
            crowd_spike_flag=False,
            disruption_score=0.0,
        )
        assert priority == PriorityTier.CRITICAL

    def test_priority_critical_crowd_spike(self):
        """crowd_spike_flag=True → CRITICAL."""
        priority = ReviewQueueService.calculate_priority(
            payout_eligible_inr=200.0,
            trust_tier="trusted",
            crowd_spike_flag=True,
            disruption_score=0.0,
        )
        assert priority == PriorityTier.CRITICAL

    def test_priority_high_mid_payout(self):
        """Payout ₹300-1000 → HIGH."""
        priority = ReviewQueueService.calculate_priority(
            payout_eligible_inr=500.0,
            trust_tier="trusted",
            crowd_spike_flag=False,
            disruption_score=0.0,
        )
        assert priority == PriorityTier.HIGH

    def test_priority_high_new_worker_high_disruption(self):
        """New worker + high disruption → HIGH."""
        priority = ReviewQueueService.calculate_priority(
            payout_eligible_inr=200.0,
            trust_tier="new",
            crowd_spike_flag=False,
            disruption_score=0.8,
        )
        assert priority == PriorityTier.HIGH

    def test_priority_high_new_worker_low_disruption(self):
        """New worker + low disruption → NORMAL (not HIGH)."""
        priority = ReviewQueueService.calculate_priority(
            payout_eligible_inr=200.0,
            trust_tier="new",
            crowd_spike_flag=False,
            disruption_score=0.5,
        )
        assert priority == PriorityTier.NORMAL

    def test_priority_normal_low_payout(self):
        """Low payout, trusted worker → NORMAL."""
        priority = ReviewQueueService.calculate_priority(
            payout_eligible_inr=100.0,
            trust_tier="trusted",
            crowd_spike_flag=False,
            disruption_score=0.0,
        )
        assert priority == PriorityTier.NORMAL

    def test_priority_boundary_1000_inr(self):
        """Exactly ₹1000 → CRITICAL (not HIGH)."""
        priority = ReviewQueueService.calculate_priority(
            payout_eligible_inr=1000.0,
            trust_tier="trusted",
            crowd_spike_flag=False,
            disruption_score=0.0,
        )
        assert priority == PriorityTier.CRITICAL

    def test_priority_boundary_300_inr(self):
        """Exactly ₹300 is HIGH."""
        priority = ReviewQueueService.calculate_priority(
            payout_eligible_inr=300.0,
            trust_tier="trusted",
            crowd_spike_flag=False,
            disruption_score=0.0,
        )
        assert priority == PriorityTier.HIGH

    def test_priority_boundary_299_inr(self):
        """₹299 is NORMAL."""
        priority = ReviewQueueService.calculate_priority(
            payout_eligible_inr=299.0,
            trust_tier="trusted",
            crowd_spike_flag=False,
            disruption_score=0.0,
        )
        assert priority == PriorityTier.NORMAL


# ==============================================================================
# Queue Enqueue Tests
# ==============================================================================


class TestEnqueue:
    """Test claim enqueueing."""

    @pytest.mark.asyncio
    async def test_enqueue_sets_correct_sla_hours(self, queue_service):
        """Enqueued item gets correct SLA deadline based on priority."""
        queue_service.redis.get = AsyncMock(return_value=None)
        queue_service.redis.setex = AsyncMock()
        queue_service.redis.zadd = AsyncMock()
        queue_service.redis.sadd = AsyncMock()

        # CRITICAL (priority=1) should get 2-hour SLA
        item = await queue_service.enqueue(
            claim_id="claim_1",
            worker_id="worker_1",
            risk_score=0.8,
            payout_eligible_inr=1500.0,  # > 1000 → CRITICAL
            trust_tier="trusted",
            crowd_spike_flag=False,
            disruption_score=0.0,
        )

        # Verify priority
        assert item.priority == PriorityTier.CRITICAL

        # Verify SLA deadline is ~2 hours from now
        now = datetime.now(timezone.utc)
        expected_sla = now + timedelta(hours=2)
        time_diff = abs((item.sla_deadline - expected_sla).total_seconds())
        assert time_diff < 60  # Within 60 seconds

    @pytest.mark.asyncio
    async def test_enqueue_high_priority_gets_4_hour_sla(self, queue_service):
        """HIGH priority (2) gets 4-hour SLA."""
        queue_service.redis.get = AsyncMock(return_value=None)
        queue_service.redis.setex = AsyncMock()
        queue_service.redis.zadd = AsyncMock()
        queue_service.redis.sadd = AsyncMock()

        item = await queue_service.enqueue(
            claim_id="claim_2",
            worker_id="worker_2",
            risk_score=0.6,
            payout_eligible_inr=500.0,  # 300-1000 → HIGH
            trust_tier="trusted",
            crowd_spike_flag=False,
            disruption_score=0.0,
        )

        assert item.priority == PriorityTier.HIGH

        now = datetime.now(timezone.utc)
        expected_sla = now + timedelta(hours=4)
        time_diff = abs((item.sla_deadline - expected_sla).total_seconds())
        assert time_diff < 60

    @pytest.mark.asyncio
    async def test_enqueue_normal_priority_gets_8_hour_sla(self, queue_service):
        """NORMAL priority (3) gets 8-hour SLA."""
        queue_service.redis.get = AsyncMock(return_value=None)
        queue_service.redis.setex = AsyncMock()
        queue_service.redis.zadd = AsyncMock()
        queue_service.redis.sadd = AsyncMock()

        item = await queue_service.enqueue(
            claim_id="claim_3",
            worker_id="worker_3",
            risk_score=0.3,
            payout_eligible_inr=100.0,  # < 300 → NORMAL
            trust_tier="trusted",
            crowd_spike_flag=False,
            disruption_score=0.0,
        )

        assert item.priority == PriorityTier.NORMAL

        now = datetime.now(timezone.utc)
        expected_sla = now + timedelta(hours=8)
        time_diff = abs((item.sla_deadline - expected_sla).total_seconds())
        assert time_diff < 60


# ==============================================================================
# Auto-Assignment Tests
# ==============================================================================


class TestAutoAssignment:
    """Test reviewer auto-assignment logic."""

    @pytest.mark.asyncio
    async def test_junior_cannot_assign_critical(self, reviewer_service):
        """Junior reviewers cannot take priority=1 (CRITICAL) claims."""
        reviewer_service.redis.smembers = AsyncMock(return_value=set())
        reviewer_service.redis.get = AsyncMock(return_value=None)

        # Try to find best reviewer for CRITICAL claim as junior
        result = await reviewer_service.find_best_reviewer(
            priority=1,
            specialisation=None,
        )

        # No reviewers available (junior filtered out)
        assert result is None

    @pytest.mark.asyncio
    async def test_load_balancing_lowest_ratio_wins(self, reviewer_service):
        """
        Auto-assignment picks reviewer with lowest current_load / max_load ratio.

        Setup:
          - Reviewer A (senior): 3/10 load = 0.30
          - Reviewer B (senior): 6/10 load = 0.60
        
        Expected: A is selected
        """
        reviewer_service.redis.smembers = AsyncMock(
            return_value={"reviewer_a", "reviewer_b"}
        )

        async def mock_get_reviewer(reviewer_id):
            from manual_review.schemas import ReviewerProfile

            if reviewer_id == "reviewer_a":
                return ReviewerProfile(
                    reviewer_id="reviewer_a",
                    name="Alice",
                    email="alice@figgy.app",
                    role="senior",
                    current_load=3,
                    max_load=10,
                )
            else:
                return ReviewerProfile(
                    reviewer_id="reviewer_b",
                    name="Bob",
                    email="bob@figgy.app",
                    role="senior",
                    current_load=6,
                    max_load=10,
                )

        reviewer_service.get_reviewer = mock_get_reviewer

        result = await reviewer_service.find_best_reviewer(priority=2)

        # Should pick reviewer_a (lower ratio)
        assert result.reviewer_id == "reviewer_a"

    @pytest.mark.asyncio
    async def test_no_capacity_returns_none(self, reviewer_service):
        """If all reviewers at max load, return None."""
        reviewer_service.redis.smembers = AsyncMock(
            return_value={"reviewer_a", "reviewer_b"}
        )

        async def mock_get_reviewer(reviewer_id):
            from manual_review.schemas import ReviewerProfile

            return ReviewerProfile(
                reviewer_id=reviewer_id,
                name="Reviewer",
                email="r@figgy.app",
                role="senior",
                current_load=10,  # At max
                max_load=10,
            )

        reviewer_service.get_reviewer = mock_get_reviewer

        result = await reviewer_service.find_best_reviewer(priority=2)

        # No capacity
        assert result is None


# ==============================================================================
# SLA Breach Detection Tests
# ==============================================================================


class TestSLABreachDetection:
    """Test SLA breach identification."""

    @pytest.mark.asyncio
    async def test_sla_breach_detection_past_deadline(self, queue_service):
        """Items past SLA deadline are flagged as breached."""
        now = datetime.now(timezone.utc)
        past_deadline = now - timedelta(hours=1)  # 1 hour past SLA

        from manual_review.schemas import ReviewQueueItem

        breached_item = ReviewQueueItem(
            queue_id="queue_1",
            claim_id="claim_1",
            worker_id="worker_1",
            priority=1,
            risk_score=0.8,
            assigned_reviewer_id="reviewer_1",
            assigned_at=now - timedelta(hours=3),
            sla_deadline=past_deadline,
            status="assigned",
            created_at=now - timedelta(hours=3),
            payout_eligible_inr=1000.0,
            trust_tier="trusted",
        )

        # Mock Redis to return one queue ID in assigned set (only for priority 1)
        async def mock_smembers(key):
            # Only return the queue for priority 1
            if "priority:1" in key:
                return {"queue_1"}
            return set()

        async def mock_get(key):
            if "queue_1" in key:
                return breached_item.model_dump_json().encode()
            return None

        queue_service.redis.smembers = mock_smembers
        queue_service.redis.get = mock_get
        queue_service.redis.set = AsyncMock()

        breached = await queue_service.sla_breach_check()

        # Should identify 1 breached item
        assert len(breached) == 1
        assert breached[0].queue_id == "queue_1"
        assert breached[0].status == "escalated"

    @pytest.mark.asyncio
    async def test_sla_not_breached_before_deadline(self, queue_service):
        """Items before SLA deadline not flagged."""
        now = datetime.now(timezone.utc)
        future_deadline = now + timedelta(hours=1)  # 1 hour in future

        from manual_review.schemas import ReviewQueueItem

        pending_item = ReviewQueueItem(
            queue_id="queue_2",
            claim_id="claim_2",
            worker_id="worker_2",
            priority=2,
            risk_score=0.6,
            assigned_reviewer_id="reviewer_2",
            assigned_at=now,
            sla_deadline=future_deadline,
            status="assigned",
            created_at=now,
            payout_eligible_inr=500.0,
            trust_tier="trusted",
        )

        async def mock_smembers(key):
            # Only return the queue for priority 2
            if "priority:2" in key:
                return {"queue_2"}
            return set()

        async def mock_get(k):
            if "queue_2" in k:
                return pending_item.model_dump_json()
            return None

        queue_service.redis.smembers = mock_smembers
        queue_service.redis.get = mock_get

        breached = await queue_service.sla_breach_check()

        # Should identify 0 breached items
        assert len(breached) == 0
