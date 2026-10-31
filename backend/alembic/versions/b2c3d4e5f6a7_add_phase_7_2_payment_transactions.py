"""add phase 7.2 payment transactions table

Revision ID: b2c3d4e5f6a7
Revises: f1a2b3c4d5e6
Create Date: 2026-10-31 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create payment_transactions table for Razorpay payment and webhook auditing
    op.create_table(
        'payment_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='Primary UUID key for payment transaction'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Associated citizen User ID'),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Associated Subscription record if activated'),
        sa.Column('razorpay_order_id', sa.String(length=100), nullable=False, comment='Unique Razorpay order ID'),
        sa.Column('razorpay_payment_id', sa.String(length=100), nullable=True, comment='Unique Razorpay payment ID'),
        sa.Column('razorpay_signature', sa.String(length=255), nullable=True, comment='Cryptographic HMAC-SHA256 signature'),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False, comment='Payment amount in INR'),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False, comment='Payment currency'),
        sa.Column('plan_type', sa.String(length=20), server_default='premium', nullable=False, comment='Subscription plan: premium'),
        sa.Column('billing_cycle', sa.String(length=20), nullable=False, comment='Billing cycle: monthly or yearly'),
        sa.Column('payment_status', sa.String(length=30), server_default='created', nullable=False, comment='created, captured, failed, refunded'),
        sa.Column('payment_method', sa.String(length=50), nullable=True, comment='Payment instrument: upi, card, qr, netbanking'),
        sa.Column('error_code', sa.String(length=100), nullable=True, comment='Error code if payment failed'),
        sa.Column('error_description', sa.Text(), nullable=True, comment='Detailed failure reason'),
        sa.Column('idempotency_key', sa.String(length=100), nullable=True, comment='Idempotency key to prevent duplicate processing'),
        sa.Column('payment_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False, comment='Raw verified webhook payloads'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Transaction creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Transaction last modified timestamp'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_transactions_id'), 'payment_transactions', ['id'], unique=False)
    op.create_index(op.f('ix_payment_transactions_user_id'), 'payment_transactions', ['user_id'], unique=False)
    op.create_index(op.f('ix_payment_transactions_razorpay_order_id'), 'payment_transactions', ['razorpay_order_id'], unique=True)
    op.create_index(op.f('ix_payment_transactions_razorpay_payment_id'), 'payment_transactions', ['razorpay_payment_id'], unique=True)
    op.create_index(op.f('ix_payment_transactions_payment_status'), 'payment_transactions', ['payment_status'], unique=False)
    op.create_index(op.f('ix_payment_transactions_idempotency_key'), 'payment_transactions', ['idempotency_key'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_payment_transactions_idempotency_key'), table_name='payment_transactions')
    op.drop_index(op.f('ix_payment_transactions_payment_status'), table_name='payment_transactions')
    op.drop_index(op.f('ix_payment_transactions_razorpay_payment_id'), table_name='payment_transactions')
    op.drop_index(op.f('ix_payment_transactions_razorpay_order_id'), table_name='payment_transactions')
    op.drop_index(op.f('ix_payment_transactions_user_id'), table_name='payment_transactions')
    op.drop_index(op.f('ix_payment_transactions_id'), table_name='payment_transactions')
    op.drop_table('payment_transactions')
