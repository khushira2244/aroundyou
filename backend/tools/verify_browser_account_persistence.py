"""Non-destructive Docker-development smoke check; retains explicitly labeled check records.

Uses the actual FastAPI application and PostgreSQL via TestClient. This is not a
host-browser/network test. Credentials are generated in memory and never printed.
"""
import secrets
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import create_app
from app.settings import Settings
from app.shared.database import database
from app.access.accounts import COOKIE
import app.models

def main():
    settings=Settings()
    if settings.app_env!='development':raise SystemExit('Development only')
    engine,factory=database(settings.database_url.get_secret_value())
    with engine.connect() as db:
        assert db.execute(text('select current_database()')).scalar()=='aroundyou'
        assert db.execute(text('select version_num from alembic_version')).scalar()=='0006'
        before=db.execute(text('select count(*) from users')).scalar()
    app=create_app(settings,factory);origin={'Origin':'http://127.0.0.1:5173'}
    suffix=secrets.token_hex(8);password=secrets.token_urlsafe(24)
    with TestClient(app) as client:
        r=client.post('/v1/auth/signup',json={'name':'Integration check personal','email':suffix+'@integration.invalid','password':password,'kind':'personal'},headers=origin)
        assert r.status_code==201,r.status_code
        account=r.json()['data']['identity']['accountId']
        r=client.post('/v1/events/drafts',json={},headers={**origin,'Idempotency-Key':suffix+'-draft'})
        assert r.status_code==201,r.status_code
        state=r.json()['data'];eid=state['event']['id'];form=state['runtime']['draft']['creation_details']
        form.update(title='Technical integration check — private draft',category='Education',city='Hazaribagh',country='India')
        r=client.patch('/v1/events/'+eid+'/draft',json={'step':2,'form':form},headers={**origin,'Idempotency-Key':suffix+'-save','If-Match':str(state['runtime']['revision'])})
        assert r.status_code==200,r.status_code
        token=client.cookies.get(COOKIE)
    with TestClient(create_app(settings,factory)) as restored:
        restored.cookies.set(COOKIE,token)
        assert restored.get('/v1/me').json()['data']['identity']['accountId']==account
        item=next(x for x in restored.get('/v1/me/events').json()['data']['items'] if x['event']['id']==eid)
        assert item['resume_path']=='/create/2' and item['event']['title']==form['title']
        assert restored.post('/v1/auth/logout',headers=origin).status_code==200
        restored.cookies.set(COOKIE,token)
        assert restored.get('/v1/me').status_code==401
        restored.cookies.clear()
        assert restored.post('/v1/auth/signin',json={'email':suffix+'@integration.invalid','password':password},headers=origin).status_code==200
        assert restored.post('/v1/auth/logout',headers=origin).status_code==200
    with engine.connect() as db:
        assert db.execute(text('select count(*) from users')).scalar()==before+1
    print('PASS: actual Docker PostgreSQL signup/signin, fresh-app session restoration, draft persistence/resume and logout revocation.')
    print('Retained one labeled technical-check account and private draft; no existing records replaced. No provider calls.')
    engine.dispose()

if __name__=='__main__':main()
