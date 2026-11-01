import os
from pathlib import Path
import pytest
from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect
from sqlalchemy.engine import make_url
from app.shared.database import Base,database
import app.models

def test_migration_upgrade_downgrade_and_metadata_match():
    url=os.environ.get("TEST_MIGRATION_DATABASE_URL")
    if not url:pytest.skip("TEST_MIGRATION_DATABASE_URL not available")
    assert make_url(url).database.endswith("_migration_test")
    previous=os.environ.get("AROUNDYOU_MIGRATION_DATABASE_URL")
    os.environ["AROUNDYOU_MIGRATION_DATABASE_URL"]=url
    config=Config(str(Path(__file__).resolve().parents[1]/"alembic.ini"))
    engine,_=database(url)
    try:
        command.downgrade(config,"base")
        command.upgrade(config,"head")
        assert set(Base.metadata.tables)<=set(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert compare_metadata(MigrationContext.configure(connection),Base.metadata)==[]
        command.downgrade(config,"base")
        assert not set(Base.metadata.tables)&set(inspect(engine).get_table_names())
        command.upgrade(config,"head")
        command.upgrade(config,"head")
    finally:
        engine.dispose()
        if previous is None:os.environ.pop("AROUNDYOU_MIGRATION_DATABASE_URL",None)
        else:os.environ["AROUNDYOU_MIGRATION_DATABASE_URL"]=previous


def test_group2_upgrade_preserves_existing_group1_rows():
    url=os.environ.get('TEST_MIGRATION_DATABASE_URL')
    if not url:pytest.skip('TEST_MIGRATION_DATABASE_URL not available')
    assert make_url(url).database.endswith('_migration_test')
    previous=os.environ.get('AROUNDYOU_MIGRATION_DATABASE_URL');os.environ['AROUNDYOU_MIGRATION_DATABASE_URL']=url
    config=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'));engine,_=database(url)
    try:
        command.downgrade(config,'base');command.upgrade(config,'0001')
        with engine.begin() as connection:
            connection.execute(__import__('sqlalchemy').text("INSERT INTO users(id,external_auth_subject,display_name,active) VALUES ('migration-user','migration-subject','Preserved user',true)"))
            connection.execute(__import__('sqlalchemy').text("INSERT INTO events(id,creator_id,title,category,version) VALUES ('migration-event','migration-user','Preserved event','Education',7)"))
        command.upgrade(config,'head')
        with engine.connect() as connection:
            row=connection.execute(__import__('sqlalchemy').text("SELECT title,version,lifecycle FROM events WHERE id='migration-event'")).one()
            assert tuple(row)==('Preserved event',7,'created_unpublished')
    finally:
        engine.dispose()
        if previous is None:os.environ.pop('AROUNDYOU_MIGRATION_DATABASE_URL',None)
        else:os.environ['AROUNDYOU_MIGRATION_DATABASE_URL']=previous
