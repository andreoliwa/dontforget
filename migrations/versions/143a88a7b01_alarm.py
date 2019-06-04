# -*- coding: utf-8 -*-
"""Alarm.

Revision ID: 143a88a7b01
Revises: 1b2288a0f6
Create Date: 2015-11-09 01:39:43.336965
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from dontforget.database import add_required_column

# revision identifiers, used by Alembic.
revision = "143a88a7b01"
down_revision = "1b2288a0f6"

ALARM_STATE_ENUM = postgresql.ENUM(
    "unseen", "displayed", "skipped", "snoozed", "completed", "killed", name="alarm_state_enum", create_type=False
)


def upgrade():
    """Upgrade the database."""
    ALARM_STATE_ENUM.create(op.get_bind())

    op.create_table(
        "alarm",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("current_state", ALARM_STATE_ENUM, nullable=False),
        sa.Column("next_at", sa.TIMESTAMP(True), nullable=False),
        sa.Column("chore_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["chore_id"], ["chore.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("chore") as batch_op:
        batch_op.add_column(sa.Column("alarm_end", sa.TIMESTAMP(True), nullable=True))
    add_required_column("chore", "alarm_start", sa.TIMESTAMP(True), "current_timestamp")


def downgrade():
    """Downgrade the database."""
    with op.batch_alter_table("chore") as batch_op:
        batch_op.drop_column("alarm_start")
        batch_op.drop_column("alarm_end")
    op.drop_table("alarm")

    ALARM_STATE_ENUM.drop(op.get_bind())
