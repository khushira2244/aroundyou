"""Three explicit stage-scoped live checks. Never imported by application startup."""
import json,sys
from pathlib import Path
from fastapi.testclient import TestClient
from app.settings import Settings
from app.main import create_app
from app.shared.database import database
from app.shared.types import uid
from app.access.models import User
from app.access.authentication import issue_token
from app.events.models import Event
from app.ai.meta_provider import MetaProvider
import app.models
ROOT=Path(__file__).resolve().parents[1]
BUDGET=ROOT/'.tmp'/'prompt3-stage-scope-budget.json'
REPORT=ROOT/'.tmp'/'prompt3-stage-scope-results.json'
class ApprovedProvider(MetaProvider):
    def send(self,path,**kwargs):
        if path!='/chat/completions':raise RuntimeError('Only Spark calls authorized')
        count=json.loads(BUDGET.read_text())['calls'] if BUDGET.exists() else 0
        if count>=3:raise RuntimeError('Three-call cap exhausted')
        BUDGET.write_text(json.dumps({'calls':count+1}));return super().send(path,**kwargs)

def main():
    if '--approved-three-stage-calls' not in sys.argv:raise SystemExit('Fresh explicit approval flag required')
    if REPORT.exists():raise SystemExit('Prior result exists; no automatic repeat')
    settings=Settings();engine,factory=database(settings.database_url.get_secret_value())
    event_id='3db4b03a-d8ef-4d15-84b3-a82928bcc6e9'
    with factory() as db:
        event=db.get(Event,event_id);user=db.get(User,event.creator_id)
        if not user.external_auth_subject.startswith('prompt2-verification-'):raise RuntimeError('Private verification identity required')
        token=issue_token(settings,user.external_auth_subject)
    provider=ApprovedProvider(settings.meta_api_key.get_secret_value(),settings.meta_model_id)
    report={'event_id':event_id,'model':settings.meta_model_id,'checks':[],'browser_verified':False}
    try:
        with TestClient(create_app(settings,factory,planning_adapter=provider)) as client:
            def read(path):
                r=client.get('/v1'+path,headers={'Authorization':'Bearer '+token});r.raise_for_status();return r.json()['data']
            def post(path,body):
                h={'Authorization':'Bearer '+token,'Idempotency-Key':uid(),'If-Match':str(read('/events/'+event_id)['version'])}
                r=client.post('/v1/events/'+event_id+path,json=body,headers=h)
                if r.status_code>=400:raise RuntimeError('API '+str(r.status_code)+' '+r.json().get('error',{}).get('code','unknown'))
                return r.json()['data']
            def state():return read('/events/'+event_id+'/planning')
            before=state();stage=next(iter(before['planning']['stages'].values()));sid=stage['id'];report['stage_id']=sid;report['stage_title']=stage['title']
            if not before['planning']['stage_confirmed']:raise RuntimeError('Confirmed stages required')
            def generate(path,message):
                run=post('/planning/'+path,{'stage_id':sid,'message':message});result=read('/ai-runs/'+run['run_id'])
                check={'action':path,'run_id':run['run_id'],'status':result['status'],'error':result.get('error')};report['checks'].append(check)
                if result['status']!='succeeded':raise RuntimeError('Live '+path+' failed: '+str(result.get('error')))
                p=result['proposal'];check.update({'proposal_id':p['id'],'stage_id':p.get('stage_id'),'message':p['message'],'provider_metadata':p['provenance'].get('provider_metadata')});return p
            def apply_confirm(p,level):
                post('/planning/proposals/'+p['id']+'/apply',{'reviewed_digest':p['digest']})
                post('/planning/'+level+'-confirmations',{'stage_id':sid,'expected_draft_version':state()['draft_version']})
            p=generate('work-proposals','Generate 1-3 short work units for this selected stage only. Use its approved relative day window and event timezone. Keep the response concise; resource quantities are demand only.')
            apply_confirm(p,'work');work=state();assert sid in work['planning']['work_confirmed_stage_ids']
            assert all(w['stage_id']==sid for w in p['preview_plan']['work'] if w['id'] not in before['planning']['work'])
            p=generate('actor-proposals','Recommend concise actor demand only for this selected stage confirmed work. Cover the exact supplied work IDs. No recruited people or availability claims.')
            apply_confirm(p,'actor');saved=state();assert sid in saved['planning']['actor_confirmed_stage_ids']
            p=generate('conversations','Why is this selected stage work necessary, and can its work units run in parallel? Use actual work and dependency facts; distinguish unknown resources and staffing.')
            assert p['advisory_only'];assert state()['planning']==saved['planning']
            for _ in range(3):assert state()['planning']==saved['planning']
            for key in ('work','roles'):
                assert {k:v for k,v in saved['planning'][key].items() if (v['stage_id']!=sid if key=='work' else sid not in v['stage_ids'])}=={k:v for k,v in before['planning'][key].items() if (v['stage_id']!=sid if key=='work' else sid not in v['stage_ids'])}
            report.update({'saved_reads_without_inference':True,'other_stages_unchanged':True,'work_count':len([w for w in saved['planning']['work'].values() if w['stage_id']==sid]),'role_count':len([r for r in saved['planning']['roles'].values() if sid in r['stage_ids']])})
    except Exception as exc:report['failure']=str(exc)
    finally:
        report['calls']=json.loads(BUDGET.read_text())['calls'] if BUDGET.exists() else 0
        REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2));engine.dispose()
if __name__=='__main__':main()
