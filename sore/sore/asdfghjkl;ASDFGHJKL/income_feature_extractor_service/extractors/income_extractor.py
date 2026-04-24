import yaml
from pathlib import Path
from datetime import datetime
from ..schemas.income_features import IncomeSignalFeatures
from ..repositories.worker_profile_repository import WorkerProfileRepository
from ..repositories.worker_loss_session_repository import WorkerLossSessionRepository
from ..services.worker_earnings_service import WorkerEarningsService

class IncomeFeatureExtractor:
    def __init__(self, profile_repo: WorkerProfileRepository, loss_repo: WorkerLossSessionRepository, earnings_service: WorkerEarningsService, config_path: str):
        self.profile_repo = profile_repo
        self.loss_repo = loss_repo
        self.earnings_service = earnings_service
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

    async def extract(self, aligned_event: dict) -> IncomeSignalFeatures:
        worker_id = aligned_event['worker_id']
        minute_bucket = aligned_event['minute_bucket']
        zone_id = aligned_event.get('delivery_zone_id')
        attempts = aligned_event.get('sum_delivery_attempts', 0)
        disruption_index = aligned_event.get('composite_disruption_index', 0.0)
        trigger_active = aligned_event.get('any_trigger_active', False)

        # Get profile
        profile = await self.profile_repo.get_profile(worker_id)
        if not profile:
            # Default
            profile = type('Profile', (), {
                'base_hourly_rate_inr': 100.0,
                'historical_avg_deliveries_per_hr': 8.0,
                'historical_avg_earnings_per_hr': 80.0
            })()

        # Expected earnings
        base_rate = profile.base_hourly_rate_inr
        zone_mult = await self._get_zone_multiplier(zone_id)
        time_mult = self._get_time_multiplier(minute_bucket)
        expected = base_rate * (1 + zone_mult) * time_mult

        # Actual earnings
        actual = await self.earnings_service.get_earnings(worker_id, minute_bucket) or -1.0

        # Loss
        loss = max(0, expected - actual) if actual != -1.0 else 0.0
        loss_ratio = loss / expected if expected > 0 else 0.0

        # Plausibility
        plausibility = 1 - abs(loss_ratio - disruption_index)
        plausibility = max(0.0, min(1.0, plausibility))
        suspicious_plaus = plausibility < 0.3

        # Delivery rate
        baseline_rate = profile.historical_avg_deliveries_per_hr / 60.0
        delivery_rate = attempts / baseline_rate if baseline_rate > 0 else 0.0
        suspicious_delivery = trigger_active and delivery_rate > 1.1

        # Consistency
        avg_per_delivery = profile.historical_avg_earnings_per_hr / profile.historical_avg_deliveries_per_hr
        implied = attempts * avg_per_delivery
        if implied > 0:
            ratio = actual / implied if actual > 0 else 0.0
            consistency = 1 - min(abs(ratio - 1.0), 1.0)
        else:
            consistency = 1.0

        # Cumulative loss
        prev_cumulative = await self.loss_repo.get_cumulative_loss(worker_id)
        if not trigger_active:
            await self.loss_repo.reset_session(worker_id)
            cumulative = 0.0
        else:
            cumulative = prev_cumulative + loss
            await self.loss_repo.set_cumulative_loss(worker_id, cumulative)

        # Payout
        coverage = self.config['coverage_ratio']
        eligible = loss * coverage if not (suspicious_plaus or suspicious_delivery) else 0.0

        return IncomeSignalFeatures(
            worker_id=worker_id,
            minute_bucket=minute_bucket,
            expected_earnings_inr=expected,
            actual_earnings_inr=actual,
            income_loss_inr=loss,
            income_loss_ratio=loss_ratio,
            loss_plausibility_score=plausibility,
            loss_plausibility_suspicious=suspicious_plaus,
            delivery_rate_vs_baseline=delivery_rate,
            delivery_rate_suspicious=suspicious_delivery,
            earnings_consistency_score=consistency,
            cumulative_loss_session_inr=cumulative,
            payout_eligible_inr=eligible,
            feature_computed_at=datetime.utcnow()
        )

    async def _get_zone_multiplier(self, zone_id: Optional[str]) -> float:
        if zone_id:
            key = f'zone_demand:{zone_id}'
            mult = await self.profile_repo.redis.get(key)
            return float(mult) if mult else self.config['zone_demand_default']
        return self.config['zone_demand_default']

    def _get_time_multiplier(self, minute_bucket: int) -> float:
        hour = (minute_bucket // 60) % 24
        for range_str, mult in self.config['time_of_day_multipliers'].items():
            start, end = map(int, range_str.split('-'))
            if start <= hour <= end:
                return mult
        return 1.0