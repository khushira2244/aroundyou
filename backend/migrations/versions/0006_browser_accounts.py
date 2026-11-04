"""Add password accounts and revocable browser sessions without changing existing users."""
from alembic import op
import sqlalchemy as sa
revision='0006'
down_revision='0005'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('account_credentials',sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),primary_key=True),sa.Column('email',sa.String(254),nullable=False,unique=True),sa.Column('password_hash',sa.String(200),nullable=False),sa.Column('account_kind',sa.String(20),nullable=False),sa.Column('failures',sa.Integer(),nullable=False),sa.Column('locked_until',sa.DateTime(timezone=True)))
    op.create_table('browser_sessions',sa.Column('id',sa.String(36),primary_key=True),sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),sa.Column('token_hash',sa.String(64),nullable=False,unique=True),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),sa.Column('revoked',sa.Boolean(),nullable=False))
    op.create_index('ix_browser_sessions_user_id','browser_sessions',['user_id'])
def downgrade():
    op.drop_table('browser_sessions');op.drop_table('account_credentials')
