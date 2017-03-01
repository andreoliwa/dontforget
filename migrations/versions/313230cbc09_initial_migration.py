"""Initial migration.

Revision ID: 313230cbc09
Revises: None
Create Date: 2015-11-01 13:49:00.896469

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '313230cbc09'
down_revision = None


def upgrade():
    """Upgrade the database."""
    op.create_table('users',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('username', sa.String(length=80), nullable=False),
                    sa.Column('email', sa.String(length=80), nullable=False),
                    sa.Column('password', sa.String(length=128), nullable=True),
                    sa.Column('created_at', sa.TIMESTAMP(True), nullable=False),
                    sa.Column('first_name', sa.String(length=30), nullable=True),
                    sa.Column('last_name', sa.String(length=30), nullable=True),
                    sa.Column('active', sa.Boolean(), nullable=True),
                    sa.Column('is_admin', sa.Boolean(), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('email'),
                    sa.UniqueConstraint('username')
                    )
    op.create_table('roles',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(length=80), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=True),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('name')
                    )


def downgrade():
    """Downgrade the database."""
    op.drop_table('roles')
    op.drop_table('users')
