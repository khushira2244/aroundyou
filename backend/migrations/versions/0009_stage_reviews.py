"""Independent stage work and actor review fingerprints."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0009'
down_revision='0008'
branch_labels=None
depends_on=None
def upgrade():op.add_column('planning_drafts',sa.Column('stage_reviews',JSONB,nullable=False,server_default=sa.text("'{}'::jsonb")))
def downgrade():op.drop_column('planning_drafts','stage_reviews')
