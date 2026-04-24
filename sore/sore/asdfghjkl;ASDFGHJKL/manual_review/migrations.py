"""
Database migrations for Manual Review System

Alembic migration script to create PostgreSQL tables:
- review_queue: stores pending/assigned review items
- reviewers: reviewer profiles and stats
- appeals: worker appeals for rejected claims
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    """Create manual review tables."""
    
    # Create review_queue table
    op.create_table(
        'review_queue',
        sa.Column('queue_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('priority', sa.Integer(), nullable=False, comment='1=CRITICAL, 2=HIGH, 3=NORMAL'),
        sa.Column('status', sa.String(50), nullable=False, default='pending', 
                  comment='pending|assigned|in_review|decided|escalated'),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('sla_deadline', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('enqueued_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decision', sa.String(50), nullable=True, comment='approve|reject|request_more_info'),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('payout_override_inr', sa.Float(), nullable=True),
        sa.Column('reviewer_notes', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Integer(), nullable=True, comment='1-5 confidence level'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Indexes for common queries
    op.create_index('idx_review_queue_status_priority', 'review_queue', ['status', 'priority'])
    op.create_index('idx_review_queue_reviewer_id_status', 'review_queue', ['reviewer_id', 'status'])
    op.create_index('idx_review_queue_sla_deadline', 'review_queue', ['sla_deadline'])
    
    # Create reviewers table
    op.create_table(
        'reviewers',
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('role', sa.String(20), nullable=False, comment='junior|senior|lead'),
        sa.Column('current_load', sa.Integer(), nullable=False, default=0),
        sa.Column('max_load', sa.Integer(), nullable=False, 
                  comment='5 for junior, 10 for senior, 15 for lead'),
        sa.Column('specialisation', postgresql.JSONB(), nullable=True, 
                  comment='{"cities": ["delhi", "bangalore"], "claim_types": ["ride", "delivery"]}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('total_decided', sa.Integer(), nullable=False, default=0),
        sa.Column('approval_rate', sa.Float(), nullable=False, default=0.5, 
                  comment='proportion of approved decisions'),
        sa.Column('avg_decision_time_min', sa.Float(), nullable=False, default=0.0,
                  comment='exponential moving average'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Indexes
    op.create_index('idx_reviewers_role_is_active', 'reviewers', ['role', 'is_active'])
    op.create_index('idx_reviewers_email', 'reviewers', ['email'])
    
    # Create appeals table
    op.create_table(
        'appeals',
        sa.Column('appeal_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True, index=True, comment='one appeal per claim'),
        sa.Column('worker_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('status', sa.String(50), nullable=False, default='pending', 
                  comment='pending|under_review|approved|rejected'),
        sa.Column('appeal_reason', sa.Text(), nullable=False),
        sa.Column('evidence_urls', postgresql.JSONB(), nullable=True, 
                  comment='["https://...", "https://..."]'),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=True, 
                  comment='lead reviewer on appeal'),
        sa.Column('appeal_decision', sa.String(50), nullable=True, 
                  comment='approved|rejected on appeal'),
        sa.Column('appeal_decision_notes', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Indexes
    op.create_index('idx_appeals_claim_id', 'appeals', ['claim_id'])
    op.create_index('idx_appeals_worker_id', 'appeals', ['worker_id'])
    op.create_index('idx_appeals_status', 'appeals', ['status'])
    op.create_index('idx_appeals_submitted_resolved', 'appeals', ['submitted_at', 'resolved_at'])


def downgrade():
    """Drop manual review tables."""
    op.drop_table('appeals')
    op.drop_table('reviewers')
    op.drop_table('review_queue')
