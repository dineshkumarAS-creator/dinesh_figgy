"""
Payout calculator test suite.

Tests each calculation step independently, cap enforcement, edge cases.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from income_calculator.session_builder import DisruptionSessionBuilder
from income_calculator.calculator import PayoutCalculator
from income_calculator.schemas import DisruptionSession, WorkerProfile, ClaimRiskScore
from income_calculator.config import payout_config


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def builder():
    """Disruption session builder."""
    return DisruptionSessionBuilder()


@pytest.fixture
def calculator():
    """Payout calculator."""
    return PayoutCalculator()


@pytest.fixture
def sample_session():
    """Sample disruption session for testing."""
    now = datetime.now(timezone.utc)
    return DisruptionSession(
        claim_id=uuid4(),
        worker_id="worker_123",
        session_start=now,
        session_end=now,
        total_duration_minutes=60,
        trigger_types=["curfew"],
        avg_disruption_index=0.75,  # High disruption
        peak_disruption_index=0.9,
        total_delivery_attempts=15,
        total_expected_earnings_inr=500.0,  # Expected ₹500 in 1 hour
        total_actual_earnings_inr=100.0,    # Actual ₹100 (₹400 loss)
        windows_with_pending_earnings=0,
        data_completeness=0.95,
    )


@pytest.fixture
def sample_worker_profile():
    """Sample worker profile."""
    return WorkerProfile(
        worker_id="worker_123",
        trust_tier="silver",
        base_hourly_rate_inr=500.0,
        historical_avg_earnings_per_hr=450.0,
        is_active=True,
    )


@pytest.fixture
def sample_risk_score():
    """Sample ML risk score."""
    return ClaimRiskScore(
        worker_id="worker_123",
        minute_bucket=1713081000,
        composite_claim_score=0.85,
        confidence_level="high",
        disruption_score=0.75,
        anti_spoofing_flag=False,
        top_risk_signals=[],
        score_components={},
    )


# ============================================================================
# GROSS LOSS CALCULATION TESTS
# ============================================================================

class TestGrossLossCalculation:
    """Test income loss calculation (expected - actual)."""
    
    @pytest.mark.asyncio
    async def test_gross_loss_positive(self, calculator, sample_session):
        """Gross loss = expected - actual (positive case)."""
        session = sample_session
        assert session.total_expected_earnings_inr == 500.0
        assert session.total_actual_earnings_inr == 100.0
        
        # Gross loss should be 500 - 100 = 400
        loss = calculator._calculate_gross_loss(session)
        assert float(loss) == 400.0
    
    @pytest.mark.asyncio
    async def test_gross_loss_zero(self, calculator):
        """When actual > expected, loss floors to zero."""
        now = datetime.now(timezone.utc)
        session = DisruptionSession(
            claim_id=uuid4(),
            worker_id="worker_123",
            session_start=now,
            session_end=now,
            total_duration_minutes=60,
            trigger_types=["curfew"],
            avg_disruption_index=0.75,
            peak_disruption_index=0.9,
            total_delivery_attempts=0,
            total_expected_earnings_inr=100.0,
            total_actual_earnings_inr=200.0,  # More than expected!
            windows_with_pending_earnings=0,
            data_completeness=1.0,
        )
        
        loss = calculator._calculate_gross_loss(session)
        assert float(loss) == 0.0


# ============================================================================
# SEVERITY MULTIPLIER TESTS
# ============================================================================

class TestSeverityMultiplier:
    """Test disruption severity adjustment."""
    
    @pytest.mark.asyncio
    async def test_severity_full_payout_at_threshold(self, calculator):
        """At threshold (0.6), multiplier = 1.0 (full coverage)."""
        now = datetime.now(timezone.utc)
        session = DisruptionSession(
            claim_id=uuid4(),
            worker_id="worker_123",
            session_start=now,
            session_end=now,
            total_duration_minutes=60,
            trigger_types=["curfew"],
            avg_disruption_index=0.60,  # Exactly at threshold
            peak_disruption_index=0.65,
            total_delivery_attempts=0,
            total_expected_earnings_inr=500.0,
            total_actual_earnings_inr=100.0,
            windows_with_pending_earnings=0,
            data_completeness=1.0,
        )
        
        multiplier = calculator._calculate_severity_multiplier(session)
        assert multiplier == 1.0
    
    @pytest.mark.asyncio
    async def test_severity_full_payout_above_threshold(self, calculator):
        """Above threshold (0.75), multiplier = 1.0 (full coverage)."""
        now = datetime.now(timezone.utc)
        session = DisruptionSession(
            claim_id=uuid4(),
            worker_id="worker_123",
            session_start=now,
            session_end=now,
            total_duration_minutes=60,
            trigger_types=["curfew", "bandh"],
            avg_disruption_index=0.75,  # High disruption
            peak_disruption_index=0.9,
            total_delivery_attempts=0,
            total_expected_earnings_inr=500.0,
            total_actual_earnings_inr=100.0,
            windows_with_pending_earnings=0,
            data_completeness=1.0,
        )
        
        multiplier = calculator._calculate_severity_multiplier(session)
        assert multiplier == 1.0
    
    @pytest.mark.asyncio
    async def test_severity_prorata_below_threshold(self, calculator):
        """Below threshold, multiplier = avg_disruption_index / threshold."""
        now = datetime.now(timezone.utc)
        session = DisruptionSession(
            claim_id=uuid4(),
            worker_id="worker_123",
            session_start=now,
            session_end=now,
            total_duration_minutes=60,
            trigger_types=["protest"],
            avg_disruption_index=0.30,  # Moderate disruption
            peak_disruption_index=0.35,
            total_delivery_attempts=0,
            total_expected_earnings_inr=500.0,
            total_actual_earnings_inr=300.0,
            windows_with_pending_earnings=0,
            data_completeness=1.0,
        )
        
        multiplier = calculator._calculate_severity_multiplier(session)
        # 0.30 / 0.60 = 0.5 (50% coverage)
        assert abs(multiplier - 0.5) < 0.001


# ============================================================================
# DATA QUALITY ADJUSTMENT TESTS
# ============================================================================

class TestDataQualityAdjustment:
    """Test data completeness penalties."""
    
    @pytest.mark.asyncio
    async def test_high_completeness_no_penalty(self, calculator):
        """Completeness >= 0.6: no penalty (multiplier = 1.0)."""
        now = datetime.now(timezone.utc)
        session = DisruptionSession(
            claim_id=uuid4(),
            worker_id="worker_123",
            session_start=now,
            session_end=now,
            total_duration_minutes=60,
            trigger_types=["curfew"],
            avg_disruption_index=0.75,
            peak_disruption_index=0.9,
            total_delivery_attempts=0,
            total_expected_earnings_inr=500.0,
            total_actual_earnings_inr=100.0,
            windows_with_pending_earnings=0,
            data_completeness=0.95,  # Excellent data
        )
        
        adjustment = calculator._calculate_data_quality_adjustment(session)
        assert adjustment == 1.0
    
    @pytest.mark.asyncio
    async def test_moderate_incompleteness_20_pct_penalty(self, calculator):
        """Completeness < 0.6: 20% penalty (multiplier = 0.8)."""
        now = datetime.now(timezone.utc)
        session = DisruptionSession(
            claim_id=uuid4(),
            worker_id="worker_123",
            session_start=now,
            session_end=now,
            total_duration_minutes=60,
            trigger_types=["curfew"],
            avg_disruption_index=0.75,
            peak_disruption_index=0.9,
            total_delivery_attempts=0,
            total_expected_earnings_inr=500.0,
            total_actual_earnings_inr=100.0,
            windows_with_pending_earnings=15,
            data_completeness=0.45,  # Missing 55% of data
        )
        
        adjustment = calculator._calculate_data_quality_adjustment(session)
        assert adjustment == 0.8
    
    @pytest.mark.asyncio
    async def test_poor_completeness_50_pct_penalty(self, calculator):
        """Completeness < 0.3: 50% penalty (multiplier = 0.5)."""
        now = datetime.now(timezone.utc)
        session = DisruptionSession(
            claim_id=uuid4(),
            worker_id="worker_123",
            session_start=now,
            session_end=now,
            total_duration_minutes=60,
            trigger_types=["curfew"],
            avg_disruption_index=0.75,
            peak_disruption_index=0.9,
            total_delivery_attempts=0,
            total_expected_earnings_inr=500.0,
            total_actual_earnings_inr=100.0,
            windows_with_pending_earnings=50,
            data_completeness=0.20,  # Missing 80% of data!
        )
        
        adjustment = calculator._calculate_data_quality_adjustment(session)
        assert adjustment == 0.5


# ============================================================================
# FULL CALCULATION TESTS
# ============================================================================

class TestFullPayoutCalculation:
    """Test complete payout calculation."""
    
    @pytest.mark.asyncio
    async def test_normal_claim_full_calculation(
        self, calculator, sample_session, sample_worker_profile, sample_risk_score
    ):
        """Full calculation: 500 expected, 100 actual, 0.75 disruption."""
        calculation = await calculator.calculate(
            session=sample_session,
            worker_profile=sample_worker_profile,
            claim_risk_score=sample_risk_score,
            daily_paid_inr=0.0,
            monthly_paid_inr=0.0,
        )
        
        # Expected calculation:
        # 1. Gross loss: 500 - 100 = 400
        # 2. Severity multiplier: 0.75 > 0.6 → 1.0, adjusted = 400
        # 3. Coverage: 400 × 0.67 = 268
        # 4. Data quality: 0.95 → 1.0, so no change = 268
        # 5. No caps applied
        # 6. No flags
        
        assert calculation.gross_loss_inr == 400.0
        assert abs(calculation.final_payout_inr - 268.0) < 0.1
        assert calculation.cap_applied is None
        assert calculation.below_minimum is False
    
    @pytest.mark.asyncio
    async def test_claim_below_minimum(self, calculator, sample_worker_profile, sample_risk_score):
        """Payout below ₹50 → returns ₹0."""
        now = datetime.now(timezone.utc)
        session = DisruptionSession(
            claim_id=uuid4(),
            worker_id="worker_123",
            session_start=now,
            session_end=now,
            total_duration_minutes=60,
            trigger_types=["protest"],
            avg_disruption_index=0.10,  # Very low disruption
            peak_disruption_index=0.15,
            total_delivery_attempts=0,
            total_expected_earnings_inr=100.0,
            total_actual_earnings_inr=95.0,  # Loss = 5
            windows_with_pending_earnings=0,
            data_completeness=1.0,
        )
        
        calculation = await calculator.calculate(
            session=session,
            worker_profile=sample_worker_profile,
            claim_risk_score=sample_risk_score,
            daily_paid_inr=0.0,
            monthly_paid_inr=0.0,
        )
        
        # Loss: 5 → after severity & coverage: ~2.5 → below ₹50 min
        assert calculation.final_payout_inr == 0.0
        assert calculation.below_minimum is True
    
    @pytest.mark.asyncio
    async def test_daily_cap_enforcement(
        self, calculator, sample_session, sample_worker_profile, sample_risk_score
    ):
        """Worker already paid ₹2800 today, new claim capped at ₹200."""
        calculation = await calculator.calculate(
            session=sample_session,
            worker_profile=sample_worker_profile,
            claim_risk_score=sample_risk_score,
            daily_paid_inr=2800.0,  # Already paid ₹2800 today
            monthly_paid_inr=5000.0,
        )
        
        # Daily cap: 3000, remaining: 200
        assert calculation.cap_applied == "daily_cap"
        assert calculation.final_payout_inr == 200.0
        assert calculation.daily_total_after_payout == 3000.0
    
    @pytest.mark.asyncio
    async def test_monthly_cap_enforcement(
        self, calculator, sample_worker_profile, sample_risk_score
    ):
        """Worker already paid ₹14500 this month, new payout capped to ₹500."""
        now = datetime.now(timezone.utc)
        # Create session with high gross loss that would exceed ₹500 payout
        session = DisruptionSession(
            claim_id=uuid4(),
            worker_id="worker_123",
            session_start=now,
            session_end=now,
            total_duration_minutes=60,
            trigger_types=["curfew"],
            avg_disruption_index=0.75,  # Will trigger full 1.0 multiplier
            peak_disruption_index=0.9,
            total_delivery_attempts=15,
            total_expected_earnings_inr=2000.0,  # Higher expected
            total_actual_earnings_inr=100.0,    # Low actual → ₹1900 gross loss
            windows_with_pending_earnings=0,
            data_completeness=0.95,
        )
        
        calculation = await calculator.calculate(
            session=session,
            worker_profile=sample_worker_profile,
            claim_risk_score=sample_risk_score,
            daily_paid_inr=0.0,
            monthly_paid_inr=14500.0,  # Already paid ₹14500 this month
        )
        
        # Gross loss: 2000-100=1900, severity=1.0 (0.75≥0.6)
        # Covered: 1900×0.67≈1273, no data penalty
        # Monthly remaining: 15000-14500=500, so capped to 500
        assert calculation.cap_applied == "monthly_cap", f"Expected monthly_cap but got {calculation.cap_applied}"
        assert calculation.final_payout_inr == 500.0, f"Expected 500.0 but got {calculation.final_payout_inr}"
        assert calculation.monthly_total_after_payout == 15000.0
    
    @pytest.mark.asyncio
    async def test_claim_cap_enforcement(
        self, calculator, sample_worker_profile, sample_risk_score
    ):
        """Claim payout exceeds ₹2000 cap."""
        now = datetime.now(timezone.utc)
        session = DisruptionSession(
            claim_id=uuid4(),
            worker_id="worker_123",
            session_start=now,
            session_end=now,
            total_duration_minutes=120,
            trigger_types=["curfew", "bandh"],
            avg_disruption_index=0.95,  # Extreme disruption
            peak_disruption_index=1.0,
            total_delivery_attempts=0,
            total_expected_earnings_inr=5000.0,  # High expected
            total_actual_earnings_inr=50.0,     # Very low actual
            windows_with_pending_earnings=0,
            data_completeness=1.0,
        )
        
        calculation = await calculator.calculate(
            session=session,
            worker_profile=sample_worker_profile,
            claim_risk_score=sample_risk_score,
            daily_paid_inr=0.0,
            monthly_paid_inr=0.0,
        )
        
        # Gross loss: 4950 × 1.0 severity × 0.67 coverage = 3317 → capped at 2000
        assert calculation.cap_applied == "claim_cap"
        assert calculation.final_payout_inr == 2000.0
    
    @pytest.mark.asyncio
    async def test_gold_tier_bonus(self, calculator, sample_session, sample_risk_score):
        """Gold tier worker gets 5% bonus."""
        gold_worker = WorkerProfile(
            worker_id="worker_gold",
            trust_tier="gold",
            base_hourly_rate_inr=500.0,
            historical_avg_earnings_per_hr=450.0,
            is_active=True,
        )
        
        calculation = await calculator.calculate(
            session=sample_session,
            worker_profile=gold_worker,
            claim_risk_score=sample_risk_score,
            daily_paid_inr=0.0,
            monthly_paid_inr=0.0,
        )
        
        # Normal calc gives ~268, gold bonus: 268 × 1.05 = 281.4
        expected_with_bonus = 268.0 * 1.05
        assert abs(calculation.final_payout_inr - expected_with_bonus) < 0.1
        assert calculation.trust_adjustment_applied is True
    
    @pytest.mark.asyncio
    async def test_flagged_worker_zero_payout(self, calculator, sample_session, sample_risk_score):
        """Flagged worker always gets ₹0."""
        flagged_worker = WorkerProfile(
            worker_id="worker_flagged",
            trust_tier="flagged",
            base_hourly_rate_inr=500.0,
            historical_avg_earnings_per_hr=450.0,
            is_active=False,
        )
        
        calculation = await calculator.calculate(
            session=sample_session,
            worker_profile=flagged_worker,
            claim_risk_score=sample_risk_score,
            daily_paid_inr=0.0,
            monthly_paid_inr=0.0,
        )
        
        assert calculation.final_payout_inr == 0.0


# ============================================================================
# SESSION BUILDER TESTS
# ============================================================================

class TestSessionBuilder:
    """Test disruption session building from feature vectors."""
    
    @pytest.mark.asyncio
    async def test_build_session_normal(self, builder):
        """Build session from typical feature vectors."""
        now = datetime.now(timezone.utc)
        feature_vectors = [
            {
                "timestamp": now,
                "expected_earnings_inr": 10.0,
                "actual_earnings_inr": 2.0,
                "composite_disruption_index": 0.7,
                "trigger_types": ["curfew"],
                "delivery_attempts": 2,
            },
            {
                "timestamp": now,
                "expected_earnings_inr": 10.0,
                "actual_earnings_inr": 3.0,
                "composite_disruption_index": 0.75,
                "trigger_types": ["curfew"],
                "delivery_attempts": 3,
            },
        ]
        
        session = await builder.build_session(
            claim_id=uuid4(),
            worker_id="worker_123",
            feature_vectors=feature_vectors,
            worker_historical_avg_earnings_per_hr=450.0,
        )
        
        assert session.total_expected_earnings_inr == 20.0
        assert session.total_actual_earnings_inr == 5.0
        assert len(session.trigger_types) == 1
        assert "curfew" in session.trigger_types
        assert session.total_delivery_attempts == 5
        assert session.data_completeness == 1.0
    
    @pytest.mark.asyncio
    async def test_build_session_with_pending_earnings(self, builder):
        """Handle pending earnings (-1.0 sentinel)."""
        now = datetime.now(timezone.utc)
        feature_vectors = [
            {
                "timestamp": now,
                "expected_earnings_inr": 10.0,
                "actual_earnings_inr": -1.0,  # Pending!
                "composite_disruption_index": 0.8,
                "trigger_types": ["bandh"],
                "delivery_attempts": 1,
            },
        ]
        
        session = await builder.build_session(
            claim_id=uuid4(),
            worker_id="worker_123",
            feature_vectors=feature_vectors,
            worker_historical_avg_earnings_per_hr=600.0,
        )
        
        # Should estimate actual as: 600/60 × (1-0.8) × 0.7 ≈ 1.4
        assert session.windows_with_pending_earnings == 1
        assert session.total_actual_earnings_inr > 0  # Conservative estimate
        assert session.data_completeness == 0.0  # 0 complete windows
