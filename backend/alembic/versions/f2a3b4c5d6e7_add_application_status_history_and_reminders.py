"""add application status history and reminders

Revision ID: f2a3b4c5d6e7
Revises: e6f7a8b9c0d1
Create Date: 2026-11-01 17:30:00.000000

"""
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f2a3b4c5d6e7'
down_revision = 'e6f7a8b9c0d1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # 1. Add composite unique constraint or index on applications(id, user_id)
    if bind.dialect.name == "sqlite":
        op.create_index('uq_applications_id_user_id', 'applications', ['id', 'user_id'], unique=True)
    else:
        op.create_unique_constraint(
            'uq_applications_id_user_id',
            'applications',
            ['id', 'user_id'],
        )

    # 2. Create application_status_history table (no redundant primary key index)
    op.create_table(
        'application_status_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, comment='Primary UUID key for status history record'),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False, comment='Parent application tracking record ID'),
        sa.Column('previous_status', sa.String(length=50), nullable=True, comment='Status prior to this transition'),
        sa.Column('new_status', sa.String(length=50), nullable=False, comment='Updated status'),
        sa.Column('event_type', sa.String(length=50), server_default='STATUS_UPDATE', nullable=False, comment='Event type: INITIAL_REGISTRATION, STATUS_UPDATE, REMARK_ADDED, APPLICATION_DETAILS_UPDATED'),
        sa.Column('source', sa.String(length=50), server_default='USER_REPORTED', nullable=False, comment='Source: USER_REPORTED or SYSTEM_MIGRATION'),
        sa.Column('remarks', sa.Text(), nullable=True, comment='Citizen notes or remarks (null if omitted)'),
        sa.Column('changed_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment='User ID who submitted this update'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Timestamp when this status transition or remark occurred'),
    )
    op.create_index(op.f('ix_application_status_history_application_id'), 'application_status_history', ['application_id'], unique=False)
    op.create_index(op.f('ix_application_status_history_changed_by_user_id'), 'application_status_history', ['changed_by_user_id'], unique=False)
    op.create_index(op.f('ix_application_status_history_created_at'), 'application_status_history', ['created_at'], unique=False)

    # 3. Create application_reminders table with composite foreign key (no redundant primary key index)
    op.create_table(
        'application_reminders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, comment='Primary UUID key for reminder record'),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Associated application tracking record ID'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Citizen owner ID (strictly locked to application.user_id)'),
        sa.Column('title', sa.String(length=200), nullable=False, comment='Short summary / title of the reminder task'),
        sa.Column('description', sa.Text(), nullable=True, comment='Detailed instructions or required items'),
        sa.Column('reminder_date', sa.DateTime(timezone=True), nullable=False, comment='Scheduled date and time for reminder (UTC)'),
        sa.Column('is_completed', sa.Boolean(), server_default=sa.text('false'), nullable=False, comment='Completion flag'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when reminder was completed'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Record last updated timestamp'),
        sa.ForeignKeyConstraint(
            ['application_id', 'user_id'],
            ['applications.id', 'applications.user_id'],
            ondelete='CASCADE',
            name='fk_application_reminders_application_user',
        ),
    )
    op.create_index(op.f('ix_application_reminders_application_id'), 'application_reminders', ['application_id'], unique=False)
    op.create_index(op.f('ix_application_reminders_user_id'), 'application_reminders', ['user_id'], unique=False)
    op.create_index(op.f('ix_application_reminders_reminder_date'), 'application_reminders', ['reminder_date'], unique=False)
    op.create_index(op.f('ix_application_reminders_is_completed'), 'application_reminders', ['is_completed'], unique=False)

    # 4. Safe Python-driven backfill: preserves existing status, SYSTEM_MIGRATION source, no fabricated user attribution, NULL remarks
    bind = op.get_bind()
    res = bind.execute(sa.text("""
        SELECT id, status, created_at FROM applications a
        WHERE NOT EXISTS (
            SELECT 1 FROM application_status_history h WHERE h.application_id = a.id
        )
    """))

    if res is not None:
        apps = res.fetchall()
        for row in apps:
            bind.execute(
                sa.text("""
                    INSERT INTO application_status_history (
                        id, application_id, previous_status, new_status, event_type, source, remarks, changed_by_user_id, created_at
                    ) VALUES (
                        :id, :app_id, NULL, :status, 'INITIAL_REGISTRATION', 'SYSTEM_MIGRATION', NULL, NULL, :created_at
                    )
                """),
                {
                    "id": str(uuid.uuid4()) if bind.dialect.name == "sqlite" else uuid.uuid4(),
                    "app_id": row[0],
                    "status": row[1],
                    "created_at": row[2],
                }
            )


def downgrade() -> None:
    # Drop dependent objects in exact reverse dependency order
    op.drop_table('application_reminders')
    op.drop_table('application_status_history')
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.drop_index('uq_applications_id_user_id', table_name='applications')
    else:
        op.drop_constraint('uq_applications_id_user_id', 'applications', type_='unique')

