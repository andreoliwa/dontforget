"""Alarm.

Revision ID: 143a88a7b01
Revises: 1b2288a0f6
Create Date: 2015-11-09 01:39:43.336965
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
from helpers.alembic import add_required_column

revision = '143a88a7b01'
down_revision = '1b2288a0f6'


def upgrade():
    """Upgrade the database."""
    op.create_table('alarm',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('current_state', sa.Enum('unseen', 'skipped', 'snoozed', 'done', name='alarm_state_enum'),
                              nullable=False),
                    sa.Column('next_at', sa.DateTime(), nullable=False),
                    sa.Column('chore_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['chore_id'], ['chore.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    with op.batch_alter_table('chore') as batch_op:
        batch_op.add_column(sa.Column('alarm_end', sa.DateTime(), nullable=True))
        add_required_column('chore', 'alarm_start', sa.DateTime(), 'current_timestamp', batch_operation=batch_op)


def downgrade():
    """Downgrade the database."""
    op.drop_column('chore', 'alarm_start')
    op.drop_column('chore', 'alarm_end')
    op.drop_table('alarm')
