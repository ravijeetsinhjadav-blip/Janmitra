"""add analytics provenance and category rule verification fields

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-11-14 20:49:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'f8a9b0c1d2e3'
down_revision = 'e7f8a9b0c1d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Update scheme_analytics_datasets with complete provenance fields
    with op.batch_alter_table('scheme_analytics_datasets') as batch_op:
        batch_op.add_column(sa.Column('report_title', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('geographic_scope', sa.String(length=100), nullable=False, server_default='National'))
        batch_op.add_column(sa.Column('metric_definition', sa.Text(), nullable=True))

    # 2. Update scheme_category_rules with geographic scope and verification status
    with op.batch_alter_table('scheme_category_rules') as batch_op:
        batch_op.add_column(sa.Column('geographic_scope', sa.String(length=100), nullable=False, server_default='National'))
        batch_op.add_column(sa.Column('verification_status', sa.String(length=50), nullable=False, server_default='Verified'))


def downgrade() -> None:
    with op.batch_alter_table('scheme_category_rules') as batch_op:
        batch_op.drop_column('verification_status')
        batch_op.drop_column('geographic_scope')

    with op.batch_alter_table('scheme_analytics_datasets') as batch_op:
        batch_op.drop_column('metric_definition')
        batch_op.drop_column('geographic_scope')
        batch_op.drop_column('report_title')
