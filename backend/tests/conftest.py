import os
from pathlib import Path
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from fastapi.testclient import TestClient
from app.shared.database import database
from app.shared.unit_of_work import unit_of_work
from app.shared.types import uid
from app.access.models import User, EventGrant
from app.events.models import Event
from app.events.source_revisions import append_context
from app.settings import Settings
from app.main import create_app
from app.access.authentication import issue_token
import app.models as registered_models

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope="session")
def factory():
    url=os.environ.get("TEST_DATABASE_URL")
    if not url: pytest.skip("TEST_DATABASE_URL unavailable: PostgreSQL integration tests not executed")
    if not make_url(url).database.endswith("_test"):
        pytest.fail("Refusing to truncate a database whose name does not end in _test")
    os.environ["AROUNDYOU_MIGRATION_DATABASE_URL"]=url
    config=Config(str(ROOT/"alembic.ini"));command.downgrade(config,"base");command.upgrade(config,"head")
    engine,factory=database(url)
    try: yield factory
    finally: engine.dispose()

@pytest.fixture
def seeded(factory):
    with unit_of_work(factory) as db:
        names=','.join('"'+x+'"' for x in registered_models.User.metadata.tables)
        db.execute(text("TRUNCATE "+names+" CASCADE"))
        owner=User(id=uid(),external_auth_subject="owner-subject",display_name="Owner")
        outsider=User(id=uid(),external_auth_subject="outsider-subject",display_name="Outsider")
        viewer=User(id=uid(),external_auth_subject="viewer-subject",display_name="Viewer")
        db.add_all([owner,outsider,viewer]);db.flush()
        event=Event(id=uid(),creator_id=owner.id,title="Community reading lab",category="Education")
        other=Event(id=uid(),creator_id=outsider.id,title="Garden study",category="Environment")
        db.add_all([event,other]);db.flush()
        permissions=["event:read","memory:read","memory:extract","memory:review","source:private","context:write","plan:write","source:verify"]
        for e,u in [(event,owner),(other,outsider)]:
            for permission in permissions:db.add(EventGrant(event_id=e.id,user_id=u.id,permission=permission,scope={}))
        for permission in ["event:read","memory:read"]:db.add(EventGrant(event_id=event.id,user_id=viewer.id,permission=permission,scope={}))
        db.flush()
        source=append_context(db,owner.id,event.id,"Reading workshop requires two available projectors",event.version,{"category":"Education","tags":["learning"],"work_pattern":"workshop","conditions":["indoor"],"unknowns":["power availability"]})
        result={"owner":owner.id,"outsider":outsider.id,"viewer":viewer.id,"event":event.id,"other":other.id,"source":source.id,"ref":{"source_kind":"context","source_id":source.id,"source_revision":source.sequence,"source_digest":source.content_hash}}
    return result

@pytest.fixture
def settings():
    return Settings(_env_file=None,database_url="postgresql+psycopg://unused:unused@localhost/test",session_secret="test-only-secret-material-at-least-32-bytes",auth_issuer="tests",auth_audience="aroundyou-tests")

@pytest.fixture
def app(factory,settings): return create_app(settings,factory)
@pytest.fixture
def client(app):
    with TestClient(app) as client: yield client
@pytest.fixture
def headers(settings):
    def make(subject="owner-subject",key="test-key",version="1"):
        return {"Authorization":"Bearer "+issue_token(settings,subject),"Idempotency-Key":key,"If-Match":version}
    return make
