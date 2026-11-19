"""add password reset tokens table

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-11-02 17:00:00.000000

"""
import uuid
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c5d6e7f8a9b0'
down_revision = 'b4c5d6e7f8a9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment='Primary UUID key for password reset token'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True, comment='User requesting password reset'),
        sa.Column('token_hash', sa.String(length=255), nullable=False, unique=True, index=True, comment='Cryptographic SHA-256 hash of reset token'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, index=True, comment='Timestamp when token expires'),
        sa.Column('is_used', sa.Boolean(), server_default='false', nullable=False, index=True, comment='Flag indicating whether token has been consumed'),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when token was consumed'),
        sa.Column('ip_address', sa.String(length=50), nullable=True, comment='Client IP address at request'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Creation timestamp'),
    )


def downgrade() -> None:
    op.drop_table('password_reset_tokens')

