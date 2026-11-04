"""Resume deterministic checks on the saved synthetic HTTP event. No inference calls."""
from verify_prompt56_http import *
from app.events.models import Event
from app.participation.models import Assignment,AssignmentTerms

def followup():
    path=ROOT/'.tmp/prompt56-http-results.json';output=json.loads(path.read_text());settings=Settings(meta_ai_enabled=False);engine,factory=database(settings.database_url.get_secret_value())
    with factory() as db:
        event=db.get(Event,output['event_id']);owner=db.get(User,event.creator_id).external_auth_subject
        assignment=db.scalar(select(Assignment).where(Assignment.event_id==event.id,Assignment.status=='assignment_accepted'));person=db.get(User,assignment.account_id).external_auth_subject;pid=assignment.account_id;assignment_id=assignment.id
        terms=db.get(AssignmentTerms,assignment.current_terms_id);wid=terms.content['work_ids'][0]
        output['migration']=db.execute(text('select version_num from alembic_version')).scalar()
    app=create_app(settings,factory);sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];server=uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False));thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
    for _ in range(100):
        if server.started:break
        time.sleep(.1)
    client=httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=30)
    def headers(subject='owner-subject',key='followup',version='1'):return {'Authorization':'Bearer '+issue_token(settings,owner if subject=='owner-subject' else subject),'Idempotency-Key':key,'If-Match':str(version)}
    s=Scenario(client,headers,factory);s.flow.id=output['event_id'];s.subject=person;s.person_id=pid;s.work=wid
    try:
        issue=s.call('/issues',{'work_id':wid,'description':'Synthetic integration issue, not a real incident','severity':'delayed'},person)['blocker'];s.call('/issues/'+issue['id']+'/review',{'expected_revision':issue['revision'],'state':'acknowledged','note':'Synthetic verification acknowledged','condition_cleared':False})
        meeting=s.call('/coordination',{'kind':'meeting','title':'Synthetic followup review','body':'Agenda: integration checks','work_ids':[wid],'schedule':{'start_day':1,'end_day':1,'start_minute':720,'end_minute':750,'timezone':'Asia/Kolkata'}})['record']
        meeting=s.call('/coordination/'+meeting['id']+'/actions',{'expected_revision':meeting['revision'],'action':'revise_invitees','invited_account_ids':[pid]})['record']
        meeting=s.call('/coordination/'+meeting['id']+'/actions',{'expected_revision':meeting['revision'],'action':'confirm'})['record'];s.call('/coordination/'+meeting['id']+'/actions',{'expected_revision':meeting['revision'],'action':'rsvp','response':'going'},person)
        action=s.call('/coordination',{'kind':'action','title':'Synthetic next check','parent_id':meeting['id'],'status':'open'})['record'];s.call('/coordination/'+action['id']+'/actions',{'expected_revision':action['revision'],'action':'approve_action','note':'Authorized synthetic followup'})
        s.call('/coordination',{'kind':'note','title':'Synthetic review note','body':'Only integration behavior checked','audience':'participants','status':'published'},person)
        attendance=s.call('/attendance',{'assignment_id':assignment_id,'action':'claim','note':'Synthetic check-in'},person);pending=state(s)['attendance'][0];s.call('/attendance',{'assignment_id':assignment_id,'action':'verify','note':'Synthetic HTTP verification only','expected_revision':pending['revision']})
        restored=state(s,person);assert any(x['id']==issue['id'] for x in restored['blockers'])
        output['checks'].append('Followup HTTP: invite revision, meeting confirmation, RSVP, action approval, note, attendance, issue acknowledgement and reload')
        output['deterministic_journey']='passed';path.write_text(json.dumps(output,indent=2));print(json.dumps(output,indent=2))
    finally:client.close();server.should_exit=True;thread.join(10);engine.dispose()
if __name__=='__main__':followup()
