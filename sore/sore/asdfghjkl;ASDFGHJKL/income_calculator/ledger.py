"""
Payout ledger: PostgreSQL-backed payment tracking.

Two tables:
1. payout_calculations: Append-only calculation history (audit trail)
2. payout_ledger: Current/historical payout records (payment status)
"""

from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4
import json
import logging

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from income_calculator.schemas import PayoutCalculation, PayoutLedgerEntry

logger = logging.getLogger(__name__)


class PayoutLedgerService:
    """
    Manage payout calculations and ledger entries in PostgreSQL.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize ledger service.
        
        Args:
            db_session: SQLAlchemy async session
        """
        self.db = db_session
    
    async def record_calculation(
        self,
        calculation: PayoutCalculation,
        calculated_by: str = "auto",
    ) -> UUID:
        """
        Record payout calculation (append-only).
        
        Args:
            calculation: PayoutCalculation object
            calculated_by: "auto" or reviewer_id
        
        Returns:
            calculation_id (UUID)
        """
        from manual_review.models import PayoutCalculationsRecord
        
        calculation_id = uuid4()
        
        record = PayoutCalculationsRecord(
            calculation_id=calculation_id,
            claim_id=calculation.claim_id,
            worker_id=calculation.worker_id,
            calculation_json=calculation.model_dump_json(),
            calculated_by=calculated_by,
            created_at=datetime.now(timezone.utc),
        )
        
        self.db.add(record)
        await self.db.flush()
        
        logger.info(
            "calculation_recorded",
            calculation_id=str(calculation_id),
            claim_id=str(calculation.claim_id),
            worker_id=calculation.worker_id,
            payout_inr=calculation.final_payout_inr,
        )
        
        return calculation_id
    
    async def create_payout_record(
        self,
        calculation_id: UUID,
        calculation: PayoutCalculation,
        payment_method: str = "bank",
    ) -> PayoutLedgerEntry:
        """
        Create payout ledger entry (payment tracking).
        
        Args:
            calculation_id: FK to payout_calculations
            calculation: PayoutCalculation object (for reference)
            payment_method: "bank" | "upi" | "wallet"
        
        Returns:
            PayoutLedgerEntry
        """
        from manual_review.models import PayoutLedgerRecord
        
        ledger_id = uuid4()
        
        record = PayoutLedgerRecord(
            ledger_id=ledger_id,
            claim_id=calculation.claim_id,
            worker_id=calculation.worker_id,
            calculation_id=calculation_id,
            payout_inr=calculation.final_payout_inr,
            payment_method=payment_method,
            payment_status="pending",
            created_at=datetime.now(timezone.utc),
        )
        
        self.db.add(record)
        await self.db.flush()
        
        entry = PayoutLedgerEntry(
            ledger_id=ledger_id,
            claim_id=calculation.claim_id,
            worker_id=calculation.worker_id,
            calculation_id=calculation_id,
            payout_inr=calculation.final_payout_inr,
            payment_method=payment_method,
            payment_status="pending",
            created_at=datetime.now(timezone.utc),
        )
        
        logger.info(
            "ledger_entry_created",
            ledger_id=str(ledger_id),
            claim_id=str(calculation.claim_id),
            worker_id=calculation.worker_id,
            payout_inr=calculation.final_payout_inr,
        )
        
        return entry
    
    async def update_payment_status(
        self,
        ledger_id: UUID,
        status: str,
        payment_ref: Optional[str] = None,
    ) -> PayoutLedgerEntry:
        """
        Update payment status for a ledger entry.
        
        Args:
            ledger_id: Ledger entry ID
            status: "processing" | "success" | "failed" | "refunded"
            payment_ref: Bank/UPI reference when successful
        
        Returns:
            Updated PayoutLedgerEntry
        """
        from manual_review.models import PayoutLedgerRecord
        
        stmt = select(PayoutLedgerRecord).where(
            PayoutLedgerRecord.ledger_id == ledger_id
        )
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()
        
        if not record:
            raise ValueError(f"Ledger entry {ledger_id} not found")
        
        record.payment_status = status
        record.payment_ref = payment_ref
        
        if status == "processing":
            record.payment_initiated_at = datetime.now(timezone.utc)
        elif status == "success":
            record.payment_confirmed_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        
        entry = PayoutLedgerEntry(
            ledger_id=record.ledger_id,
            claim_id=record.claim_id,
            worker_id=record.worker_id,
            calculation_id=record.calculation_id,
            payout_inr=record.payout_inr,
            payment_method=record.payment_method,
            payment_status=record.payment_status,
            payment_ref=record.payment_ref,
            payment_initiated_at=record.payment_initiated_at,
            payment_confirmed_at=record.payment_confirmed_at,
            created_at=record.created_at,
        )
        
        logger.info(
            "payment_status_updated",
            ledger_id=str(ledger_id),
            status=status,
            payment_ref=payment_ref,
        )
        
        return entry
    
    async def get_worker_daily_total(
        self,
        worker_id: str,
        date_utc: date,
    ) -> float:
        """
        Get total payouts for worker on a specific day.
        
        Args:
            worker_id: Worker ID
            date_utc: UTC date
        
        Returns:
            Total payout amount (INR)
        """
        from manual_review.models import PayoutLedgerRecord
        
        start_of_day = datetime.combine(date_utc, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        end_of_day = datetime.combine(date_utc, datetime.max.time()).replace(
            tzinfo=timezone.utc
        )
        
        stmt = select(func.sum(PayoutLedgerRecord.payout_inr)).where(
            and_(
                PayoutLedgerRecord.worker_id == worker_id,
                PayoutLedgerRecord.payment_status == "success",
                PayoutLedgerRecord.created_at >= start_of_day,
                PayoutLedgerRecord.created_at < end_of_day,
            )
        )
        
        result = await self.db.execute(stmt)
        total = result.scalar()
        
        return float(total) if total else 0.0
    
    async def get_worker_monthly_total(
        self,
        worker_id: str,
        year: int,
        month: int,
    ) -> float:
        """
        Get total payouts for worker in a specific month.
        
        Args:
            worker_id: Worker ID
            year: Year (2026)
            month: Month (1-12)
        
        Returns:
            Total payout amount (INR)
        """
        from manual_review.models import PayoutLedgerRecord
        
        start_of_month = datetime(year, month, 1, tzinfo=timezone.utc)
        
        # Calculate next month's first day
        if month == 12:
            end_of_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_of_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        
        stmt = select(func.sum(PayoutLedgerRecord.payout_inr)).where(
            and_(
                PayoutLedgerRecord.worker_id == worker_id,
                PayoutLedgerRecord.payment_status == "success",
                PayoutLedgerRecord.created_at >= start_of_month,
                PayoutLedgerRecord.created_at < end_of_month,
            )
        )
        
        result = await self.db.execute(stmt)
        total = result.scalar()
        
        return float(total) if total else 0.0
    
    async def get_pending_payouts(
        self,
        worker_id: Optional[str] = None,
    ) -> list[PayoutLedgerEntry]:
        """
        Get all pending payouts (not yet processed).
        
        Args:
            worker_id: Filter by worker (optional)
        
        Returns:
            List of pending PayoutLedgerEntries
        """
        from manual_review.models import PayoutLedgerRecord
        
        stmt = select(PayoutLedgerRecord).where(
            PayoutLedgerRecord.payment_status == "pending"
        )
        
        if worker_id:
            stmt = stmt.where(PayoutLedgerRecord.worker_id == worker_id)
        
        result = await self.db.execute(stmt)
        records = result.scalars().all()
        
        return [
            PayoutLedgerEntry(
                ledger_id=r.ledger_id,
                claim_id=r.claim_id,
                worker_id=r.worker_id,
                calculation_id=r.calculation_id,
                payout_inr=r.payout_inr,
                payment_method=r.payment_method,
                payment_status=r.payment_status,
                created_at=r.created_at,
            )
            for r in records
        ]
