"""add email password authentication and password_hash

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-11-02 14:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b4c5d6e7f8a9'
down_revision = 'a3b4c5d6e7f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add password_hash column to users table
    op.add_column(
        'users',
        sa.Column(
            'password_hash',
            sa.String(length=255),
            nullable=True,
            comment='Argon2id or bcrypt password hash'
        )
    )


def downgrade() -> None:
    # Drop password_hash column from users table
    op.drop_column('users', 'password_hash')

