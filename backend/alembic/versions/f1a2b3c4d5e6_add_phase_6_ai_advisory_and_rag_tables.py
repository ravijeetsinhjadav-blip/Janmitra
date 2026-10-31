"""add phase 6 ai advisory and rag tables

Revision ID: f1a2b3c4d5e6
Revises: e9f8a7b6c5d4
Create Date: 2026-10-31 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'e9f8a7b6c5d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create scheme_knowledge_chunks table for RAG knowledge retrieval
    op.create_table(
        'scheme_knowledge_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='Primary UUID key for knowledge chunk'),
        sa.Column('scheme_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Associated scheme UUID'),
        sa.Column('chunk_title', sa.String(length=255), nullable=False, comment='Section/clause title'),
        sa.Column('chunk_category', sa.String(length=50), server_default='eligibility', nullable=False, comment='Category: eligibility, documents, benefits, process, faq'),
        sa.Column('chunk_content', sa.Text(), nullable=False, comment='Official verbatim or summarized text excerpt'),
        sa.Column('source_url', sa.String(length=500), nullable=False, comment='Official portal URL'),
        sa.Column('source_title', sa.String(length=255), nullable=False, comment='Publication or guideline document title'),
        sa.Column('source_reference', sa.String(length=255), nullable=True, comment='Specific chapter, clause, or paragraph reference'),
        sa.Column('source_freshness_status', sa.String(length=50), server_default='Verified Official Source', nullable=False, comment='Freshness status'),
        sa.Column('is_demo_data', sa.Boolean(), server_default='true', nullable=False, comment='Demo data flag'),
        sa.Column('embedding', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Dense vector representation'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Ingestion timestamp'),
        sa.ForeignKeyConstraint(['scheme_id'], ['schemes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_scheme_knowledge_chunks_id'), 'scheme_knowledge_chunks', ['id'], unique=False)
    op.create_index(op.f('ix_scheme_knowledge_chunks_scheme_id'), 'scheme_knowledge_chunks', ['scheme_id'], unique=False)
    op.create_index(op.f('ix_scheme_knowledge_chunks_chunk_title'), 'scheme_knowledge_chunks', ['chunk_title'], unique=False)
    op.create_index(op.f('ix_scheme_knowledge_chunks_chunk_category'), 'scheme_knowledge_chunks', ['chunk_category'], unique=False)

    # 2. Add Phase 6 columns to assessments table
    op.add_column(
        'assessments',
        sa.Column('advisory_guidance', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False, comment='Structured AI explanation, next steps, and citations (Phase 6)')
    )
    op.add_column(
        'assessments',
        sa.Column('readiness_breakdown', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False, comment='Component readiness scores: criteria match, document coverage, completeness, consistency (Phase 6)')
    )
    op.add_column(
        'assessments',
        sa.Column('language', sa.String(length=10), server_default='en', nullable=False, comment='Advisory language code: en, hi, gu (Phase 6)')
    )


def downgrade() -> None:
    # Remove Phase 6 columns from assessments table
    op.drop_column('assessments', 'language')
    op.drop_column('assessments', 'readiness_breakdown')
    op.drop_column('assessments', 'advisory_guidance')

    # Drop scheme_knowledge_chunks table
    op.drop_index(op.f('ix_scheme_knowledge_chunks_chunk_category'), table_name='scheme_knowledge_chunks')
    op.drop_index(op.f('ix_scheme_knowledge_chunks_chunk_title'), table_name='scheme_knowledge_chunks')
    op.drop_index(op.f('ix_scheme_knowledge_chunks_scheme_id'), table_name='scheme_knowledge_chunks')
    op.drop_index(op.f('ix_scheme_knowledge_chunks_id'), table_name='scheme_knowledge_chunks')
    op.drop_table('scheme_knowledge_chunks')

