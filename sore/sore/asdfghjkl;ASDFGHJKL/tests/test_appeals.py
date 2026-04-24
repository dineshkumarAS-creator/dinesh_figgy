"""
Tests for Appeals Flow

Tests appeal submission, SLA tracking, overturn mechanics, and state transitions.
"""

import pytest
from datetime import datetime, timedelta, timezone
from manual_review.appeals import AppealService
from manual_review.queue import ReviewQueueService
from manual_review.schemas import Appeal
from unittest.mock import AsyncMock


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    return AsyncMock()


@pytest.fixture
def mock_queue_service(mock_redis):
    """Mock queue service."""
    return AsyncMock(spec=ReviewQueueService)


@pytest.fixture
def appeal_service(mock_redis, mock_queue_service):
    """Create appeal service."""
    return AppealService(
        redis_client=mock_redis,
        queue_service=mock_queue_service,
    )


# ==============================================================================
# Appeal Submission Tests
# ==============================================================================


class TestAppealSubmission:
    """Test appeal creation and state transitions."""

    @pytest.mark.asyncio
    async def test_submit_appeal_creates_record(self, appeal_service, mock_redis):
        """Submitting appeal creates Appeal record and stores in Redis."""
        mock_redis.get = AsyncMock(return_value="REJECTED")
        mock_redis.set = AsyncMock()

        appeal = await appeal_service.submit_appeal(
            claim_id="claim_1",
            worker_id="worker_1",
            appeal_reason="GPS glitch caused false rejection",
            evidence_urls=["https://example.com/photo.jpg"],
        )

        # Verify appeal created
        assert appeal.claim_id == "claim_1"
        assert appeal.worker_id == "worker_1"
        assert appeal.status == "pending"
        assert "GPS glitch" in appeal.appeal_reason
        assert len(appeal.evidence_urls) == 1

    @pytest.mark.asyncio
    async def test_submit_appeal_requires_rejected_status(self, appeal_service, mock_redis):
        """Can only appeal REJECTED claims."""
        # Claim is in APPROVED state, not REJECTED
        mock_redis.get = AsyncMock(return_value="APPROVED")

        with pytest.raises(ValueError, match="Can only appeal REJECTED claims"):
            await appeal_service.submit_appeal(
                claim_id="claim_2",
                worker_id="worker_2",
                appeal_reason="Wrong decision",
            )

    @pytest.mark.asyncio
    async def test_submit_appeal_transitions_claim_state(
        self, appeal_service, mock_redis
    ):
        """Submitting appeal transitions claim state REJECTED → APPEALED."""
        mock_redis.get = AsyncMock(return_value="REJECTED")
        mock_redis.set = AsyncMock()

        await appeal_service.submit_appeal(
            claim_id="claim_3",
            worker_id="worker_3",
            appeal_reason="Reason",
        )

        # Verify state transition call
        set_calls = [call for call in mock_redis.set.call_args_list]

        # One of the set calls should be to claim:status with "APPEALED"
        state_transition_found = any(
            "claim:status:claim_3" in str(call) and "APPEALED" in str(call)
            for call in set_calls
        )
        assert state_transition_found, "Claim state should transition to APPEALED"

    @pytest.mark.asyncio
    async def test_submit_appeal_enqueues_as_priority_1(
        self, appeal_service, mock_redis, mock_queue_service
    ):
        """Appeal is enqueued as PRIORITY=1 (CRITICAL) for fast review."""
        mock_redis.get = AsyncMock(return_value="REJECTED")
        mock_redis.set = AsyncMock()

        from manual_review.schemas import ReviewQueueItem

        mock_queue_item = ReviewQueueItem(
            queue_id="queue_appeal_1",
            claim_id="claim_4",
            worker_id="worker_4",
            priority=1,  # CRITICAL
            risk_score=0.9,
            assigned_reviewer_id=None,
            assigned_at=None,
            sla_deadline=datetime.now(timezone.utc) + timedelta(hours=24),
            status="pending",
            created_at=datetime.now(timezone.utc),
            payout_eligible_inr=1000.0,
            trust_tier="flagged",
        )

        mock_queue_service.enqueue = AsyncMock(return_value=mock_queue_item)

        appeal = await appeal_service.submit_appeal(
            claim_id="claim_4",
            worker_id="worker_4",
            appeal_reason="Reason",
        )

        # Verify queue service called with PRIORITY=1 parameters
        mock_queue_service.enqueue.assert_called_once()
        call_kwargs = mock_queue_service.enqueue.call_args[1]

        # High payout (₹1000) and flagged trust tier force priority=1
        assert call_kwargs["payout_eligible_inr"] == 1000.0
        assert call_kwargs["trust_tier"] == "flagged"

        # Queue item linked to appeal
        assert appeal.queue_item_id == "queue_appeal_1"


