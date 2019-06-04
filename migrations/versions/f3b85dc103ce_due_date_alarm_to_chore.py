# -*- coding: utf-8 -*-
"""Add due date and alarm date to the chore (https://github.com/andreoliwa/python-dontforget/issues/98).

Revision ID: f3b85dc103ce
Revises: a2de422d22b8
Create Date: 2017-03-02 00:44:15.483580
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
from dontforget.database import add_required_column

revision = "f3b85dc103ce"
down_revision = "a2de422d22b8"

ALARM_ACTION_ENUM = postgresql.ENUM("complete", "snooze", "jump", "pause", name="alarm_action_enum", create_type=False)

ALARM_STATE_ENUM = postgresql.ENUM(
    "unseen", "displayed", "skipped", "snoozed", "completed", "killed", name="alarm_state_enum", create_type=False
)


def upgrade():
    """Upgrade the database."""
    ALARM_ACTION_ENUM.create(op.get_bind())

    op.add_column("chore", sa.Column("due_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("chore", sa.Column("alarm_at", sa.TIMESTAMP(timezone=True), nullable=True))
    add_required_column("chore", "created_at", sa.TIMESTAMP(timezone=True), "alarm_start")
    add_required_column("chore", "updated_at", sa.TIMESTAMP(timezone=True), "alarm_start")
    op.drop_column("chore", "alarm_start")

    op.execute(
        """UPDATE chore
SET due_at = alarm.next_at,
  alarm_at = coalesce(alarm.original_at, alarm.next_at)
FROM alarm
WHERE alarm.chore_id = chore.id AND alarm.current_state = 'unseen';
"""
    )

    # Alarm date should not be inferior to the due date.
    op.execute(
        """UPDATE chore
SET alarm_at = due_at
WHERE alarm_at < chore.due_at
"""
    )

    op.add_column("alarm", sa.Column("due_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("alarm", sa.Column("alarm_at", sa.TIMESTAMP(timezone=True), nullable=True))
    add_required_column("alarm", "action", ALARM_ACTION_ENUM, "'snooze'")
    op.add_column("alarm", sa.Column("snooze_repetition", sa.String(), nullable=True))
    add_required_column("alarm", "created_at", sa.TIMESTAMP(timezone=True), "next_at")

    op.execute(
        """UPDATE alarm
SET due_at          = next_at,
  alarm_at          = original_at,
  snooze_repetition = last_snooze,
  "action"          = CASE current_state
                      WHEN 'skipped'
                        THEN 'jump'
                      WHEN 'snoozed'
                        THEN 'snooze'
                      WHEN 'completed'
                        THEN 'complete'
                      WHEN 'killed'
                        THEN 'pause'
                      ELSE 'snooze'
                      END :: alarm_action_enum
"""
    )

    op.drop_column("alarm", "next_at")
    op.drop_column("alarm", "original_at")
    op.drop_column("alarm", "last_snooze")
    op.drop_column("alarm", "current_state")
    ALARM_STATE_ENUM.drop(op.get_bind())

    op.drop_table("roles")
    op.drop_table("users")


def downgrade():
    """Downgrade the database."""
    ALARM_STATE_ENUM.create(op.get_bind())

    add_required_column("chore", "alarm_start", postgresql.TIMESTAMP(timezone=True), "created_at")
    op.drop_column("chore", "updated_at")
    op.drop_column("chore", "due_at")
    op.drop_column("chore", "created_at")
    op.drop_column("chore", "alarm_at")

    op.add_column("alarm", sa.Column("original_at", postgresql.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("alarm", sa.Column("last_snooze", sa.VARCHAR(), autoincrement=False, nullable=True))
    add_required_column("alarm", "next_at", postgresql.TIMESTAMP(timezone=True), "created_at")

    # This UPDATE will destroy history and mark everything as unseen.
    # The right thing would be a manual UPDATE, mapping old enum items to new ones.
    add_required_column("alarm", "current_state", ALARM_STATE_ENUM, "'unseen'")

    op.drop_column("alarm", "created_at")
    op.drop_column("alarm", "snooze_repetition")
    op.drop_column("alarm", "due_at")
    op.drop_column("alarm", "alarm_at")
    op.drop_column("alarm", "action")
    ALARM_ACTION_ENUM.drop(op.get_bind())

    op.create_table(
        "users",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("username", sa.VARCHAR(length=80), autoincrement=False, nullable=False),
        sa.Column("email", sa.VARCHAR(length=80), autoincrement=False, nullable=False),
        sa.Column("password", sa.VARCHAR(length=128), autoincrement=False, nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
        sa.Column("first_name", sa.VARCHAR(length=30), autoincrement=False, nullable=True),
        sa.Column("last_name", sa.VARCHAR(length=30), autoincrement=False, nullable=True),
        sa.Column("active", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column("is_admin", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("id", name="users_pkey"),
        sa.UniqueConstraint("email", name="users_email_key"),
        sa.UniqueConstraint("username", name="users_username_key"),
        postgresql_ignore_search_path=False,
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=80), autoincrement=False, nullable=False),
        sa.Column("user_id", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="roles_user_id_fkey"),
        sa.PrimaryKeyConstraint("id", name="roles_pkey"),
        sa.UniqueConstraint("name", name="roles_name_key"),
    )
