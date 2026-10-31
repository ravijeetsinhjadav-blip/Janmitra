"""initial_schema_phase_2

Revision ID: e36378f07849
Revises: 
Create Date: 2026-10-31 12:18:35.219458

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e36378f07849'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, comment='Primary UUID key for the user'),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='citizen', comment='Account role: citizen or admin'),
        sa.Column('email', sa.String(length=255), nullable=True, comment='Citizen email address (optional, unique when provided)'),
        sa.Column('mobile_number', sa.String(length=20), nullable=True, comment='Citizen mobile number (optional, unique when provided)'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true'), comment='Flag indicating active account status'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_mobile_number'), 'users', ['mobile_number'], unique=True)

    # 2. user_profiles table
    op.create_table(
        'user_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, comment='Primary UUID key for citizen profile'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, comment='Associated User account ID'),
        sa.Column('full_name', sa.String(length=150), nullable=False, comment="Citizen's legal full name"),
        sa.Column('date_of_birth', sa.Date(), nullable=False, comment='Date of birth for age-based criteria'),
        sa.Column('state', sa.String(length=100), nullable=False, comment='State / UT of residence'),
        sa.Column('district', sa.String(length=100), nullable=False, comment='District of residence'),
        sa.Column('residence_type', sa.String(length=20), nullable=False, server_default='rural', comment='Residence type: rural or urban'),
        sa.Column('annual_family_income', sa.Numeric(precision=12, scale=2), nullable=True, comment='Annual family income in INR'),
        sa.Column('occupation', sa.String(length=100), nullable=True, comment='Citizen occupation'),
        sa.Column('education_level', sa.String(length=100), nullable=True, comment='Highest education completed'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_user_profiles_id'), 'user_profiles', ['id'], unique=False)
    op.create_index(op.f('ix_user_profiles_user_id'), 'user_profiles', ['user_id'], unique=True)
    op.create_index(op.f('ix_user_profiles_state'), 'user_profiles', ['state'], unique=False)
    op.create_index(op.f('ix_user_profiles_district'), 'user_profiles', ['district'], unique=False)

    # 3. schemes table
    op.create_table(
        'schemes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, comment='Primary UUID key for government scheme'),
        sa.Column('scheme_name', sa.String(length=255), nullable=False, comment='Official title of the government scheme'),
        sa.Column('description', sa.Text(), nullable=False, comment='Detailed overview of objectives and benefits'),
        sa.Column('department', sa.String(length=200), nullable=False, comment='Nodal ministry or state department'),
        sa.Column('state_applicability', sa.String(length=100), nullable=False, server_default='All India', comment='Geographic scope'),
        sa.Column('eligibility_summary', sa.Text(), nullable=False, comment='Summary of eligibility criteria'),
        sa.Column('official_source_url', sa.String(length=500), nullable=False, comment='Official government portal guidelines URL'),
        sa.Column('official_application_url', sa.String(length=500), nullable=False, comment='Official government online portal URL'),
        sa.Column('source_last_verified_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when verified'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true'), comment='Flag indicating active status'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_schemes_id'), 'schemes', ['id'], unique=False)
    op.create_index(op.f('ix_schemes_scheme_name'), 'schemes', ['scheme_name'], unique=False)
    op.create_index(op.f('ix_schemes_department'), 'schemes', ['department'], unique=False)
    op.create_index(op.f('ix_schemes_state_applicability'), 'schemes', ['state_applicability'], unique=False)
    op.create_index(op.f('ix_schemes_is_active'), 'schemes', ['is_active'], unique=False)

    # 4. document_metadata table
    op.create_table(
        'document_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, comment='Primary UUID key for document record'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='Owner citizen user ID'),
        sa.Column('document_type', sa.String(length=100), nullable=False, comment='Document classification'),
        sa.Column('original_filename', sa.String(length=255), nullable=False, comment='Original uploaded filename'),
        sa.Column('storage_reference', sa.String(length=500), nullable=False, comment='Storage path / identifier on secure filesystem'),
        sa.Column('mime_type', sa.String(length=100), nullable=False, comment='MIME type'),
        sa.Column('file_size', sa.BigInteger(), nullable=False, comment='Document file size in bytes'),
        sa.Column('upload_status', sa.String(length=50), nullable=False, server_default='uploaded', comment='Status: uploaded, verified, rejected'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_document_metadata_id'), 'document_metadata', ['id'], unique=False)
    op.create_index(op.f('ix_document_metadata_user_id'), 'document_metadata', ['user_id'], unique=False)
    op.create_index(op.f('ix_document_metadata_document_type'), 'document_metadata', ['document_type'], unique=False)
    op.create_index(op.f('ix_document_metadata_upload_status'), 'document_metadata', ['upload_status'], unique=False)

    # 5. assessments table
    op.create_table(
        'assessments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, comment='Primary UUID key for assessment run'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='Citizen user ID'),
        sa.Column('scheme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('schemes.id', ondelete='SET NULL'), nullable=True, comment='Target scheme ID'),
        sa.Column('assessment_type', sa.String(length=50), nullable=False, server_default='scheme_eligibility', comment='Assessment category'),
        sa.Column('result_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Advisory outcome JSONB'),
        sa.Column('overall_readiness_score', sa.Float(), nullable=True, comment='Readiness score from 0.0 to 100.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_assessments_id'), 'assessments', ['id'], unique=False)
    op.create_index(op.f('ix_assessments_user_id'), 'assessments', ['user_id'], unique=False)
    op.create_index(op.f('ix_assessments_scheme_id'), 'assessments', ['scheme_id'], unique=False)
    op.create_index(op.f('ix_assessments_assessment_type'), 'assessments', ['assessment_type'], unique=False)

    # 6. applications table
    op.create_table(
        'applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, comment='Primary UUID key for application record'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='Citizen user ID'),
        sa.Column('scheme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('schemes.id', ondelete='CASCADE'), nullable=False, comment='Target scheme ID'),
        sa.Column('application_reference_number', sa.String(length=100), nullable=True, comment='Government portal application reference'),
        sa.Column('submission_date', sa.DateTime(timezone=True), nullable=True, comment='Submission date on official portal'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='Submitted', comment='Manual status tracking'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_applications_id'), 'applications', ['id'], unique=False)
    op.create_index(op.f('ix_applications_user_id'), 'applications', ['user_id'], unique=False)
    op.create_index(op.f('ix_applications_scheme_id'), 'applications', ['scheme_id'], unique=False)
    op.create_index(op.f('ix_applications_application_reference_number'), 'applications', ['application_reference_number'], unique=False)
    op.create_index(op.f('ix_applications_status'), 'applications', ['status'], unique=False)

    # 7. subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, comment='Primary UUID key for subscription'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='Subscriber user ID'),
        sa.Column('plan_type', sa.String(length=20), nullable=False, server_default='free', comment='free or premium'),
        sa.Column('billing_cycle', sa.String(length=20), nullable=True, comment='monthly, six_months, or yearly'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active', comment='active, expired, cancelled'),
        sa.Column('start_date', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_subscriptions_id'), 'subscriptions', ['id'], unique=False)
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_plan_type'), 'subscriptions', ['plan_type'], unique=False)
    op.create_index(op.f('ix_subscriptions_status'), 'subscriptions', ['status'], unique=False)

    # 8. notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, comment='Primary UUID key for notification'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='Recipient user ID'),
        sa.Column('title', sa.String(length=200), nullable=False, comment='Notification subject'),
        sa.Column('message', sa.Text(), nullable=False, comment='Notification content'),
        sa.Column('notification_type', sa.String(length=50), nullable=False, server_default='system', comment='Notification category'),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='Read receipt flag'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_notifications_notification_type'), 'notifications', ['notification_type'], unique=False)
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('subscriptions')
    op.drop_table('applications')
    op.drop_table('assessments')
    op.drop_table('document_metadata')
    op.drop_table('schemes')
    op.drop_table('user_profiles')
    op.drop_table('users')
