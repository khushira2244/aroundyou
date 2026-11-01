"""Immutable context snapshots for clarification and accepted interpretation history."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('event_context_revisions',sa.Column('snapshot',postgresql.JSONB(),nullable=False,server_default=sa.text("'{}'::jsonb")))
    op.alter_column('event_context_revisions','snapshot',server_default=None)

def downgrade():
    op.drop_column('event_context_revisions','snapshot')
