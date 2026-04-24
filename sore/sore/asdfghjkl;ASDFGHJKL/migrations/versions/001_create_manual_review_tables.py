"""
Database Migration: Create manual review tables

Creates tables for review_queue and appeals with proper schema.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    """Create review_queue and appeals tables."""
    
    # Create review_queue table
    op.create_table(
        'review_queue',
        sa.Column('queue_id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('claim_id', sa.String(36), nullable=False, unique=True),
        sa.Column('worker_id', sa.String(36), nullable=False),
        sa.Column('priority', sa.Integer, nullable=False, server_default='3'),
        sa.Column('risk_score', sa.Float, nullable=False),
        sa.Column('assigned_reviewer_id', sa.String(36), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sla_deadline', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('payout_eligible_inr', sa.Float, nullable=False),
        sa.Column('trust_tier', sa.String(20), nullable=False),
        
        sa.Index('idx_review_queue_status', 'status'),
        sa.Index('idx_review_queue_priority', 'priority'),
        sa.Index('idx_review_queue_reviewer', 'assigned_reviewer_id'),
        sa.Index('idx_review_queue_sla', 'sla_deadline'),
    )
    
    # Create reviewers table
    op.create_table(
        'reviewers',
        sa.Column('reviewer_id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('active', sa.Boolean, default=True, nullable=False),
        sa.Column('current_load', sa.Integer, default=0, nullable=False),
        sa.Column('max_load', sa.Integer, nullable=False),
        sa.Column('specialisation', postgresql.ARRAY(sa.String), default=[], nullable=False),
        sa.Column('total_decided', sa.Integer, default=0, nullable=False),
        sa.Column('approval_rate', sa.Float, default=0.5, nullable=False),
        sa.Column('avg_decision_time_min', sa.Float, default=0.0, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        sa.Index('idx_reviewers_role', 'role'),
        sa.Index('idx_reviewers_active', 'active'),
    )
    
    # Create appeals table
    op.create_table(
        'appeals',
        sa.Column('appeal_id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('claim_id', sa.String(36), nullable=False, unique=True),
        sa.Column('worker_id', sa.String(36), nullable=False),
        sa.Column('appeal_reason', sa.Text, nullable=False),
        sa.Column('evidence_urls', postgresql.ARRAY(sa.String), default=[], nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewer_id', sa.String(36), nullable=True),
        sa.Column('decision_notes', sa.Text, nullable=True),
        sa.Column('queue_item_id', sa.String(36), nullable=True),
        
        sa.Index('idx_appeals_worker', 'worker_id'),
        sa.Index('idx_appeals_status', 'status'),
        sa.Index('idx_appeals_resolved_at', 'resolved_at'),
    )
    
    # Create manual_review_decisions table (for audit trail)
    op.create_table(
        'manual_review_decisions',
        sa.Column('decision_id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('queue_id', sa.String(36), nullable=False),
        sa.Column('claim_id', sa.String(36), nullable=False),
        sa.Column('reviewer_id', sa.String(36), nullable=False),
        sa.Column('decision', sa.String(20), nullable=False),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('payout_override_inr', sa.Float, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('confidence', sa.Integer, nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        sa.Index('idx_decisions_reviewer', 'reviewer_id'),
        sa.Index('idx_decisions_claim', 'claim_id'),
        sa.Index('idx_decisions_decided_at', 'decided_at'),
    )


def downgrade():
    """Drop all manual review tables."""
    op.drop_table('manual_review_decisions')
    op.drop_table('appeals')
    op.drop_table('reviewers')
    op.drop_table('review_queue')
