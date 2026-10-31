"""extend scheme model for phase 4

Revision ID: 7a8e5f3c9102
Revises: 4dcd7dfc601d
Create Date: 2026-10-31 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7a8e5f3c9102'
down_revision = '4dcd7dfc601d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add Phase 4 Scheme discovery & structured rule fields
    op.add_column('schemes', sa.Column('short_description', sa.String(length=500), nullable=True, comment='Concise summary for mobile cards'))
    op.add_column('schemes', sa.Column('category', sa.String(length=100), server_default='General', nullable=False, comment='Sector category'))
    op.create_index(op.f('ix_schemes_category'), 'schemes', ['category'], unique=False)
    
    op.add_column('schemes', sa.Column('benefits', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False, comment='List of benefits'))
    op.add_column('schemes', sa.Column('eligibility_criteria', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False, comment='Structured rule conditions'))
    op.add_column('schemes', sa.Column('required_profile_fields', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False, comment='Required profile field names'))
    op.add_column('schemes', sa.Column('application_process', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False, comment='Application steps'))
    op.add_column('schemes', sa.Column('required_documents', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False, comment='Informational checklist'))
    op.add_column('schemes', sa.Column('eligibility_source_reference', sa.String(length=500), nullable=True, comment='Supporting official source reference for eligibility criteria'))
    op.add_column('schemes', sa.Column('benefits_source_reference', sa.String(length=500), nullable=True, comment='Supporting official source reference for scheme benefits'))
    op.add_column('schemes', sa.Column('source_freshness_status', sa.String(length=50), server_default='Verified Official Source', nullable=False, comment='Verification freshness status'))
    op.add_column('schemes', sa.Column('source_verification_details', sa.Text(), nullable=True, comment='Supporting official source verification references and limitations'))
    
    op.add_column('schemes', sa.Column('status', sa.String(length=20), server_default='active', nullable=False, comment='active, inactive, discontinued'))
    op.create_index(op.f('ix_schemes_status'), 'schemes', ['status'], unique=False)
    
    op.add_column('schemes', sa.Column('is_demo_data', sa.Boolean(), server_default='false', nullable=False, comment='Designates test seed data vs live records'))
    op.create_index(op.f('ix_schemes_is_demo_data'), 'schemes', ['is_demo_data'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_schemes_is_demo_data'), table_name='schemes')
    op.drop_column('schemes', 'is_demo_data')
    op.drop_index(op.f('ix_schemes_status'), table_name='schemes')
    op.drop_column('schemes', 'status')
    op.drop_column('schemes', 'source_verification_details')
    op.drop_column('schemes', 'source_freshness_status')
    op.drop_column('schemes', 'benefits_source_reference')
    op.drop_column('schemes', 'eligibility_source_reference')
    op.drop_column('schemes', 'required_documents')
    op.drop_column('schemes', 'application_process')
    op.drop_column('schemes', 'required_profile_fields')
    op.drop_column('schemes', 'eligibility_criteria')
    op.drop_column('schemes', 'benefits')
    op.drop_index(op.f('ix_schemes_category'), table_name='schemes')
    op.drop_column('schemes', 'category')
    op.drop_column('schemes', 'short_description')

