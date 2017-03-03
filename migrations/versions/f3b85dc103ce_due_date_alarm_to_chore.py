"""Add due date and alarm date to the chore (https://github.com/andreoliwa/python-dontforget/issues/98).

Revision ID: f3b85dc103ce
Revises: a2de422d22b8
Create Date: 2017-03-02 00:44:15.483580
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f3b85dc103ce'
down_revision = 'a2de422d22b8'

ALARM_ACTION_ENUM = postgresql.ENUM('complete', 'snooze', 'jump', 'finish',
                                    name='alarm_action_enum', create_type=False)

ALARM_STATE_ENUM = postgresql.ENUM('unseen', 'displayed', 'skipped', 'snoozed', 'completed', 'killed',
                                   name='alarm_state_enum', create_type=False)


def upgrade():
    """Upgrade the database."""
    # TODO Augusto: What about those not null columns? they will fail when XXX (I forgot)
    ALARM_ACTION_ENUM.create(op.get_bind())

    op.add_column('chore', sa.Column('due_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('chore', sa.Column('alarm_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('chore', sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False))
    op.add_column('chore', sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False))
    op.drop_column('chore', 'alarm_start')

    op.add_column('alarm', sa.Column('due_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('alarm', sa.Column('alarm_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('alarm', sa.Column('action', ALARM_ACTION_ENUM, nullable=False))
    op.add_column('alarm', sa.Column('snooze_text', sa.String(), nullable=True))
    op.add_column('alarm', sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False))
    op.drop_column('alarm', 'current_state')
    op.drop_column('alarm', 'next_at')
    op.drop_column('alarm', 'last_snooze')
    op.drop_column('alarm', 'original_at')

    ALARM_STATE_ENUM.drop(op.get_bind())


def downgrade():
    """Downgrade the database."""
    ALARM_STATE_ENUM.create(op.get_bind())

    op.drop_column('chore', 'updated_at')
    op.drop_column('chore', 'due_at')
    op.drop_column('chore', 'created_at')
    op.drop_column('chore', 'alarm_at')
    op.add_column('chore',
                  sa.Column('alarm_start', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False))

    op.drop_column('alarm', 'created_at')
    op.add_column('alarm',
                  sa.Column('original_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True))
    op.add_column('alarm', sa.Column('last_snooze', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('alarm',
                  sa.Column('next_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False))
    op.add_column('alarm', sa.Column('current_state', ALARM_STATE_ENUM, autoincrement=False, nullable=False))
    op.drop_column('alarm', 'snooze_text')
    op.drop_column('alarm', 'due_at')
    op.drop_column('alarm', 'alarm_at')
    op.drop_column('alarm', 'action')

    ALARM_ACTION_ENUM.drop(op.get_bind())
