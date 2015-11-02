"""${message}.

Revision ID: ${up_revision}
Revises: ${down_revision}
Create Date: ${create_date}
"""

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

def upgrade():
    """Upgrade the database."""
    ${upgrades if upgrades else "pass"}


def downgrade():
    """Downgrade the database."""
    ${downgrades if downgrades else "pass"}
