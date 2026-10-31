"""add_auth_and_user_management_tables

Revision ID: 4dcd7dfc601d
Revises: e36378f07849
Create Date: 2026-10-31 12:46:54.011688

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4dcd7dfc601d'
down_revision: Union[str, None] = 'e36378f07849'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. otp_challenges table
    op.create_table(
        'otp_challenges',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, comment='Primary UUID key for OTP challenge'),
        sa.Column('mobile_number', sa.String(length=20), nullable=False, comment='Normalized mobile number'),
        sa.Column('hashed_otp', sa.String(length=255), nullable=False, comment='SHA-256 hash of the generated OTP'),
        sa.Column('purpose', sa.String(length=50), nullable=False, server_default='auth', comment='Challenge intent'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, comment='Expiration timestamp'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0', comment='Verification attempts count'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3', comment='Max allowed attempts'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='Verification status'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_otp_challenges_id'), 'otp_challenges', ['id'], unique=False)
    op.create_index(op.f('ix_otp_challenges_mobile_number'), 'otp_challenges', ['mobile_number'], unique=False)

    # 2. user_sessions table (Hashed Refresh Tokens)
    op.create_table(
        'user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, comment='Primary UUID key for session record'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='Owner user ID'),
        sa.Column('token_hash', sa.String(length=255), nullable=False, unique=True, comment='SHA-256 hash of refresh token'),
        sa.Column('device_info', sa.String(length=255), nullable=True, comment='Client device information'),
        sa.Column('ip_address', sa.String(length=50), nullable=True, comment='Client IP address'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, comment='Session expiry timestamp'),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='Revocation status'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_user_sessions_id'), 'user_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_sessions_token_hash'), 'user_sessions', ['token_hash'], unique=True)
    op.create_index(op.f('ix_user_sessions_is_revoked'), 'user_sessions', ['is_revoked'], unique=False)

    # 3. account_deletion_requests table
    op.create_table(
        'account_deletion_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, comment='Primary UUID key for deletion request'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='Citizen user ID'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending', comment='pending, cancelled, completed'),
        sa.Column('reason', sa.Text(), nullable=True, comment='Citizen deletion rationale'),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=False, comment='Scheduled deletion timestamp'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_account_deletion_requests_id'), 'account_deletion_requests', ['id'], unique=False)
    op.create_index(op.f('ix_account_deletion_requests_user_id'), 'account_deletion_requests', ['user_id'], unique=False)
    op.create_index(op.f('ix_account_deletion_requests_status'), 'account_deletion_requests', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('account_deletion_requests')
    op.drop_table('user_sessions')
    op.drop_table('otp_challenges')
