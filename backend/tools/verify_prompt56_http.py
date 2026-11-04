"""Explicit bounded live verification; creates only a new synthetic event, never resets data."""
import json,os,secrets,socket,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ['TEMP']=str(ROOT/'.tmp');os.environ['TMP']=str(ROOT/'.tmp')
import httpx,uvicorn
from sqlalchemy import select,text
from app.settings import Settings
from app.main import create_app
from app.ai.meta_provider import MetaProvider
from app.access.models import User
from app.access.accounts import Credential
from app.access.authentication import issue_token
from app.shared.database import database
from tests.test_group3 import Scenario
from tests.test_group2 import FORM
from tests.test_group4 import report,state,review
from tests.test_prompt56_media import attach

def main():
    budget=ROOT/'.tmp/prompt56-live-budget.json'
    class Bounded(MetaProvider):
        def send(self,path,**kwargs):
            calls=json.loads(budget.read_text()) if budget.exists() else []
            if len(calls)>=4:raise RuntimeError('Four-request budget exhausted; no retry')
            calls.append({'path':path,'at':time.time()});budget.write_text(json.dumps(calls))
            return super().send(path,**kwargs)
    settings=Settings();engine,factory=database(settings.database_url.get_secret_value())
    adapter=Bounded(settings.meta_api_key.get_secret_value(),settings.meta_model_id)
    app=create_app(settings,factory,planning_adapter=adapter)
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False));thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
    for _ in range(100):
        if server.started:break
        time.sleep(.1)
    client=httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=150,headers={'Origin':'http://127.0.0.1:5173'})
    output={'transport':'actual HTTP to configured development PostgreSQL','browser_verified':False,'checks':[]}
    try:
        subjects=[];ids=[]
        for n in range(3):
            email=secrets.token_hex(8)+'@example.test';password=secrets.token_urlsafe(24)
            response=client.post('/v1/auth/signup',json={'name':'Synthetic Prompt56 verification '+str(n),'email':email,'password':password,'kind':'personal'});assert response.is_success,response.text
            assert client.post('/v1/auth/logout').is_success
            assert client.post('/v1/auth/signin',json={'email':email,'password':password}).is_success
            with factory() as db:
                credential=db.scalar(select(Credential).where(Credential.email==email));user=db.get(User,credential.user_id);subjects.append(user.external_auth_subject);ids.append(user.id)
        client.post('/v1/auth/logout')
        def headers(subject='owner-subject',key='verification',version='1'):
            return {'Authorization':'Bearer '+issue_token(settings,subjects[0] if subject=='owner-subject' else subject),'Idempotency-Key':key,'If-Match':str(version)}
        FORM.update(title='Synthetic Prompt56 HTTP verification',purpose='Synthetic verification only; no real gathering',executionIntent='Synthetic integration verification. No real activity or outcome claimed.')
        s=Scenario(client,headers,factory).build(resource=True);output['event_id']=s.id;output['checks'].append('Real signup/signin and published event with confirmed plan')
        aid=s.apply(subjects[1]);run=s.call('/participation-assessments',{'application_id':aid,'message':'Explain suitability and uncertainty using only the supplied applicant and confirmed work.'},expected=202)
        for _ in range(100):
            value=client.get('/v1/ai-runs/'+run['run_id'],headers=headers()).json()['data']
            if value['status'] not in ('queued','running'):break
            time.sleep(.3)
        output['suitability']={'status':value['status'],'run_id':run['run_id'],'error':value.get('error')}
        assert client.get('/v1/ai-runs/'+run['run_id'],headers=headers()).is_success
        s.approve(aid);offer=s.offer(aid);s.call('/assignments/'+offer['id']+'/accept',{'terms_key':offer['terms_key']},subjects[1]);s.subject=subjects[1];s.person_id=ids[1];s.assignment=offer
        declined=s.apply(subjects[2]);s.approve(declined);other=s.offer(declined);s.call('/assignments/'+other['id']+'/decline',{'terms_key':other['terms_key']},subjects[2])
        assert client.get('/v1/me/events',headers=headers(s.subject)).json()['data']['items'][0]['accepted_assignments']
        output['checks'].append('Application review, exact acceptance and decline, My Events restored')
        r=report(s);raw=(ROOT/'.tmp/prompt2-spoken-test.wav').read_bytes();a,rev=attach(s,r,raw,'audio','audio/wav','verification.wav')
        path='/v1/events/'+s.id+'/media/'+a['id'];voice=client.post(path+'/transcription-runs',json={},headers=headers(s.subject,key='voice-one')).json()['data'];output['voice']={'status':voice['status'],'error':voice.get('error')}
        if voice['status']=='succeeded':
            saved=state(s,s.subject)['evidence'][0];corrected=client.post(path+'/transcript-review',json={'expected_revision':saved['revision'],'text':'Synthetic verification voice note reviewed by participant; no completed activity claimed.'},headers=headers(s.subject,key='voice-review'));assert corrected.is_success,corrected.text
        image=Path('C:/Users/Khushboo/Downloads/canary_hill profile.jpg').read_bytes();a,rev=attach(s,{**r,'revision':rev},image,'image','image/jpeg','genuine-location-reference.jpg')
        r=s.call('/reports/'+r['id']+'/submit',{'report_revision':rev},s.subject)['report']
        visual=client.post('/v1/events/'+s.id+'/media/'+a['id']+'/segmentation-runs',json={'concept':'trees'},headers=headers(key='image-one')).json()['data'];output['visual']={'status':visual['status'],'error':visual.get('error'),'run_id':visual['run_id']}
        assert state(s)['work'][0]['verified_percent']==0
        versions={}
        for asset in state(s)['evidence']:
            inspected=s.call('/evidence/'+asset['id']+'/inspection',{'expected_revision':asset['revision'],'decision':'accept_for_review','note':'Synthetic HTTP verification: original bytes inspected, no genuine outcome claimed'})['asset'];versions[asset['id']]=inspected['revision']
        review(s,r,20,versions=versions);assert state(s)['work'][0]['verified_percent']==20
        assert client.get('/v1/events/'+s.id+'/evidence/'+a['id']+'/content',headers=headers(subjects[2])).status_code==404
        output['checks'].append('Private original evidence, explicit human review, unauthorized download denied')
        meeting=s.call('/coordination',{'kind':'meeting','title':'Synthetic verification coordination','body':'Agenda: verify integration only','invited_account_ids':[ids[1]],'work_ids':[s.work],'schedule':{'start_day':1,'end_day':1,'start_minute':720,'end_minute':750,'timezone':'Asia/Kolkata'}})['record']
        meeting=s.call('/coordination/'+meeting['id']+'/actions',{'expected_revision':meeting['revision'],'action':'confirm'})['record'];s.call('/coordination/'+meeting['id']+'/actions',{'expected_revision':meeting['revision'],'action':'rsvp','response':'going'},s.subject)
        issue=s.call('/issues',{'work_id':s.work,'description':'Synthetic verification issue; not an actual incident','severity':'delayed'},s.subject)['blocker'];s.call('/issues/'+issue['id']+'/review',{'expected_revision':issue['revision'],'state':'acknowledged','note':'Synthetic issue acknowledged','condition_cleared':False})
        output['checks'].append('Persisted meeting, invitation scope, RSVP and issue acknowledgement')
        with factory() as db:output['migration']=db.execute(text('select version_num from alembic_version')).scalar()
    finally:
        output['paid_requests']=len(json.loads(budget.read_text())) if budget.exists() else 0
        (ROOT/'.tmp/prompt56-http-results.json').write_text(json.dumps(output,indent=2));print(json.dumps(output,indent=2));client.close();server.should_exit=True;thread.join(10);engine.dispose()
if __name__=='__main__':main()
