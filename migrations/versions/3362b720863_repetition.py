"""Repetition.

Revision ID: 3362b720863
Revises: 143a88a7b01
Create Date: 2015-11-26 00:40:43.789890
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
from helpers.alembic import add_required_column

revision = '3362b720863'
down_revision = '143a88a7b01'


def upgrade():
    """Upgrade the database."""
    with op.batch_alter_table('alarm') as batch_op:
        add_required_column('alarm', 'updated_at', sa.DateTime(), 'current_timestamp', batch_operation=batch_op)

    with op.batch_alter_table('chore') as batch_op:
        add_required_column('chore', 'repeat_from_completed', sa.Boolean(), False, batch_operation=batch_op)
        batch_op.add_column(sa.Column('repetition', sa.String(), nullable=True))


def downgrade():
    """Downgrade the database."""
    with op.batch_alter_table('chore') as batch_op:
        batch_op.drop_column('repetition')
        batch_op.drop_column('repeat_from_completed')

    with op.batch_alter_table('alarm') as batch_op:
        batch_op.drop_column('updated_at')
