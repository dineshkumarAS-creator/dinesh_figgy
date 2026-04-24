"""
Income calculator package: precise payout computation for approved claims.

Modules:
- config: Configuration (coverage ratio, caps, thresholds)
- schemas: Pydantic models (DisruptionSession, PayoutCalculation, etc.)
- session_builder: Aggregates feature vectors into disruption sessions
- calculator: Main payout calculation engine
- ledger: PostgreSQL-backed payout tracking
"""

from income_calculator.schemas import (
    DisruptionSession,
    PayoutCalculation,
    PayoutLedgerEntry,
    WorkerProfile,
)
from income_calculator.session_builder import DisruptionSessionBuilder
from income_calculator.calculator import PayoutCalculator
from income_calculator.ledger import PayoutLedgerService

__all__ = [
    "DisruptionSession",
    "PayoutCalculation",
    "PayoutLedgerEntry",
    "WorkerProfile",
    "DisruptionSessionBuilder",
    "PayoutCalculator",
    "PayoutLedgerService",
]
