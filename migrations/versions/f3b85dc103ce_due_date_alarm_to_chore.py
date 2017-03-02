"""Add due date and alarm date to the chore (https://github.com/andreoliwa/python-dontforget/issues/98).


Revision ID: f3b85dc103ce
Revises: a2de422d22b8
Create Date: 2017-03-02 00:44:15.483580
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'f3b85dc103ce'
down_revision = 'a2de422d22b8'


def upgrade():
    """Upgrade the database."""
    op.add_column('alarm', sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False))
    # TODO Augusto: What about those not null columns? they will fail when XXX (I forgot)
    op.add_column('chore', sa.Column('alarm_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('chore', sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False))
    op.add_column('chore', sa.Column('due_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('chore', sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    """Downgrade the database."""
    op.drop_column('chore', 'updated_at')
    op.drop_column('chore', 'due_at')
    op.drop_column('chore', 'created_at')
    op.drop_column('chore', 'alarm_at')
    op.drop_column('alarm', 'created_at')
