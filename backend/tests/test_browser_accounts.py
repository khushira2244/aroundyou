from sqlalchemy import select
from app.access.accounts import Credential, BrowserSession, COOKIE
from app.shared.unit_of_work import unit_of_work

ORIGIN={'Origin':'http://127.0.0.1:5173'}
ACCOUNT={'name':'New Organizer','email':'Test.New@Example.org','password':'a-long-test-password','kind':'personal'}

def signup(client,**changes):
    return client.post('/v1/auth/signup',json={**ACCOUNT,**changes},headers=ORIGIN)

def test_signup_cookie_restore_logout_and_password_hash(client,seeded,factory):
    r=signup(client);assert r.status_code==201,r.text
    identity=r.json()['data']['identity'];assert identity['kind']=='personal'
    assert 'HttpOnly' in r.headers['set-cookie'] and 'SameSite=lax' in r.headers['set-cookie']
    token=client.cookies.get(COOKIE)
    assert client.get('/v1/me').json()['data']['identity']==identity
    with unit_of_work(factory) as db:
        c=db.get(Credential,identity['accountId']);assert c.email=='test.new@example.org'
        assert ACCOUNT['password'] not in c.password_hash
        assert db.scalar(select(BrowserSession)).token_hash!=token
    assert client.post('/v1/auth/logout',headers=ORIGIN).status_code==200
    client.cookies.set(COOKIE,token)
    assert client.get('/v1/me').status_code==401
    client.cookies.clear()
    assert client.post('/v1/auth/signin',json={'email':' TEST.NEW@example.org ','password':ACCOUNT['password']},headers=ORIGIN).status_code==200

def test_no_email_only_login_duplicate_invalid_password_and_csrf(client,seeded):
    assert signup(client,password='').status_code==422
    assert signup(client,email='broken').status_code==422
    assert signup(client,password='short').status_code==422
    assert signup(client).status_code==201
    assert signup(client,email='test.new@example.org').status_code==409
    assert client.post('/v1/auth/logout',headers={'Origin':'https://evil.example'}).status_code==403
    assert client.post('/v1/auth/signin',json={'email':ACCOUNT['email'],'password':''},headers=ORIGIN).status_code==401
    assert client.post('/v1/events/drafts',json={},headers={'Idempotency-Key':'csrf-test','Origin':'https://evil.example'}).status_code==403

def test_lockout_persists_and_role_is_server_owned(client,seeded):
    assert signup(client,kind='sponsor').status_code==201
    assert client.get('/v1/me').json()['data']['identity']['kind']=='sponsor'
    assert client.post('/v1/events/drafts',json={},headers={**ORIGIN,'Idempotency-Key':'sponsor-create'}).status_code==403
    for _ in range(5):
        assert client.post('/v1/auth/signin',json={'email':ACCOUNT['email'],'password':'wrong'},headers=ORIGIN).status_code==401
    assert client.post('/v1/auth/signin',json={'email':ACCOUNT['email'],'password':ACCOUNT['password']},headers=ORIGIN).status_code==401

def test_new_account_persists_private_draft_and_resume_step(client,seeded):
    assert signup(client).status_code==201
    r=client.post('/v1/events/drafts',json={},headers={**ORIGIN,'Idempotency-Key':'new-draft'})
    assert r.status_code==201,r.text
    state=r.json()['data'];eid=state['event']['id']
    form=state['runtime']['draft']['creation_details'];form['title']='New private education event'
    r=client.patch(f'/v1/events/{eid}/draft',json={'step':2,'form':form},headers={**ORIGIN,'Idempotency-Key':'save-draft','If-Match':str(state['runtime']['revision'])})
    assert r.status_code==200,r.text
    rows=client.get('/v1/me/events').json()['data']['items']
    assert len(rows)==1 and rows[0]['resume_path']=='/create/2'
    assert rows[0]['event']['title']==form['title']
    public=client.get('/v1/events').json()['data']['items']
    assert all(e['id']!=eid for e in public)
    client.post('/v1/auth/logout',headers=ORIGIN)
    assert client.get(f'/v1/events/{eid}').status_code==401

def test_password_whitespace_is_preserved(client,seeded):
    password='  a-long-test-password  '
    assert signup(client,password=password).status_code==201
    client.post('/v1/auth/logout',headers=ORIGIN)
    assert client.post('/v1/auth/signin',json={'email':ACCOUNT['email'],'password':password.strip()},headers=ORIGIN).status_code==401
    assert client.post('/v1/auth/signin',json={'email':ACCOUNT['email'],'password':password},headers=ORIGIN).status_code==200

def test_sponsor_registration_uses_membership_and_prevents_duplicate(client,seeded):
    assert signup(client,kind='sponsor').status_code==201
    profile={'name':'Community support organization','type':'Nonprofit','description':'Supports community education','contact_name':'Representative','email':'rep@example.org','city':'Hazaribagh','country':'India','focus':['Education'],'capabilities':['materials'],'coverage':['Hazaribagh']}
    r=client.post('/v1/organizations/draft',json={'profile':profile},headers={**ORIGIN,'Idempotency-Key':'organization-first'})
    assert r.status_code==200,r.text
    org=r.json()['data']['organization_id']
    r=client.post(f'/v1/organizations/{org}/registration/complete',json={},headers={**ORIGIN,'Idempotency-Key':'complete-org'})
    assert r.status_code==200,r.text
    portal=client.get('/v1/me/sponsor-portal').json()['data']
    assert portal['organization']['id']==org and portal['organization']['registration_status']=='registered_unverified'
    assert portal['membership']['permission']=='representative'
    assert client.post('/v1/organizations/draft',json={'profile':profile},headers={**ORIGIN,'Idempotency-Key':'duplicate-org'}).status_code==409
    client.post('/v1/auth/logout',headers=ORIGIN)
    assert signup(client,email='outsider@example.org').status_code==201
    assert client.get(f'/v1/organizations/{org}/sponsor-portal').status_code==404
    assert client.post('/v1/organizations/draft',json={'profile':profile},headers={**ORIGIN,'Idempotency-Key':'personal-org'}).status_code==403


from tests.test_group2 import flow

def test_created_event_list_opens_existing_dashboard_without_a_plan(flow):
    flow.new('Owned event before planning');flow.create()
    rows=flow.client.get('/v1/me/events',headers=flow.headers()).json()['data']['items']
    own=next(r for r in rows if r['event']['id']==flow.id)
    assert own['organizer'] and own['resume_path']==f'/events/{flow.id}/manage/overview'
    assert all(r['event']['title']!='Garden study' for r in rows)
    assert flow.get('/profile?preview=organizer').status_code==200
    assert flow.get('/organizer/dashboard').status_code==200

