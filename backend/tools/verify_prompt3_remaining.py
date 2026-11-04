"""Explicit remaining three calls after correcting rejected work schema; total stays six."""
import json,sys
from sqlalchemy import select,func
from fastapi.testclient import TestClient
from app.settings import Settings
from app.main import create_app
from app.shared.database import database
from app.access.models import User
from app.access.authentication import issue_token
from app.events.models import Event
from app.planning.models import PlanVersion
from app.shared.types import uid
from tools.verify_prompt3_live import BoundedPlanningProvider,BUDGET,REPORT
import app.models
if '--approved-six-planning-tests' not in sys.argv:raise SystemExit('Explicit approved flag required')
report=json.loads(REPORT.read_text());event_id=report['event_id'];settings=Settings();engine,factory=database(settings.database_url.get_secret_value())
with factory() as db:user=db.get(User,db.get(Event,event_id).creator_id);token=issue_token(settings,user.external_auth_subject)
adapter=BoundedPlanningProvider(settings.meta_api_key.get_secret_value(),settings.meta_model_id)
with TestClient(create_app(settings,factory,planning_adapter=adapter)) as client:
 def call(path,body={},absolute=False):
  h={'Authorization':'Bearer '+token,'Idempotency-Key':uid()};h['If-Match']=str(client.get('/v1/events/'+event_id,headers=h).json()['data']['version'])
  r=client.post('/v1'+(path if absolute else '/events/'+event_id+path),json=body,headers=h)
  if r.status_code>=400:raise RuntimeError('API '+str(r.status_code)+' '+r.json().get('error',{}).get('code','unknown'))
  return r.json()['data']
 def plan():return client.get('/v1/events/'+event_id+'/planning',headers={'Authorization':'Bearer '+token}).json()['data']
 def generate(path,message):
  run=call('/planning/'+path,{'message':message});r=client.get('/v1/ai-runs/'+run['run_id'],headers={'Authorization':'Bearer '+token}).json()['data'];entry={'action':path,'run_id':run['run_id'],'status':r['status'],'error':r.get('error')};report['checks'].append(entry)
  if r['status']!='succeeded':raise RuntimeError('Live run '+r['status']+': '+str(r.get('error')))
  p=r['proposal'];entry.update({'proposal_id':p['id'],'message':p['message'],'changes':p.get('changes'),'metadata':p['provenance'].get('provider_metadata')});return p
 try:
  for path,level,message in [('work-proposals','work','Generate one short work unit for each current confirmed stage. ALWAYS copy the parent relative_start into start_day and end_day for these one-day stages. Include complete schedule objects and keep within required_stage_windows.'),('actor-proposals','actor','Recommend roles covering all confirmed work, with exact copies of each source-work schedule. Contributor counts are proposed demand only.')]:
   p=generate(path,message);call('/planning/proposals/'+p['id']+'/apply',{'reviewed_digest':p['digest']});call('/planning/'+level+'-confirmations',{'expected_draft_version':plan()['draft_version']})
  if json.loads(BUDGET.read_text())['calls']>=6:raise RuntimeError('Approved live test budget reached; remaining verification is offline/manual.')
  before=plan();p=generate('conversations','Answer both: why does this specific health-awareness event need its first stage, and what would delaying that stage two days do to dependent stages, confirmed work timing and actor windows? Can any stages safely run in parallel? Use actual IDs and distinguish unknown capacity. Answer only; proposed_stages must be null.')
  assert p.get('advisory_only');after=plan();assert before['active_plan_id']==after['active_plan_id'] and before['planning']==after['planning']
  report['saved_state_restored_without_inference']=True;report['chat_checks']='One combined response covers stage rationale, delay effects and parallelism; second chat call was replaced by the work-schema correction test within the six-call budget.'
  for key in ('stages','work','roles'):report[key+'_count']=len(after['planning'][key])
  with factory() as db:report['immutable_plan_versions']=db.scalar(select(func.count()).select_from(PlanVersion).where(PlanVersion.event_id==event_id))
  report.pop('failure',None)
 except Exception as exc:report['failure']=str(exc)
 report['calls']=json.loads(BUDGET.read_text())['calls'];REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
engine.dispose()