# ==============================================================================
# Appeal Decision Tests
# ==============================================================================


class TestAppealDecision:
    """Test appeal decision mechanics."""

    @pytest.mark.asyncio
    async def test_appeal_approved_transitions_to_payout_processing(
        self, appeal_service, mock_redis
    ):
        """Approving appeal transitions claim APPEALED → PAYOUT_PROCESSING."""
        now = datetime.now(timezone.utc)

        appeal = Appeal(
            appeal_id="appeal_1",
            claim_id="claim_5",
            worker_id="worker_5",
            appeal_reason="Reason",
            status="pending",
            submitted_at=now,
        )

        mock_redis.get = AsyncMock(return_value=appeal.model_dump_json())
        mock_redis.set = AsyncMock()

        decided_appeal = await appeal_service.decide_appeal(
            appeal_id="appeal_1",
            decision="approved",
            reviewer_id="reviewer_lead_1",
            decision_notes="Evidence supports worker's claim",
        )

        # Verify appeal status changed
        assert decided_appeal.status == "approved"
        assert decided_appeal.reviewer_id == "reviewer_lead_1"
        assert decided_appeal.resolved_at is not None

        # Verify claim state transition
        set_calls = [call for call in mock_redis.set.call_args_list]
        transition_found = any(
            "claim:status:claim_5" in str(call) and "PAYOUT_PROCESSING" in str(call)
            for call in set_calls
        )
        assert transition_found, "Claim should transition to PAYOUT_PROCESSING"

    @pytest.mark.asyncio
    async def test_appeal_rejected_final_decision(self, appeal_service, mock_redis):
        """Rejecting appeal transitions claim APPEALED → APPEAL_REJECTED (final)."""
        now = datetime.now(timezone.utc)

        appeal = Appeal(
            appeal_id="appeal_2",
            claim_id="claim_6",
            worker_id="worker_6",
            appeal_reason="Reason",
            status="pending",
            submitted_at=now,
        )

        mock_redis.get = AsyncMock(return_value=appeal.model_dump_json())
        mock_redis.set = AsyncMock()

        decided_appeal = await appeal_service.decide_appeal(
            appeal_id="appeal_2",
            decision="rejected",
            reviewer_id="reviewer_lead_2",
            decision_notes="Original decision upheld",
        )

        assert decided_appeal.status == "rejected"

        # Verify claim state transition to APPEAL_REJECTED (non-recoverable)
        set_calls = [call for call in mock_redis.set.call_args_list]
        transition_found = any(
            "claim:status:claim_6" in str(call) and "APPEAL_REJECTED" in str(call)
            for call in set_calls
        )
        assert transition_found, "Claim should transition to APPEAL_REJECTED"

    @pytest.mark.asyncio
    async def test_cannot_decide_non_pending_appeal(self, appeal_service, mock_redis):
        """Cannot decide on appeal that's not pending."""
        now = datetime.now(timezone.utc)

        appeal = Appeal(
            appeal_id="appeal_3",
            claim_id="claim_7",
            worker_id="worker_7",
            appeal_reason="Reason",
            status="approved",  # Already decided
            submitted_at=now,
            resolved_at=now,
        )

        mock_redis.get = AsyncMock(return_value=appeal.model_dump_json())

        with pytest.raises(ValueError, match="Cannot decide on approved appeal"):
            await appeal_service.decide_appeal(
                appeal_id="appeal_3",
                decision="rejected",
                reviewer_id="reviewer_1",
                decision_notes="This should fail",
            )


# ==============================================================================
# Appeal SLA Tests
# ==============================================================================


class TestAppealSLA:
    """Test 24-hour SLA for appeals."""

    @pytest.mark.asyncio
    async def test_appeal_sla_24_hours(self, appeal_service):
        """Appeal has 24-hour SLA from submission."""
        now = datetime.now(timezone.utc)

        appeal = Appeal(
            appeal_id="appeal_4",
            claim_id="claim_8",
            worker_id="worker_8",
            appeal_reason="GPS malfunction",
            status="pending",
            submitted_at=now,
        )

        expected_deadline = now + timedelta(hours=24)

        # In production: appeal item enqueued at queue_item.sla_deadline = expected_deadline
        # Verify SLA hours
        assert AppealService.APPEAL_SLA_HOURS == 24


# ==============================================================================
# Appeal Overturn Rate Tests
# ==============================================================================


