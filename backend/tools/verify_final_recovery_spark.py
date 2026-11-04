"""One authorized live Spark recovery request over local HTTP. No retries."""
from verify_prompt56_http import *
from app.ai.models import AIRun,AIProposal
from app.events.models import Event
from app.planning.models import PlanVersion

def main():
 guard=ROOT/'.tmp/final-recovery-spark-attempt.json';out=ROOT/'.tmp/final-recovery-spark-result.json'
 settings=Settings(modal_memory_enabled=False);engine,factory=database(settings.database_url.get_secret_value())
 class One(MetaProvider):
  def send(self,path,**kwargs):
   with guard.open('x') as f:json.dump({'path':path,'at':time.time(),'model':self.model_profile},f)
   value=super().send(path,**kwargs)
   return value
 if guard.exists():raise SystemExit('One-request authorization already consumed')
 adapter=One(settings.meta_api_key.get_secret_value(),settings.meta_model_id)
 assert adapter.model_profile=='muse-spark-1.3'
 app=create_app(settings,factory,planning_adapter=adapter);sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];server=uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False));thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
 while not server.started:time.sleep(.1)
 client=httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=90)
 with factory() as db:
  e=db.get(Event,'01b19638-0f30-47ff-af9f-cfc51bde2354');owner=db.get(User,e.creator_id).external_auth_subject
 def headers(subject='owner-subject',key='final-recovery',version='1'):return {'Authorization':'Bearer '+issue_token(settings,owner),'Idempotency-Key':key,'If-Match':str(version)}
 try:
  FORM.update(title='Synthetic final Spark recovery verification',purpose='Synthetic execution verification only',executionIntent='Synthetic planning scenario; no real gathering or historical outcome.')
  s=Scenario(client,headers,factory).build(capacity=2,resource=True)
  s.call('/memory/data-class',{'data_class':'synthetic','reason':'Isolated live AI verification only'})
  issue=s.call('/issues',{'work_id':s.work,'description':'The planned work cannot start until the organizer checks missing supplies. Available quantity remains unverified.','category':'resource_missing','severity':'delayed','can_continue':False})['blocker']
  s.call('/recovery/issues/'+issue['id']+'/confirm',{'expected_revision':issue['revision'],'reason':'Organizer confirmed supplies require verification before work begins'})
  with factory() as db:before=db.get(Event,s.id).active_plan_id
  result=s.call('/recovery/ai-runs',{'issue_id':issue['id'],'message':'Suggest one small conditional recovery using actual IDs, or return no alternatives and questions if missing quantities prevent a defensible change. Never assert stock or staff availability. Do not activate anything.'})
  rid=result['run_id']
  for _ in range(80):
   with factory() as db:
    run=db.get(AIRun,rid)
    if run.status not in ('queued','running'):break
   time.sleep(1)
  with factory() as db:
   run=db.get(AIRun,rid);p=db.get(AIProposal,run.proposal_id) if run.proposal_id else None
   data={'event_id':s.id,'run_id':rid,'status':run.status,'failure_code':run.failure_code,'model':adapter.model_profile,'proposal':{'id':p.id,'status':p.status,'payload':p.payload,'provenance':p.provenance} if p else None,'active_plan_unchanged':db.get(Event,s.id).active_plan_id==before,'memory_count':len(run.context_manifest['context_manifest']['retrieved_memories']),'one_request_attempted':guard.exists()}
  # Manual path remains usable after the model run, without another inference.
  hub=s.call('/recovery/workspaces',{'issue_ids':[issue['id']],'expected_plan_id':before});data['manual_workspace_id']=hub['id']
  out.write_text(json.dumps(data,indent=2));print(json.dumps(data,indent=2))
 finally:client.close();server.should_exit=True;thread.join(10);engine.dispose()
if __name__=='__main__':main()

