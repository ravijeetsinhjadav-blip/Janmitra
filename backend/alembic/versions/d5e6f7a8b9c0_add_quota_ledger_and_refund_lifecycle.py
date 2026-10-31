"""add user_monthly_quotas table and refund lifecycle columns

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-10-31 22:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd5e6f7a8b9c0'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create user_monthly_quotas table for atomic quota tracking
    op.create_table(
        'user_monthly_quotas',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='Primary UUID key for monthly quota record'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Associated citizen user ID'),
        sa.Column('year_month', sa.String(length=7), nullable=False, comment='Calendar month formatted as YYYY-MM'),
        sa.Column('guidance_sessions_used', sa.Integer(), server_default='0', nullable=False, comment='Count of consumed AI guidance sessions this calendar month'),
        sa.Column('doc_analyses_used', sa.Integer(), server_default='0', nullable=False, comment='Count of consumed AI document analyses this calendar month'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Quota ledger record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Quota ledger record last updated timestamp'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'year_month', name='uq_user_monthly_quota')
    )
    op.create_index(op.f('ix_user_monthly_quotas_id'), 'user_monthly_quotas', ['id'], unique=False)
    op.create_index(op.f('ix_user_monthly_quotas_user_id'), 'user_monthly_quotas', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_monthly_quotas_year_month'), 'user_monthly_quotas', ['year_month'], unique=False)

    # 2. Add refund and dispute lifecycle columns to payment_transactions
    op.add_column(
        'payment_transactions',
        sa.Column(
            'amount_refunded',
            sa.Numeric(precision=10, scale=2),
            server_default='0.00',
            nullable=False,
            comment='Cumulative refunded amount in INR'
        )
    )
    op.add_column(
        'payment_transactions',
        sa.Column(
            'dispute_status',
            sa.String(length=50),
            server_default='none',
            nullable=False,
            comment='Dispute status: none, created, under_review, won, lost, closed'
        )
    )
    op.add_column(
        'payment_transactions',
        sa.Column(
            'refunds_log',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default='{}',
            nullable=False,
            comment='Audit registry of processed refunds indexed by refund ID'
        )
    )
    op.create_index(op.f('ix_payment_transactions_dispute_status'), 'payment_transactions', ['dispute_status'], unique=False)


def downgrade() -> None:
    # Drop columns and table
    op.drop_index(op.f('ix_payment_transactions_dispute_status'), table_name='payment_transactions')
    op.drop_column('payment_transactions', 'refunds_log')
    op.drop_column('payment_transactions', 'dispute_status')
    op.drop_column('payment_transactions', 'amount_refunded')
    op.drop_index(op.f('ix_user_monthly_quotas_year_month'), table_name='user_monthly_quotas')
    op.drop_index(op.f('ix_user_monthly_quotas_user_id'), table_name='user_monthly_quotas')
    op.drop_index(op.f('ix_user_monthly_quotas_id'), table_name='user_monthly_quotas')
    op.drop_table('user_monthly_quotas')
