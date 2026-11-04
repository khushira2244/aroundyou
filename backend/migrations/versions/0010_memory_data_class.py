"""Explicit event provenance for reusable lessons; existing events remain unclassified."""
from alembic import op
import sqlalchemy as sa
revision='0010'
down_revision='0009'
branch_labels=None
depends_on=None
def upgrade():
    op.add_column('events',sa.Column('memory_data_class',sa.String(20),nullable=False,server_default='unclassified'))
    op.create_check_constraint('ck_event_memory_data_class','events',"memory_data_class IN ('unclassified','real','synthetic')")
def downgrade():
    op.drop_constraint('ck_event_memory_data_class','events',type_='check');op.drop_column('events','memory_data_class')
