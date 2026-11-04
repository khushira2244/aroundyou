"""Last approved call, after correcting bounded work latency. Never exceeds six."""
import json,sys
from fastapi.testclient import TestClient
from app.settings import Settings
from app.main import create_app
from app.shared.database import database
from app.events.models import Event
from app.access.models import User
from app.access.authentication import issue_token
from app.shared.types import uid
from tools.verify_prompt3_live import BoundedPlanningProvider,BUDGET,REPORT
import app.models
if '--approved-six-planning-tests' not in sys.argv:raise SystemExit('Approved flag required')
report=json.loads(REPORT.read_text());settings=Settings();engine,factory=database(settings.database_url.get_secret_value());event_id=report['event_id']
with factory() as db:user=db.get(User,db.get(Event,event_id).creator_id);token=issue_token(settings,user.external_auth_subject)
adapter=BoundedPlanningProvider(settings.meta_api_key.get_secret_value(),settings.meta_model_id)
with TestClient(create_app(settings,factory,planning_adapter=adapter)) as client:
 def get(suffix):return client.get('/v1/events/'+event_id+suffix,headers={'Authorization':'Bearer '+token}).json()['data']
 def post(suffix,body):
  r=client.post('/v1/events/'+event_id+suffix,json=body,headers={'Authorization':'Bearer '+token,'Idempotency-Key':uid(),'If-Match':str(get('')['version'])})
  if r.status_code>=400:raise RuntimeError('API '+str(r.status_code)+' '+r.json().get('error',{}).get('code','unknown'))
  return r.json()['data']
 try:
  run=post('/planning/work-proposals',{'message':'Generate exactly one concise work unit per confirmed stage, and a group for each. Copy exact parent relative_start into both schedule day fields. Preserve required_stage_windows. Keep descriptions brief; include skills and evidence expectations. Resource demand only.'})
  result=client.get('/v1/ai-runs/'+run['run_id'],headers={'Authorization':'Bearer '+token}).json()['data'];entry={'action':'work-proposals','run_id':run['run_id'],'status':result['status'],'error':result.get('error')};report['checks'].append(entry)
  if result['status']!='succeeded':raise RuntimeError('Final live work check: '+str(result.get('error')))
  p=result['proposal'];entry.update({'proposal_id':p['id'],'changes':p['changes'],'metadata':p['provenance'].get('provider_metadata')})
  post('/planning/proposals/'+p['id']+'/apply',{'reviewed_digest':p['digest']});post('/planning/work-confirmations',{'expected_draft_version':get('/planning')['draft_version']})
  a=get('/planning');b=get('/planning');assert a['planning']==b['planning'];report['work_count']=len(a['planning']['work']);report['saved_state_restored_without_inference']=True;report.pop('failure',None)
 except Exception as exc:report['failure']=str(exc)
 report['remaining_live_verification']='Actor recommendations and conversational inference were not exercised live: six-call test cap reached. They are tested offline and remain available through explicit UI actions.'
 report['calls']=json.loads(BUDGET.read_text())['calls'];REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
engine.dispose()
