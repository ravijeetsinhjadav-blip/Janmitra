"""add reminder dispatch lease and tracking columns

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-11-02 23:30:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'd6e7f8a9b0c1'
down_revision = 'c5d6e7f8a9b0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('application_reminders') as batch_op:
        batch_op.add_column(
            sa.Column('last_dispatched_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when notification was successfully dispatched')
        )
        batch_op.add_column(
            sa.Column('dispatch_lease_until', sa.DateTime(timezone=True), nullable=True, comment='Lease expiration timestamp for active worker claim')
        )
        batch_op.add_column(
            sa.Column('dispatch_token', sa.String(length=64), nullable=True, comment='Unique worker token claiming this reminder for dispatch')
        )
        batch_op.add_column(
            sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False, comment='Number of dispatch retry attempts on transient failure')
        )
        batch_op.create_index(batch_op.f('ix_application_reminders_dispatch_lease_until'), ['dispatch_lease_until'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('application_reminders') as batch_op:
        batch_op.drop_index(batch_op.f('ix_application_reminders_dispatch_lease_until'))
        batch_op.drop_column('retry_count')
        batch_op.drop_column('dispatch_token')
        batch_op.drop_column('dispatch_lease_until')
        batch_op.drop_column('last_dispatched_at')

