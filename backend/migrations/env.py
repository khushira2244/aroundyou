import os
from alembic import context
from sqlalchemy import create_engine
from app.shared.database import Base
import app.models
from app.settings import Settings

# Explicit override used for isolated tests/admin migrations; never prints the URL.
url=os.environ.get("AROUNDYOU_MIGRATION_DATABASE_URL")
if not url: url=Settings().database_url.get_secret_value()
if context.is_offline_mode():
    context.configure(url=url,target_metadata=Base.metadata,literal_binds=True,dialect_opts={"paramstyle":"named"})
    with context.begin_transaction(): context.run_migrations()
else:
    engine=create_engine(url,hide_parameters=True)
    with engine.connect() as connection:
        context.configure(connection=connection,target_metadata=Base.metadata,compare_type=True)
        with context.begin_transaction(): context.run_migrations()
    engine.dispose()
