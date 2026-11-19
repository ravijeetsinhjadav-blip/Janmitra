"""add scheme intelligence category rules document guides and beneficiary analytics

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-11-05 21:55:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from alembic import op

# revision identifiers, used by Alembic.
revision = 'e7f8a9b0c1d2'
down_revision = 'd6e7f8a9b0c1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Scheme Category Rules
    op.create_table(
        'scheme_category_rules',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('scheme_id', UUID(as_uuid=True), sa.ForeignKey('schemes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('condition_name', sa.String(length=255), nullable=False),
        sa.Column('field', sa.String(length=100), nullable=False),
        sa.Column('operator', sa.String(length=20), nullable=False, server_default='lte'),
        sa.Column('expected_value', JSONB, nullable=False),
        sa.Column('special_conditions', sa.Text(), nullable=True),
        sa.Column('exceptions', sa.Text(), nullable=True),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('official_source_reference', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_scheme_category_rules_id', 'scheme_category_rules', ['id'])
    op.create_index('ix_scheme_category_rules_scheme_id', 'scheme_category_rules', ['scheme_id'])
    op.create_index('ix_scheme_category_rules_category', 'scheme_category_rules', ['category'])

    # 2. Scheme Category Documents
    op.create_table(
        'scheme_category_documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('scheme_id', UUID(as_uuid=True), sa.ForeignKey('schemes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('document_name', sa.String(length=255), nullable=False),
        sa.Column('document_type', sa.String(length=100), nullable=False),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('conditions_description', sa.Text(), nullable=True),
        sa.Column('issuing_authority', sa.String(length=255), nullable=False, server_default='Competent Revenue Authority'),
        sa.Column('accepted_formats', sa.String(length=100), nullable=False, server_default='PDF, JPG, PNG'),
        sa.Column('validity_rules', sa.String(length=255), nullable=True),
        sa.Column('official_source', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_scheme_category_documents_id', 'scheme_category_documents', ['id'])
    op.create_index('ix_scheme_category_documents_scheme_id', 'scheme_category_documents', ['scheme_id'])
    op.create_index('ix_scheme_category_documents_category', 'scheme_category_documents', ['category'])
    op.create_index('ix_scheme_category_documents_document_type', 'scheme_category_documents', ['document_type'])

    # 3. Document Guides
    op.create_table(
        'document_guides',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('document_type', sa.String(length=100), nullable=False, unique=True),
        sa.Column('document_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('issuing_department', sa.String(length=255), nullable=False),
        sa.Column('state_specific_authority', JSONB, nullable=False, server_default='{}'),
        sa.Column('required_supporting_documents', JSONB, nullable=False, server_default='[]'),
        sa.Column('online_steps', JSONB, nullable=False, server_default='{}'),
        sa.Column('offline_steps', JSONB, nullable=False, server_default='{}'),
        sa.Column('fees_and_timelines', JSONB, nullable=False, server_default='{}'),
        sa.Column('official_links', JSONB, nullable=False, server_default='{}'),
        sa.Column('languages_supported', JSONB, nullable=False, server_default='["en", "hi", "gu"]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_document_guides_id', 'document_guides', ['id'])
    op.create_index('ix_document_guides_document_type', 'document_guides', ['document_type'], unique=True)

    # 4. Scheme Analytics Datasets
    op.create_table(
        'scheme_analytics_datasets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('scheme_id', UUID(as_uuid=True), sa.ForeignKey('schemes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_name', sa.String(length=255), nullable=False),
        sa.Column('source_url', sa.String(length=500), nullable=False),
        sa.Column('source_publication_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reporting_period', sa.String(length=100), nullable=False),
        sa.Column('metric_type', sa.String(length=100), nullable=False, server_default='unique_beneficiaries'),
        sa.Column('total_beneficiaries', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('dataset_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('verification_status', sa.String(length=50), nullable=False, server_default='Pending Verification'),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_scheme_analytics_datasets_id', 'scheme_analytics_datasets', ['id'])
    op.create_index('ix_scheme_analytics_datasets_scheme_id', 'scheme_analytics_datasets', ['scheme_id'])
    op.create_index('ix_scheme_analytics_datasets_verification_status', 'scheme_analytics_datasets', ['verification_status'])
    op.create_index('ix_scheme_analytics_datasets_is_published', 'scheme_analytics_datasets', ['is_published'])

    # 5. Scheme Analytics Breakdowns
    op.create_table(
        'scheme_analytics_breakdowns',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('dataset_id', UUID(as_uuid=True), sa.ForeignKey('scheme_analytics_datasets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dimension', sa.String(length=50), nullable=False),
        sa.Column('category_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('percentage', sa.Float(), nullable=True),
        sa.Column('notes', sa.String(length=255), nullable=True),
    )
    op.create_index('ix_scheme_analytics_breakdowns_id', 'scheme_analytics_breakdowns', ['id'])
    op.create_index('ix_scheme_analytics_breakdowns_dataset_id', 'scheme_analytics_breakdowns', ['dataset_id'])
    op.create_index('ix_scheme_analytics_breakdowns_dimension', 'scheme_analytics_breakdowns', ['dimension'])

    # 6. Scheme Analytics Audit Logs
    op.create_table(
        'scheme_analytics_audit_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('dataset_id', UUID(as_uuid=True), nullable=True),
        sa.Column('scheme_id', UUID(as_uuid=True), nullable=True),
        sa.Column('admin_id', UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('details', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_scheme_analytics_audit_logs_id', 'scheme_analytics_audit_logs', ['id'])
    op.create_index('ix_scheme_analytics_audit_logs_dataset_id', 'scheme_analytics_audit_logs', ['dataset_id'])
    op.create_index('ix_scheme_analytics_audit_logs_scheme_id', 'scheme_analytics_audit_logs', ['scheme_id'])


def downgrade() -> None:
    op.drop_table('scheme_analytics_audit_logs')
    op.drop_table('scheme_analytics_breakdowns')
    op.drop_table('scheme_analytics_datasets')
    op.drop_table('document_guides')
    op.drop_table('scheme_category_documents')
    op.drop_table('scheme_category_rules')

