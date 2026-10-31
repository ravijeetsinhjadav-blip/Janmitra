"""extend document metadata for phase 5

Revision ID: e9f8a7b6c5d4
Revises: 7a8e5f3c9102
Create Date: 2026-10-31 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e9f8a7b6c5d4'
down_revision = '7a8e5f3c9102'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add Phase 5 OCR processing fields to document_metadata table
    op.add_column(
        'document_metadata',
        sa.Column('ocr_status', sa.String(length=50), server_default='UPLOADED', nullable=False, comment='Status: UPLOADED, PENDING_OCR, PROCESSING, OCR_COMPLETED, MANUAL_REVIEW_REQUIRED, OCR_FAILED')
    )
    op.create_index(op.f('ix_document_metadata_ocr_status'), 'document_metadata', ['ocr_status'], unique=False)

    op.add_column(
        'document_metadata',
        sa.Column('ocr_extracted_text', sa.Text(), nullable=True, comment='Full extracted text from OCR engine')
    )

    op.add_column(
        'document_metadata',
        sa.Column('ocr_confidence', sa.Float(), nullable=True, comment='OCR extraction confidence score (0.0 to 1.0)')
    )

    op.add_column(
        'document_metadata',
        sa.Column('ocr_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False, comment='Structured OCR metadata: page count, detected language, block bounding boxes, words, lines, etc.')
    )

    op.add_column(
        'document_metadata',
        sa.Column('ocr_completed_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when OCR extraction was completed')
    )

    op.add_column(
        'document_metadata',
        sa.Column('manual_review_required', sa.Boolean(), server_default='false', nullable=False, comment='Flag indicating document requires manual citizen/operator review')
    )
    op.create_index(op.f('ix_document_metadata_manual_review_required'), 'document_metadata', ['manual_review_required'], unique=False)

    op.add_column(
        'document_metadata',
        sa.Column('ocr_error_message', sa.String(length=500), nullable=True, comment='Error description if OCR processing encountered a failure')
    )


def downgrade() -> None:
    op.drop_column('document_metadata', 'ocr_error_message')
    op.drop_index(op.f('ix_document_metadata_manual_review_required'), table_name='document_metadata')
    op.drop_column('document_metadata', 'manual_review_required')
    op.drop_column('document_metadata', 'ocr_completed_at')
    op.drop_column('document_metadata', 'ocr_metadata')
    op.drop_column('document_metadata', 'ocr_confidence')
    op.drop_column('document_metadata', 'ocr_extracted_text')
    op.drop_index(op.f('ix_document_metadata_ocr_status'), table_name='document_metadata')
    op.drop_column('document_metadata', 'ocr_status')

