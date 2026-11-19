"""add device tokens and fcm push notification support

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-11-01 20:50:00.000000

"""
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a3b4c5d6e7f8'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create device_tokens table
    op.create_table(
        'device_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment='Primary UUID key for device token record'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True, comment='Citizen user ID owner'),
        sa.Column('device_token', sa.String(length=255), nullable=False, index=True, comment='FCM registration token issued by client SDK'),
        sa.Column('device_type', sa.String(length=20), server_default='android', nullable=False, comment='Device OS platform: android, ios, or web'),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False, index=True, comment='Active delivery status'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Registration timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Last token refresh / active timestamp'),
        sa.UniqueConstraint('user_id', 'device_token', name='uq_device_tokens_user_token'),
    )


def downgrade() -> None:
    op.drop_table('device_tokens')

