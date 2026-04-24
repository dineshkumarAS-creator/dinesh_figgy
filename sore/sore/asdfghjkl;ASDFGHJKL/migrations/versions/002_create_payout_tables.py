"""
Alembic migration: create payout_ledger and payout_calculations tables.

Version: 002_create_payout_tables.py
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    """Create payout tables."""
    
    # payout_calculations: Append-only calculation history
    op.create_table(
        'payout_calculations',
        sa.Column('calculation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('worker_id', sa.String(255), nullable=False),
        sa.Column(
            'calculation_json',
            postgresql.JSONB(),
            nullable=False,
            comment="Full PayoutCalculation serialized"
        ),
        sa.Column(
            'calculated_by',
            sa.String(255),
            nullable=False,
            server_default="'auto'",
            comment="'auto' or reviewer_id"
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint('calculation_id'),
    )
    
    op.create_index(
        'ix_payout_calculations_claim_id',
        'payout_calculations',
        ['claim_id'],
    )
    op.create_index(
        'ix_payout_calculations_worker_id',
        'payout_calculations',
        ['worker_id'],
    )
    op.create_index(
        'ix_payout_calculations_created_at',
        'payout_calculations',
        ['created_at'],
    )
    
    # payout_ledger: Payment tracking
    op.create_table(
        'payout_ledger',
        sa.Column('ledger_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('worker_id', sa.String(255), nullable=False),
        sa.Column(
            'calculation_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="FK to payout_calculations"
        ),
        sa.Column(
            'payout_inr',
            sa.Numeric(10, 2),
            nullable=False,
            comment="Payout amount in INR"
        ),
        sa.Column(
            'payment_method',
            sa.String(50),
            nullable=False,
            comment="bank, upi, wallet"
        ),
        sa.Column(
            'payment_ref',
            sa.String(255),
            nullable=True,
            comment="Bank ref, UPI ref, etc."
        ),
        sa.Column(
            'payment_status',
            sa.String(50),
            nullable=False,
            server_default="'pending'",
            comment="pending, processing, success, failed, refunded"
        ),
        sa.Column(
            'payment_initiated_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When payment was sent"
        ),
        sa.Column(
            'payment_confirmed_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When payment was confirmed in worker's account"
        ),
        sa.Column(
            'pow_token_id',
            sa.String(255),
            nullable=True,
            comment="Blockchain token ID (if applicable)"
        ),
        sa.Column(
            'smart_contract_tx_hash',
            sa.String(255),
            nullable=True,
            comment="Smart contract transaction hash"
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint('ledger_id'),
        sa.ForeignKeyConstraint(
            ['calculation_id'],
            ['payout_calculations.calculation_id'],
        ),
    )
    
    op.create_index(
        'ix_payout_ledger_claim_id',
        'payout_ledger',
        ['claim_id'],
    )
    op.create_index(
        'ix_payout_ledger_worker_id',
        'payout_ledger',
        ['worker_id'],
    )
    op.create_index(
        'ix_payout_ledger_payment_status',
        'payout_ledger',
        ['payment_status'],
    )
    op.create_index(
        'ix_payout_ledger_worker_created',
        'payout_ledger',
        ['worker_id', 'created_at'],
        comment="For daily/monthly total lookups"
    )


def downgrade():
    """Drop payout tables."""
    op.drop_index('ix_payout_ledger_worker_created', table_name='payout_ledger')
    op.drop_index('ix_payout_ledger_payment_status', table_name='payout_ledger')
    op.drop_index('ix_payout_ledger_worker_id', table_name='payout_ledger')
    op.drop_index('ix_payout_ledger_claim_id', table_name='payout_ledger')
    op.drop_table('payout_ledger')
    
    op.drop_index('ix_payout_calculations_created_at', table_name='payout_calculations')
    op.drop_index('ix_payout_calculations_worker_id', table_name='payout_calculations')
    op.drop_index('ix_payout_calculations_claim_id', table_name='payout_calculations')
    op.drop_table('payout_calculations')
