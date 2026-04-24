import pytest
from unittest.mock import AsyncMock
from ..extractors.income_extractor import IncomeFeatureExtractor
from ..services.worker_profile_service import WorkerProfile
from ..services.worker_earnings_service import FakeWorkerEarningsService

@pytest.mark.asyncio
async def test_expected_earnings():
    profile_repo = AsyncMock()
    loss_repo = AsyncMock()
    earnings_service = FakeWorkerEarningsService()
    extractor = IncomeFeatureExtractor(profile_repo, loss_repo, earnings_service, 'config/income_config.yaml')

    profile_repo.get_profile.return_value = WorkerProfile(
        worker_tier='silver',
        base_hourly_rate_inr=150.0,
        historical_avg_deliveries_per_hr=10.0,
        historical_avg_earnings_per_hr=120.0,
        enrollment_date='2023-01-01'
    )
    profile_repo.redis.get.return_value = None  # No zone mult

    event = {
        'worker_id': 'w1',
        'minute_bucket': 720,  # 12:00
        'sum_delivery_attempts': 1,
        'composite_disruption_index': 0.5,
        'any_trigger_active': True
    }

    features = await extractor.extract(event)
    assert features.expected_earnings_inr == 150.0 * 1.15 * 1.2  # base * (1+0.15) * 1.2

@pytest.mark.asyncio
async def test_loss_plausibility():
    profile_repo = AsyncMock()
    loss_repo = AsyncMock()
    earnings_service = FakeWorkerEarningsService()
    extractor = IncomeFeatureExtractor(profile_repo, loss_repo, earnings_service, 'config/income_config.yaml')

    profile_repo.get_profile.return_value = WorkerProfile(
        worker_tier='silver',
        base_hourly_rate_inr=100.0,
        historical_avg_deliveries_per_hr=10.0,
        historical_avg_earnings_per_hr=80.0,
        enrollment_date='2023-01-01'
    )
    profile_repo.redis.get.return_value = None

    event = {
        'worker_id': 'w1',
        'minute_bucket': 600,  # 10:00
        'sum_delivery_attempts': 0,
        'composite_disruption_index': 0.8,
        'any_trigger_active': True
    }

    features = await extractor.extract(event)
    # Expected ~100, actual 100, loss 0, ratio 0, plaus 1-0.8=0.2 <0.3 suspicious
    assert features.loss_plausibility_suspicious

@pytest.mark.asyncio
async def test_payout_eligible():
    profile_repo = AsyncMock()
    loss_repo = AsyncMock()
    earnings_service = FakeWorkerEarningsService()
    extractor = IncomeFeatureExtractor(profile_repo, loss_repo, earnings_service, 'config/income_config.yaml')

    profile_repo.get_profile.return_value = WorkerProfile(
        worker_tier='silver',
        base_hourly_rate_inr=100.0,
        historical_avg_deliveries_per_hr=10.0,
        historical_avg_earnings_per_hr=80.0,
        enrollment_date='2023-01-01'
    )
    profile_repo.redis.get.return_value = None

    event = {
        'worker_id': 'w1',
        'minute_bucket': 600,
        'sum_delivery_attempts': 0,
        'composite_disruption_index': 0.8,
        'any_trigger_active': True
    }

    features = await extractor.extract(event)
    # Since suspicious, eligible 0
    assert features.payout_eligible_inr == 0.0