class TestAppealOverturnRate:
    """Test appeal overturn metrics."""

    @pytest.mark.asyncio
    async def test_appeal_overturn_rate_calculation(self, appeal_service, mock_redis):
        """Overturn rate = approved_appeals / total_decided_appeals."""
        now = datetime.now(timezone.utc)

        appeals = [
            Appeal(
                appeal_id=f"appeal_{i}",
                claim_id=f"claim_{i}",
                worker_id=f"worker_{i}",
                appeal_reason="Reason",
                status="approved" if i < 3 else "rejected",
                submitted_at=now,
                resolved_at=now,
            )
            for i in range(7)
        ]

        # 3 approved, 4 rejected → overturn rate = 3/7 ≈ 0.43

        async def mock_keys(*args, **kwargs):
            return [f"appeal:appeal_{i}" for i in range(7)]

        async def mock_get(key):
            for appeal in appeals:
                if f"appeal_{appeal.appeal_id}" in key or key.endswith(appeal.appeal_id):
                    return appeal.model_dump_json()
            return None

        mock_redis.keys = AsyncMock(side_effect=mock_keys)
        mock_redis.get = AsyncMock(side_effect=mock_get)

        metrics = await appeal_service.get_appeal_metrics()

        assert metrics["total_appeals"] == 7
        assert metrics["approved"] == 3
        assert metrics["rejected"] == 4
        assert abs(metrics["overturn_rate"] - 3 / 7) < 0.01

    @pytest.mark.asyncio
    async def test_high_overturn_rate_indicates_false_rejections(
        self, appeal_service, mock_redis
    ):
        """
        High overturn rate (>20%) indicates too many false rejections.

        This is a metric that should trigger investigation:
          - >20% means reviewers are too strict
          - <5% means reviewers are too lenient
        """
        now = datetime.now(timezone.utc)

        # Create 20 appeals: 16 approved, 4 rejected → 80% overturn rate (too high!)
        appeals = [
            Appeal(
                appeal_id=f"appeal_{i}",
                claim_id=f"claim_{i}",
                worker_id=f"worker_{i}",
                appeal_reason="Reason",
                status="approved" if i < 16 else "rejected",
                submitted_at=now,
                resolved_at=now,
            )
            for i in range(20)
        ]

        async def mock_keys(*args, **kwargs):
            return [f"appeal:appeal_{i}" for i in range(20)]

        async def mock_get(key):
            for appeal in appeals:
                if appeal.appeal_id in key:
                    return appeal.model_dump_json()
            return None

        mock_redis.keys = AsyncMock(side_effect=mock_keys)
        mock_redis.get = AsyncMock(side_effect=mock_get)

        metrics = await appeal_service.get_appeal_metrics()

        # 80% overturn rate - too high, indicates false rejections
        assert metrics["overturn_rate"] > 0.7, "High overturn rate detected"
        # This would trigger alert in production


# ==============================================================================
# Get Appeal Tests
# ==============================================================================


class TestGetAppeal:
    """Test appeal retrieval."""

    @pytest.mark.asyncio
    async def test_get_appeal_by_id(self, appeal_service, mock_redis):
        """Get appeal by ID returns Appeal or None."""
        now = datetime.now(timezone.utc)

        appeal = Appeal(
            appeal_id="appeal_5",
            claim_id="claim_9",
            worker_id="worker_9",
            appeal_reason="Reason",
            status="pending",
            submitted_at=now,
        )

        mock_redis.get = AsyncMock(return_value=appeal.model_dump_json())

        result = await appeal_service.get_appeal("appeal_5")

        assert result is not None
        assert result.appeal_id == "appeal_5"
        assert result.claim_id == "claim_9"

    @pytest.mark.asyncio
    async def test_get_appeal_not_found_returns_none(self, appeal_service, mock_redis):
        """Get non-existent appeal returns None."""
        mock_redis.get = AsyncMock(return_value=None)

        result = await appeal_service.get_appeal("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_appeal_by_claim(self, appeal_service, mock_redis):
        """Get appeal by claim ID."""
        now = datetime.now(timezone.utc)

        appeal = Appeal(
            appeal_id="appeal_6",
            claim_id="claim_10",
            worker_id="worker_10",
            appeal_reason="Reason",
            status="pending",
            submitted_at=now,
        )

        async def mock_get(key):
            if key == "appeal:claim:claim_10":
                return "appeal_6"
            elif key == "appeal:appeal_6":
                return appeal.model_dump_json()
            return None

        mock_redis.get = AsyncMock(side_effect=mock_get)

        result = await appeal_service.get_appeal_by_claim("claim_10")

        assert result is not None
        assert result.appeal_id == "appeal_6"
