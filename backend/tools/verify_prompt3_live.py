"""Six-call cap approved in Prompt 3. Explicit test only, never run on startup."""
import json,sys
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from app.settings import Settings
from app.main import create_app
from app.shared.database import database
from app.shared.types import uid
from app.access.models import User
from app.access.authentication import issue_token
from app.events.models import Event
from app.ai.models import AIProposal
from app.ai.meta_provider import MetaProvider
from app.planning.models import PlanVersion
import app.models

ROOT=Path(__file__).resolve().parents[1]
BUDGET=ROOT/'.tmp'/'prompt3-live-budget.json'
REPORT=ROOT/'.tmp'/'prompt3-live-results.json'
class BoundedPlanningProvider(MetaProvider):
    def send(self,path,**kwargs):
        if path!='/chat/completions':raise RuntimeError('Only approved Spark planning tests allowed')
        count=json.loads(BUDGET.read_text())['calls'] if BUDGET.exists() else 0
        if count>=6:raise RuntimeError('Prompt 3 live-call budget exhausted')
        BUDGET.write_text(json.dumps({'calls':count+1}));return super().send(path,**kwargs)

def main():
    if '--approved-six-planning-tests' not in sys.argv:raise SystemExit('Explicit approved bounded-test flag required')
    settings=Settings();engine,factory=database(settings.database_url.get_secret_value())
    previous=json.loads((ROOT/'.tmp'/'prompt2-governance-results.json').read_text())
    event_id=next(x['event_id'] for x in previous['events'] if x['category']=='Health')
    with factory() as db:
        event=db.get(Event,event_id);user=db.get(User,event.creator_id)
        if not event.interpretation:raise SystemExit('Previously confirmed context required')
        token=issue_token(settings,user.external_auth_subject)
    adapter=BoundedPlanningProvider(settings.meta_api_key.get_secret_value(),settings.meta_model_id)
    report={'event_id':event_id,'context':'Previously confirmed Prompt 2 health-awareness event with real reviewed governance','browser_verified':False,'checks':[]}
    with TestClient(create_app(settings,factory,planning_adapter=adapter)) as client:
        def call(path,body={},method='POST',absolute=False):
            h={'Authorization':'Bearer '+token,'Idempotency-Key':uid()}
            h['If-Match']=str(client.get('/v1/events/'+event_id,headers=h).json()['data']['version'])
            response=client.request(method,'/v1'+(path if absolute else '/events/'+event_id+path),json=body if method!='GET' else None,headers=h)
            if response.status_code>=400:raise RuntimeError('API '+str(response.status_code)+' '+response.json().get('error',{}).get('code','unknown'))
            return response.json()['data']
        def plan():return call('/planning',method='GET')
        def generate(path,message=''):
            run=call('/planning/'+path,{'message':message});value=call('/ai-runs/'+run['run_id'],method='GET',absolute=True)
            report['checks'].append({'action':path,'run_id':run['run_id'],'status':value['status'],'error':value.get('error')})
            REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
            if value['status']!='succeeded':raise RuntimeError('Live run failed: '+str(value.get('error')))
            p=value['proposal'];report['checks'][-1].update({'proposal_id':p['id'],'message':p['message'],'changes':p.get('changes'),'metadata':p['provenance'].get('provider_metadata')});return p
        def apply(p):call('/planning/proposals/'+p['id']+'/apply',{'reviewed_digest':p['digest']})
        def confirm(level):call('/planning/'+level+'-confirmations',{'expected_draft_version':plan()['draft_version']})
        try:
            current=call('/creation',method='GET')
            if current['runtime']['lifecycle']=='draft':call('/confirm-creation',{'expected_draft_version':current['runtime']['revision']})
            call('/planning/draft')
            p=generate('stage-proposals','Generate 3-4 concise stages for this health-awareness meeting. Preserve non-clinical scope and reviewed governance.');apply(p);confirm('stage')
            initial=plan();stages=list(initial['planning']['stages'].values());target=stages[0]
            edit=call('/planning/stage-edits',{'stage_id':target['id'],'start_day':target['relative_start']+1,'duration_days':target['relative_end']-target['relative_start']+1})
            report['checks'].append({'manual_edit_no_inference':True,'impact':edit['impact'],'active_schedule_unchanged':plan()['planning']['stages']==initial['planning']['stages']})
            p=generate('stage-proposals/revisions','Honor pending_human_stage_edit: delay its changed stage by one day. Keep all current stage IDs and durations; adjust affected downstream stages deterministically to respect finish-to-start dependencies. No work rewriting.');apply(p);confirm('stage')
            p=generate('work-proposals','Generate one concise work unit and group for each confirmed stage, with skills, evidence and demand-only resources.');apply(p);confirm('work')
            p=generate('actor-proposals','Recommend contributor role requirements covering all confirmed work. Copy exact source schedules. No assignments or claims of available people.');apply(p);confirm('actor')
            before=plan();active=before['active_plan_id']
            for question in ['Why is the first stage needed for this specific health-awareness meeting? Could stages safely run in parallel? Answer only; do not propose changes.','What would moving the first stage by two days affect? Use current dependencies and known work timing. Explain uncertainty; answer only, proposed_stages must be null.']:
                p=generate('conversations',question)
                if not p.get('advisory_only'):raise RuntimeError('Question unexpectedly produced a change proposal')
            restored=plan();assert restored['active_plan_id']==active and restored['planning']==before['planning']
            report['saved_state_restored_without_inference']=True
            report['stage_count']=len(restored['planning']['stages']);report['work_count']=len(restored['planning']['work']);report['role_count']=len(restored['planning']['roles'])
            with factory() as db:report['immutable_plan_versions']=db.scalar(select(func.count()).select_from(PlanVersion).where(PlanVersion.event_id==event_id))
        except Exception as exc:report['failure']=str(exc)
        report['calls']=json.loads(BUDGET.read_text())['calls'] if BUDGET.exists() else 0
        REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
    engine.dispose()
if __name__=='__main__':main()
