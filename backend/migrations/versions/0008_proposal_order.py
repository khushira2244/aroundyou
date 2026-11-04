"""Stable proposal/conversation review order."""
from alembic import op
import sqlalchemy as sa
revision='0008'
down_revision='0007'
branch_labels=None
depends_on=None
def upgrade():op.add_column('ai_proposals',sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()))
def downgrade():op.drop_column('ai_proposals','created_at')
