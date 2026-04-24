"""Create pow_tokens table

Revision ID: 003_create_pow_tokens
Revises: 002_create_payout_tables
Create Date: 2025-04-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_create_pow_tokens'
down_revision = '002_create_payout_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create pow_tokens table for blockchain token tracking."""
    op.create_table(
        'pow_tokens',
        # Primary key
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Foreign keys
        sa.Column(
            'claim_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        
        # On-chain data
        sa.Column('token_id', sa.BigInteger(), nullable=False),
        sa.Column('worker_id', sa.String(255), nullable=False),
        sa.Column('tx_hash', sa.String(255), nullable=False),
        sa.Column('block_number', sa.Integer(), nullable=False),
        sa.Column('network', sa.String(50), nullable=False),
        sa.Column('ipfs_uri', sa.String(512), nullable=False),
        sa.Column('feature_vector_hash', sa.String(255), nullable=False),
        
        # Status
        sa.Column('payout_released', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('gas_used', sa.Integer(), nullable=False, server_default='0'),
        
        # Timestamps
        sa.Column(
            'minted_at',
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('claim_id', name='uq_pow_tokens_claim_id'),
        sa.UniqueConstraint('token_id', name='uq_pow_tokens_token_id'),
        sa.UniqueConstraint('tx_hash', name='uq_pow_tokens_tx_hash'),
        sa.ForeignKeyConstraint(
            ['claim_id'],
            ['claims.claim_id'],
            name='fk_pow_tokens_claim_id',
            ondelete='RESTRICT',
        ),
    )
    
    # Create indexes for efficient queries
    op.create_index(
        'ix_pow_tokens_claim_id',
        'pow_tokens',
        ['claim_id'],
        unique=True,
    )
    op.create_index(
        'ix_pow_tokens_token_id',
        'pow_tokens',
        ['token_id'],
        unique=True,
    )
    op.create_index(
        'ix_pow_tokens_worker_id',
        'pow_tokens',
        ['worker_id'],
    )
    op.create_index(
        'ix_pow_tokens_tx_hash',
        'pow_tokens',
        ['tx_hash'],
        unique=True,
    )
    op.create_index(
        'ix_pow_tokens_payout_released',
        'pow_tokens',
        ['payout_released'],
    )
    op.create_index(
        'ix_pow_tokens_network',
        'pow_tokens',
        ['network'],
    )
    op.create_index(
        'ix_pow_tokens_minted_at',
        'pow_tokens',
        ['minted_at'],
    )


def downgrade() -> None:
    """Drop pow_tokens table."""
    op.drop_table('pow_tokens')
