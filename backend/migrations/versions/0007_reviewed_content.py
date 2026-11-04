"""Preserve human-reviewed corrections separately from immutable AI proposals."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision='0007'
down_revision='0006'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('review_decisions',sa.Column('reviewed_content',postgresql.JSONB(),nullable=True))

def downgrade():
    op.drop_column('review_decisions','reviewed_content')
