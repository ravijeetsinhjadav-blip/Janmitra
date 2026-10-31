"""add processing ownership tokens to document metadata

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-10-31 23:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e6f7a8b9c0d1'
down_revision = 'd5e6f7a8b9c0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add processing_token and lease_expires_at to document_metadata
    op.add_column(
        'document_metadata',
        sa.Column(
            'processing_token',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='Ownership lease token identifying active processing attempt',
        ),
    )
    op.add_column(
        'document_metadata',
        sa.Column(
            'lease_expires_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Lease expiration timestamp for in-flight OCR execution',
        ),
    )
    op.create_index(
        op.f('ix_document_metadata_processing_token'),
        'document_metadata',
        ['processing_token'],
        unique=False,
    )
    op.create_index(
        op.f('ix_document_metadata_lease_expires_at'),
        'document_metadata',
        ['lease_expires_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_document_metadata_lease_expires_at'), table_name='document_metadata')
    op.drop_index(op.f('ix_document_metadata_processing_token'), table_name='document_metadata')
    op.drop_column('document_metadata', 'lease_expires_at')
    op.drop_column('document_metadata', 'processing_token')

