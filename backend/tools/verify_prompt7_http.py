"""Prompt 7 connected development HTTP check. No provider calls; no existing-data reset."""
import sys,json,secrets,socket,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import httpx,uvicorn
from sqlalchemy import select,text
from app.settings import Settings
from app.main import create_app
from app.shared.database import database
from app.access.models import User
from app.access.accounts import Credential
from app.access.authentication import issue_token
from tests.test_group3 import Scenario
from tests.test_group2 import FORM

def main():
    settings=Settings(meta_ai_enabled=False,modal_memory_enabled=False);engine,factory=database(settings.database_url.get_secret_value());app=create_app(settings,factory)
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];server=uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False));thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
    for _ in range(100):
        if server.started:break
        time.sleep(.1)
    client=httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=30,headers={'Origin':'http://127.0.0.1:5173'});output={'transport':'actual HTTP / configured development PostgreSQL','provider_calls':0,'checks':[]}
    try:
        subjects=[];ids=[]
        for n in range(2):
            email=secrets.token_hex(8)+'@example.test';password=secrets.token_urlsafe(24)
            r=client.post('/v1/auth/signup',json={'name':'Prompt7 synthetic verification '+str(n),'email':email,'password':password,'kind':'personal'});assert r.is_success,r.text
            assert client.post('/v1/auth/logout').is_success;assert client.post('/v1/auth/signin',json={'email':email,'password':password}).is_success
            with factory() as db:
                credential=db.scalar(select(Credential).where(Credential.email==email));user=db.get(User,credential.user_id);subjects.append(user.external_auth_subject);ids.append(user.id)
        client.post('/v1/auth/logout')
        def headers(subject='owner-subject',key='prompt7',version='1'):return {'Authorization':'Bearer '+issue_token(settings,subjects[0] if subject=='owner-subject' else subject),'Idempotency-Key':key,'If-Match':str(version)}
        FORM.update(purpose='Synthetic Prompt7 integration verification, no real event',executionIntent='Synthetic testing only. No actual activity or outcome represented.')
        s=Scenario(client,headers,factory).build(capacity=1);output['event_id']=s.id
        s.call('/memory/data-class',{'data_class':'synthetic','reason':'Dedicated synthetic HTTP verification event'})
        a=s.apply(subjects[1]);s.approve(a);offer=s.offer(a);s.call('/assignments/'+offer['id']+'/accept',{'terms_key':offer['terms_key']},subjects[1])
        issue=s.call('/issues',{'work_id':s.work,'category':'personal_unavailability','description':'Unavailable for the first thirty minutes','can_continue':True},subjects[1])['blocker'];assert not issue['blocking']
        s.call('/recovery/issues/'+issue['id']+'/confirm',{'expected_revision':issue['revision'],'reason':'Human checked operational schedule conflict'})
        hub=s.call('/recovery/workspaces',{'issue_ids':[issue['id']],'expected_plan_id':s.plan})
        for node in hub['nodes']:
            patch={'purpose':'Adjusted operational preparation'} if node['key'].startswith('stage:') else {'schedule':{**node['original']['schedule'],'start_minute':570,'end_minute':690}} if node['key'].startswith('work:') else {}
            hub=s.call('/recovery/workspaces/'+hub['id']+'/local-review',{'expected_revision':hub['revision'],'node_key':node['key'],'patch':patch,'status':'confirmed_local_change' if patch else 'reviewed_no_change','note':'Synthetic human review of exact local values'})
        assert s.flow.get('').json()['data']['active_plan_id']==s.plan
        hub=s.call('/recovery/workspaces/'+hub['id']+'/communication',{'expected_revision':hub['revision'],'mode':'meeting','invited_account_ids':[ids[1]],'schedule':{'start_day':1,'end_day':1,'start_minute':750,'end_minute':780,'timezone':'Asia/Kolkata'},'agenda':['Review operational change','Review exact participant terms']})
        mid=hub['communication']['meeting_ids'][0];meetings=client.get('/v1/events/'+s.id+'/coordination',headers=headers()).json()['data']['items'];meeting=next(m for m in meetings if m['id']==mid)
        meeting=s.call('/coordination/'+mid+'/actions',{'expected_revision':meeting['revision'],'action':'confirm'})['record'];s.call('/coordination/'+mid+'/actions',{'expected_revision':meeting['revision'],'action':'rsvp','response':'going'},subjects[1])
        assert client.get('/v1/notifications',headers=headers(subjects[1])).json()['data']['items']
        result=s.call('/recovery/workspaces/'+hub['id']+'/submit',{'expected_revision':hub['revision'],'title':'Synthetic selective recovery','rationale':'Review local changes before overall approval'});p=result['alternative']
        reviewed=s.call('/recovery/alternatives/'+p['id']+'/review',{'expected_revision':p['revision'],'proposal_digest':p['proposal_digest'],'decision':'approve','rationale':'Reviewed exact affected scope'})
        cmd={'expected_revision':reviewed['revision'],'proposal_digest':p['proposal_digest']};assert not s.call('/recovery/alternatives/'+p['id']+'/activate',cmd)['activated']
        changed=client.get('/v1/events/'+s.id+'/recovery/offers/me',headers=headers(subjects[1])).json()['data']['items'][0]
        s.call('/recovery/alternatives/'+p['id']+'/assignments/'+offer['id']+'/consent',{'terms_key':changed['terms_key'],'decision':'accept'},subjects[1]);active=s.call('/recovery/alternatives/'+p['id']+'/activate',cmd);assert active['activated']
        output['checks'].extend(['Real signup/signin, accepted commitment and private personal issue','Confirmed blocker, local stage/work reviews, exact workspace reload','No authoritative change before overall approval and consent','Linked meeting confirmed, participant RSVP and targeted inbox','Deferred activation before consent; atomic activation after acceptance'])
        report=s.call('/reports/draft',{'work_id':s.work,'body':'Synthetic completion report for integration checks only, no actual activity','claim':'completion','progress_percent':100},subjects[1])['report'];report=s.call('/reports/'+report['id']+'/submit',{'report_revision':report['revision']},subjects[1])['report']
        report=s.call('/reports/'+report['id']+'/review',{'report_revision':report['revision'],'decision':'accept','note':'Synthetic state-transition verification, not real work','verified_percent':100,'evidence_versions':{}})['report'];s.call('/execution/work/'+s.work+'/complete',{'reason':'Synthetic human completion transition'})
        alt=next(x for x in client.get('/v1/events/'+s.id+'/recovery/alternatives',headers=headers()).json()['data']['items'] if x['id']==p['id'])
        outcome=s.call('/recovery/alternatives/'+p['id']+'/outcome',{'expected_revision':alt['revision'],'outcome':'successful','criteria':'Synthetic verification of separately reviewed completion, not a real-world lesson','report_ids':[report['id']]});assert not outcome['memory_eligible']
        s.call('/memory/data-class',{'data_class':'real','reason':'Attempted synthetic promotion must fail'},expected=422)
        denied=client.post('/v1/events/'+s.id+'/memory/extractions',json={'source_refs':[outcome['source_ref']],'extractor':'open_weight','purpose':'blocker_recovery'},headers=headers(key=secrets.token_hex(8)));assert denied.status_code==503
        output['checks'].append('Independent outcome source persisted; synthetic promotion denied; unconfigured Modal fails closed')
        with factory() as db:output['migration']=db.execute(text('select version_num from alembic_version')).scalar()
        output['status']='passed'
    finally:
        (ROOT/'.tmp/prompt7-http-results.json').write_text(json.dumps(output,indent=2));print(json.dumps(output,indent=2));client.close();server.should_exit=True;thread.join(10);engine.dispose()
if __name__=='__main__':main()
