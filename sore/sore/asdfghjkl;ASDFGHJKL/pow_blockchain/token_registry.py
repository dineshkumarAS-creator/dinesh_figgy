"""
PoW Token Registry

Manages PostgreSQL storage of minted tokens and tracks
on-chain payout events.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)

Base = declarative_base()


class PoWTokenRecord(BaseModel):
    """In-memory representation of PoW token."""
    
    token_id: int
    claim_id: UUID
    worker_id: str
    tx_hash: str
    block_number: int
    network: str  # "mumbai" | "polygon"
    ipfs_uri: str
    feature_vector_hash: str
    payout_released: bool = False
    gas_used: int
    minted_at: datetime


class PoWTokenModel(Base):
    """SQLAlchemy ORM model for pow_tokens table."""
    
    __tablename__ = "pow_tokens"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    claim_id = Column(PG_UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Data
    token_id = Column(Integer, nullable=False, unique=True, index=True)
    worker_id = Column(String(255), nullable=False, index=True)
    tx_hash = Column(String(255), nullable=False, unique=True, index=True)
    block_number = Column(Integer, nullable=False)
    network = Column(String(50), nullable=False)  # "mumbai" | "polygon" | "localhost"
    ipfs_uri = Column(String(512), nullable=False)
    feature_vector_hash = Column(String(255), nullable=False)
    
    # Status
    payout_released = Column(Boolean, default=False, nullable=False)
    
    # Gas tracking
    gas_used = Column(Integer, default=0)
    
    # Timestamps
    minted_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )


class TokenRegistryService:
    """
    Manages PoW token records in PostgreSQL.
    
    Responsibilities:
    - Save minted tokens to DB
    - Track payout releases
    - Query token history
    - Listen for PayoutReleased events (background task)
    """
    
    async def save_token(
        self,
        session: AsyncSession,
        token_id: int,
        claim_id: UUID,
        worker_id: str,
        tx_hash: str,
        block_number: int,
        network: str,
        ipfs_uri: str,
        feature_vector_hash: str,
        gas_used: int,
        minted_at: datetime,
    ) -> PoWTokenModel:
        """
        Save minted token to database.
        
        Args:
            session: SQLAlchemy async session
            token_id: On-chain token ID
            claim_id: FIGGY claim UUID
            worker_id: Worker identifier
            tx_hash: Transaction hash
            block_number: Block where minted
            network: Network name
            ipfs_uri: IPFS metadata URI
            feature_vector_hash: SHA-256 of feature vector
            gas_used: Gas consumed
            minted_at: Timestamp of mint
            
        Returns:
            Saved PoWTokenModel record
            
        Raises:
            sqlalchemy.exc.IntegrityError: If claim_id or token_id already exists
        """
        record = PoWTokenModel(
            claim_id=claim_id,
            token_id=token_id,
            worker_id=worker_id,
            tx_hash=tx_hash,
            block_number=block_number,
            network=network,
            ipfs_uri=ipfs_uri,
            feature_vector_hash=feature_vector_hash,
            payout_released=False,
            gas_used=gas_used,
            minted_at=minted_at,
        )
        
        session.add(record)
        await session.flush()
        
        logger.info(f"💾 Saved PoW token {token_id} for claim {claim_id}")
        
        return record
    
    async def get_token_by_claim(
        self,
        session: AsyncSession,
        claim_id: UUID,
    ) -> Optional[PoWTokenModel]:
        """
        Retrieve token by claim ID.
        
        Args:
            session: SQLAlchemy async session
            claim_id: Claim UUID
            
        Returns:
            PoWTokenModel or None if not found
        """
        stmt = select(PoWTokenModel).where(PoWTokenModel.claim_id == claim_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_token_by_id(
        self,
        session: AsyncSession,
        token_id: int,
    ) -> Optional[PoWTokenModel]:
        """
        Retrieve token by on-chain token ID.
        
        Args:
            session: SQLAlchemy async session
            token_id: On-chain token ID
            
        Returns:
            PoWTokenModel or None if not found
        """
        stmt = select(PoWTokenModel).where(PoWTokenModel.token_id == token_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def mark_payout_released(
        self,
        session: AsyncSession,
        token_id: int,
    ) -> bool:
        """
        Mark token as paid out (when PayoutReleased event observed).
        
        Args:
            session: SQLAlchemy async session
            token_id: On-chain token ID
            
        Returns:
            True if updated, False if token not found
        """
        record = await self.get_token_by_id(session, token_id)
        
        if not record:
            logger.warning(f"Token {token_id} not found for payout release")
            return False
        
        record.payout_released = True
        record.updated_at = datetime.now(timezone.utc)
        
        await session.flush()
        
        logger.info(f"✅ Marked token {token_id} as payout released")
        
        return True
    
    async def get_tokens_by_worker(
        self,
        session: AsyncSession,
        worker_id: str,
        limit: int = 100,
    ) -> list[PoWTokenModel]:
        """
        Retrieve all tokens for a worker.
        
        Args:
            session: SQLAlchemy async session
            worker_id: Worker identifier
            limit: Max results
            
        Returns:
            List of PoWTokenModels
        """
        stmt = (
            select(PoWTokenModel)
            .where(PoWTokenModel.worker_id == worker_id)
            .order_by(PoWTokenModel.minted_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_unpaid_tokens(
        self,
        session: AsyncSession,
        limit: int = 100,
    ) -> list[PoWTokenModel]:
        """
        Retrieve tokens where payout not yet released.
        
        Args:
            session: SQLAlchemy async session
            limit: Max results
            
        Returns:
            List of unpaid tokens
        """
        stmt = (
            select(PoWTokenModel)
            .where(PoWTokenModel.payout_released == False)
            .order_by(PoWTokenModel.minted_at.asc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_token_stats(
        self,
        session: AsyncSession,
    ) -> dict:
        """
        Get aggregate statistics on PoW tokens.
        
        Returns:
            Dict with:
            - total_tokens: Count of all tokens
            - paid_out: Count where payout_released=true
            - pending: Count where payout_released=false
            - total_gas_used: Sum of gas_used
            - networks: Dict of token counts per network
        """
        # Total count
        total_stmt = select(func.count()).select_from(PoWTokenModel)
        total_result = await session.execute(total_stmt)
        total_tokens = total_result.scalar() or 0
        
        # Paid out count
        paid_stmt = select(func.count()).select_from(PoWTokenModel).where(
            PoWTokenModel.payout_released == True
        )
        paid_result = await session.execute(paid_stmt)
        paid_out = paid_result.scalar() or 0
        
        # Total gas
        gas_stmt = select(func.sum(PoWTokenModel.gas_used)).select_from(PoWTokenModel)
        gas_result = await session.execute(gas_stmt)
        total_gas = gas_result.scalar() or 0
        
        stats = {
            "total_tokens": total_tokens,
            "paid_out": paid_out,
            "pending": total_tokens - paid_out,
            "total_gas_used": total_gas,
            "networks": {},
        }
        
        return stats


# Additional imports for stats query
from sqlalchemy import func
