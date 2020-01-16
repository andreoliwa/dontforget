"""Last snooze.

Revision ID: 250e5b590f7
Revises: 3362b720863
Create Date: 2015-12-02 23:46:39.978621
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "250e5b590f7"
down_revision = "3362b720863"


def upgrade():
    """Upgrade the database."""
    with op.batch_alter_table("alarm") as batch_op:
        batch_op.add_column(sa.Column("last_snooze", sa.String(), nullable=True))


def downgrade():
    """Downgrade the database."""
    with op.batch_alter_table("alarm") as batch_op:
        batch_op.drop_column("last_snooze")
