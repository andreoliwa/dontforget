"""Add original_at date to the alarm.

Revision ID: a2de422d22b8
Revises: 250e5b590f7
Create Date: 2017-01-06 12:26:48.916280
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'a2de422d22b8'
down_revision = '250e5b590f7'


def upgrade():
    """Upgrade the database."""
    op.add_column('alarm', sa.Column('original_at', sa.DateTime(), nullable=True))


def downgrade():
    """Downgrade the database."""
    with op.batch_alter_table('alarm') as batch_op:
        batch_op.drop_column('original_at')
