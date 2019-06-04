# -*- coding: utf-8 -*-
"""Chore.

Revision ID: 1b2288a0f6
Revises: 313230cbc09
Create Date: 2015-11-08 20:03:20.683669
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1b2288a0f6"
down_revision = "313230cbc09"


def upgrade():
    """Upgrade the database."""
    op.create_table(
        "chore",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("title"),
    )


def downgrade():
    """Downgrade the database."""
    op.drop_table("chore")
