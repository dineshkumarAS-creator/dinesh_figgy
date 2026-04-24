from dataclasses import dataclass
from typing import Optional, List, Tuple
import numpy as np
from haversine import haversine
from datetime import datetime
from ..schemas.worker_behaviour_features import WorkerBehaviourFeatures
from ..repositories.worker_session_repository import WorkerSessionRepository, WorkerSessionState
from ..clients.osrm_client import OsrmClient

@dataclass
class BehaviourContext:
    last_position: Optional[Tuple[float, float]] = None
    session_state: WorkerSessionState = None
    rolling_speeds: List[float] = None
    app_states: List[str] = None
    osrm_coords: List[Tuple[float, float]] = None

    def __post_init__(self):
        if self.session_state is None:
            self.session_state = WorkerSessionState()
        if self.rolling_speeds is None:
            self.rolling_speeds = []
        if self.app_states is None:
            self.app_states = []
        if self.osrm_coords is None:
            self.osrm_coords = []

class WorkerBehaviourFeatureExtractor:
    def __init__(self, repo: WorkerSessionRepository, osrm_client: OsrmClient):
        self.repo = repo
        self.osrm_client = osrm_client

    async def load_context(self, worker_id: str, aligned_event: dict) -> BehaviourContext:
        last_pos = await self.repo.get_last_position(worker_id)
        session_state = await self.repo.get_session_state(worker_id)
        rolling_speeds = await self.repo.get_rolling_speeds(worker_id)
        app_states = await self.repo.get_app_states(worker_id)

        # OSRM coords: last 5 positions, but since we have current, need to collect
        # For simplicity, assume we store last 4, add current
        osrm_coords = [last_pos] if last_pos else []
        current_pos = (aligned_event['avg_smoothed_lat'], aligned_event['avg_smoothed_lon'])
        osrm_coords.append(current_pos)
        osrm_coords = osrm_coords[-5:]  # Last 5

        return BehaviourContext(
            last_position=last_pos,
            session_state=session_state,
            rolling_speeds=rolling_speeds,
            app_states=app_states,
            osrm_coords=osrm_coords
        )

    def extract(self, aligned_event: dict, context: BehaviourContext) -> WorkerBehaviourFeatures:
        worker_id = aligned_event['worker_id']
        minute_bucket = aligned_event['minute_bucket']

        current_lat = aligned_event['avg_smoothed_lat']
        current_lon = aligned_event['avg_smoothed_lon']
        current_time = minute_bucket

        # GPS displacement
        gps_displacement = 0.0
        if context.last_position:
            prev_lat, prev_lon = context.last_position
            time_gap = current_time - (context.session_state.last_window_time or 0)
            if time_gap <= 600:  # 10 min
                gps_displacement = haversine((prev_lat, prev_lon), (current_lat, current_lon), unit='m')

        # Cumulative displacement
        cumulative = context.session_state.cumulative_displacement_m + gps_displacement

        # Active zone minutes
        zone_id = aligned_event.get('delivery_zone_id')
        active_zone_mins = 0
        if zone_id and aligned_event['stationary_pct'] < 0.8:
            active_zone_mins = context.session_state.zone_minutes_map.get(zone_id, 0) + 1
        else:
            # Reset
            context.session_state.zone_minutes_map = {}

        # Delivery
        attempts = aligned_event.get('sum_delivery_attempts', 0)
        rate = attempts * 60

        # Motion continuity
        continuity = self._compute_motion_continuity(
            gps_displacement, aligned_event['max_speed_ms'] * 3.6,  # kmh
            aligned_event['stationary_pct'], context.rolling_speeds
        )

        # Road match
        road_match = -1.0
        if context.osrm_coords:
            # This would be async, but since extract is sync, assume preloaded
            # For now, placeholder
            road_match = 0.8  # Mock

        # App foreground ratio
        foreground_count = sum(1 for s in context.app_states if s == 'foreground')
        ratio = foreground_count / len(context.app_states) if context.app_states else 0.0

        # Speed anomaly
        anomalies = aligned_event.get('speed_outlier_flags', 0)

        # Quality
        quality = aligned_event.get('avg_data_quality_score', 1.0)
        if road_match == -1.0:
            quality -= 0.2
        # Session reset check
        if context.session_state.last_window_time and current_time - context.session_state.last_window_time > 300:
            quality -= 0.1
        quality = max(0.0, min(1.0, quality))

        return WorkerBehaviourFeatures(
            worker_id=worker_id,
            minute_bucket=minute_bucket,
            gps_displacement_m=gps_displacement,
            cumulative_displacement_m=cumulative,
            active_zone_minutes=active_zone_mins,
            delivery_attempt_count=attempts,
            delivery_attempt_rate_per_hr=rate,
            motion_continuity_score=continuity,
            road_match_score=road_match,
            app_foreground_ratio=ratio,
            speed_anomaly_count=anomalies,
            behaviour_feature_quality=quality,
            feature_computed_at=datetime.utcnow()
        )

    async def save_context(self, worker_id: str, context: BehaviourContext, aligned_event: dict):
        # Update session
        current_time = aligned_event['minute_bucket']
        if context.session_state.last_window_time and current_time - context.session_state.last_window_time > 300:
            # Reset session
            context.session_state = WorkerSessionState(session_start=current_time)
        context.session_state.last_window_time = current_time
        context.session_state.cumulative_displacement_m = aligned_event['cumulative_displacement_m']  # From features
        zone_id = aligned_event.get('delivery_zone_id')
        if zone_id:
            context.session_state.zone_minutes_map[zone_id] = aligned_event['active_zone_minutes']

        await self.repo.set_session_state(worker_id, context.session_state)
        await self.repo.set_last_position(worker_id, aligned_event['avg_smoothed_lat'], aligned_event['avg_smoothed_lon'])
        await self.repo.add_speed(worker_id, aligned_event['max_speed_ms'] * 3.6, current_time)
        await self.repo.add_app_state(worker_id, aligned_event['majority_app_state'], current_time)

    def _compute_motion_continuity(self, displacement: float, avg_speed_kmh: float, stationary_pct: float, rolling_speeds: List[float]) -> float:
        # Speed variance penalty
        if rolling_speeds:
            speed_std = np.std(rolling_speeds)
            variance_penalty = 1 - min(speed_std / 30.0, 1.0)
        else:
            variance_penalty = 0.5

        # Displacement consistency
        expected_disp = avg_speed_kmh * (1000 / 60)  # m per min
        if expected_disp > 0:
            consistency = 1 - abs(displacement - expected_disp) / max(expected_disp, 1)
        else:
            consistency = 1.0 if displacement < 1 else 0.0

        # Stationary bonus
        if stationary_pct > 0.8:
            stationary_bonus = 1.0 if displacement < 50 else 0.0
        else:
            stationary_bonus = 1.0 if displacement > 10 else 0.0  # Should move

        score = (variance_penalty + consistency + stationary_bonus) / 3
        return max(0.0, min(1.0, score))