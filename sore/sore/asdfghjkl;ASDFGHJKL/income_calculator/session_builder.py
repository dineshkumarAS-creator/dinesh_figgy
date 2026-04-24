"""
Disruption session builder.

Aggregates minute-window feature vectors from Feast into
disruption sessions for payout calculation.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID
import logging

from income_calculator.schemas import DisruptionSession
from income_calculator.config import payout_config

logger = logging.getLogger(__name__)


class DisruptionSessionBuilder:
    """
    Builds disruption sessions from minute-window feature vectors.
    
    A session = all consecutive trigger-active windows for a worker.
    Multiple windows aggregated into single session for payout.
    """
    
    def __init__(self):
        """Initialize builder."""
        self.config = payout_config
    
    async def build_session(
        self,
        claim_id: UUID,
        worker_id: str,
        feature_vectors: list[dict],
        worker_historical_avg_earnings_per_hr: float,
    ) -> DisruptionSession:
        """
        Build disruption session from feature vectors.
        
        Args:
            claim_id: Claim identifier
            worker_id: Worker identifier
            feature_vectors: List of minute-window feature vectors from Feast
                Each vector includes:
                - timestamp: datetime
                - expected_earnings_inr: float (per minute)
                - actual_earnings_inr: float (per minute, -1.0 if pending)
                - composite_disruption_index: float (0-1)
                - trigger_types: list[str]
                - delivery_attempts: int
            worker_historical_avg_earnings_per_hr: Historical avg earnings/hour
        
        Returns:
            DisruptionSession with aggregated metrics
        """
        
        if not feature_vectors:
            logger.warning(f"No feature vectors for claim {claim_id}")
            return self._empty_session(claim_id, worker_id)
        
        # Sort vectors by timestamp
        sorted_vectors = sorted(
            feature_vectors,
            key=lambda v: v.get("timestamp", datetime.now(timezone.utc))
        )
        
        # Aggregate metrics
        session_start = sorted_vectors[0]["timestamp"]
        session_end = sorted_vectors[-1]["timestamp"]
        
        # Calculate total duration in minutes
        total_duration = (session_end - session_start).total_seconds() / 60.0
        total_duration_minutes = int(round(total_duration)) + 1  # +1 to include end minute
        
        # Collect all trigger types
        trigger_types = set()
        
        # Earnings aggregation
        total_expected_earnings_inr = 0.0
        total_actual_earnings_inr = 0.0
        windows_with_pending = 0
        
        # Disruption metrics
        disruption_indices = []
        total_delivery_attempts = 0
        
        # Data completeness tracking
        complete_windows = 0
        
        for vector in sorted_vectors:
            # Trigger types
            triggers = vector.get("trigger_types", [])
            if triggers:
                trigger_types.update(triggers)
            
            # Earnings
            expected = float(vector.get("expected_earnings_inr", 0.0))
            actual = float(vector.get("actual_earnings_inr", -1.0))
            
            total_expected_earnings_inr += expected
            
            # Handle pending earnings: use conservative estimate
            if actual < 0:  # -1.0 sentinel for pending
                windows_with_pending += 1
                # Estimate as: historical_avg × (1 - disruption_index) × conservative_factor
                disruption_idx = float(vector.get("composite_disruption_index", 0.5))
                estimated_actual = (
                    worker_historical_avg_earnings_per_hr / 60.0  # per minute
                    * (1.0 - disruption_idx)
                    * self.config.PENDING_EARNINGS_ESTIMATE_CONSERVATIVE
                )
                total_actual_earnings_inr += estimated_actual
            else:
                total_actual_earnings_inr += actual
                complete_windows += 1
            
            # Disruption index
            disruption_idx = float(vector.get("composite_disruption_index", 0.5))
            disruption_indices.append(disruption_idx)
            
            # Delivery attempts
            attempts = vector.get("delivery_attempts", 0)
            total_delivery_attempts += attempts
        
        # Calculate aggregated disruption metrics
        avg_disruption_index = (
            sum(disruption_indices) / len(disruption_indices)
            if disruption_indices
            else 0.5
        )
        peak_disruption_index = max(disruption_indices) if disruption_indices else 0.5
        
        # Data completeness: fraction of windows with data
        data_completeness = (
            complete_windows / len(sorted_vectors)
            if sorted_vectors
            else 0.0
        )
        
        session = DisruptionSession(
            claim_id=claim_id,
            worker_id=worker_id,
            session_start=session_start,
            session_end=session_end,
            total_duration_minutes=total_duration_minutes,
            trigger_types=sorted(list(trigger_types)),
            avg_disruption_index=avg_disruption_index,
            peak_disruption_index=peak_disruption_index,
            total_delivery_attempts=total_delivery_attempts,
            total_expected_earnings_inr=total_expected_earnings_inr,
            total_actual_earnings_inr=total_actual_earnings_inr,
            windows_with_pending_earnings=windows_with_pending,
            data_completeness=data_completeness,
        )
        
        logger.info(
            "session_built",
            claim_id=str(claim_id),
            worker_id=worker_id,
            duration_min=total_duration_minutes,
            expected_inr=total_expected_earnings_inr,
            actual_inr=total_actual_earnings_inr,
            completeness=data_completeness,
        )
        
        return session
    
    @staticmethod
    def _empty_session(claim_id: UUID, worker_id: str) -> DisruptionSession:
        """Return empty session (zero earnings)."""
        now = datetime.now(timezone.utc)
        return DisruptionSession(
            claim_id=claim_id,
            worker_id=worker_id,
            session_start=now,
            session_end=now,
            total_duration_minutes=0,
            trigger_types=[],
            avg_disruption_index=0.0,
            peak_disruption_index=0.0,
            total_delivery_attempts=0,
            total_expected_earnings_inr=0.0,
            total_actual_earnings_inr=0.0,
            windows_with_pending_earnings=0,
            data_completeness=0.0,
        )
