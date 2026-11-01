from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import uuid,time
import pytest
from sqlalchemy import select,text
from sqlalchemy.exc import DBAPIError
from tests.test_group3 import scenario
from app.execution.models import *
from app.events.models import Event
from app.shared.unit_of_work import unit_of_work
from app.ai.service import work_ai_once
from app.ai.models import AIRun
from app.execution.storage import LocalPrivateStorage

@pytest.fixture
def run(scenario):
    s=scenario.build(resource=True);subject,id=s.person(1);a=s.apply(subject);s.approve(a);offer=s.offer(a);s.call('/assignments/'+offer['id']+'/accept',{'terms_key':offer['terms_key']},subject)
    s.subject=subject;s.person_id=id;s.assignment=offer;return s

def report(s,claim='progress',usage=None):
    return s.call('/reports/draft',{'work_id':s.work,'body':'  Held a reading practice session; learner feedback still pending.  ','claim':claim,'progress_percent':40 if claim=='progress' else 100,'resource_usage':usage or []},s.subject)['report']
def submitted(s,claim='progress',usage=None):
    r=report(s,claim,usage);return s.call('/reports/'+r['id']+'/submit',{'report_revision':r['revision']},s.subject)['report']
def review(s,r,percent=40,decision='accept',versions=None):
    return s.call('/reports/'+r['id']+'/review',{'report_revision':r['revision'],'decision':decision,'note':'I inspected the original report and actual session outcome','verified_percent':percent,'evidence_versions':versions or {}})['report']
def state(s,subject=None):return s.client.get('/v1/events/'+s.id+'/execution',headers=s.headers(subject or 'owner-subject')).json()['data']

def test_education_partial_multiple_revisions_and_explicit_completion(run):
    s=run;s.call('/execution/work/'+s.work+'/start',{},s.subject)
    r=submitted(s);assert state(s)['work'][0]['execution_status']=='submitted_for_review';review(s,r)
    assert state(s)['work'][0]['verified_percent']==40
    s.call('/execution/work/'+s.work+'/complete',{'reason':'Attempted too early'},expected=409)
    r=submitted(s,'completion');review(s,r,100);s.call('/execution/work/'+s.work+'/complete',{'reason':'Exact reading-session outcome checked'})
    assert state(s)['work'][0]['execution_status']=='completed'
    s.call('/reports/draft',{'work_id':s.work,'body':'Must not implicitly reopen completed work'},s.subject,expected=409)
    s.call('/execution/work/'+s.work+'/complete',{'reason':'Duplicate'},expected=409)
    s.call('/execution/work/'+s.work+'/reopen',{'reason':'New discrepancy requires another review'})
    assert state(s)['work'][0]['verified_percent']==0
    with s.factory() as db:assert len(list(db.scalars(select(ExecutionRevision).where(ExecutionRevision.event_id==s.id))))>=10

def test_no_other_participant_or_withdrawn_reporting_but_history_remains(run):
    s=run;other,oid=s.person(2);r=report(s)
    s.call('/reports/draft',{'work_id':s.work,'body':'Unauthorized'},other,expected=404)
    s.call('/assignments/'+s.assignment['id']+'/withdraw',{},s.subject)
    s.call('/reports/'+r['id']+'/submit',{'report_revision':r['revision']},s.subject,expected=404)
    response=s.client.get('/v1/events/'+s.id+'/reports/'+r['id']+'/revisions',headers=s.headers(s.subject));assert response.status_code==200 and len(response.json()['data']['items'])==1
    assert s.client.get('/v1/events/'+s.id+'/reports/'+r['id']+'/revisions',headers=s.headers(other)).status_code==404

def test_changed_material_terms_remove_future_report_authority(run):
    s=run;r=report(s);replacement=s.offer(s.assignment['application_id'],replaces_assignment_id=s.assignment['id'],conditions=['Updated terms'])
    s.call('/reports/draft',{'work_id':s.work,'report_id':r['id'],'report_revision':r['revision'],'body':'Changed'},s.subject,expected=404)
    assert state(s,s.subject)['reports'][0]['can_edit'] is False

def test_human_clarification_correction_and_original_history(run):
    s=run;r=submitted(s);assert r['original_text']=='  Held a reading practice session; learner feedback still pending.  ';r=review(s,r,None,'clarify')
    edited=s.call('/reports/draft',{'work_id':s.work,'report_id':r['id'],'report_revision':r['revision'],'body':'Corrected: only two learning activities attempted.','progress_percent':20},s.subject)['report']
    r=s.call('/reports/'+r['id']+'/submit',{'report_revision':edited['revision']},s.subject)['report'];review(s,r,20)
    history=s.client.get('/v1/events/'+s.id+'/reports/'+r['id']+'/revisions',headers=s.headers()).json()['data']['items']
    assert 'Held a reading practice' in history[0]['record']['record']['original_text'] and state(s)['work'][0]['verified_percent']==20
    with pytest.raises(DBAPIError):
        with unit_of_work(s.factory) as db:db.execute(text("UPDATE execution_revisions SET digest='bad'"))

def test_private_real_bytes_upload_inspection_hash_and_retraction(run,app):
    s=run;app.state.evidence_storage=LocalPrivateStorage(__import__('pathlib').Path(__file__).resolve().parents[1]/'.tmp'/('group4-evidence-'+uuid.uuid4().hex));r=report(s,'completion');raw=b'%PDF-1.7 original field notes'
    created=s.call('/evidence/uploads',{'report_id':r['id'],'report_revision':r['revision'],'kind':'document','name':'notes.pdf','mime':'application/pdf','size':len(raw)},s.subject);asset=created['asset']
    version=s.client.get('/v1/events/'+s.id+'/participation/me',headers=s.headers(s.subject)).json()['meta']['version']
    result=s.client.put('/v1/events/'+s.id+'/evidence/'+asset['id']+'/content',content=raw,headers=s.headers(s.subject,key='upload-once',version=str(version)));assert result.status_code==200,result.text
    a=result.json()['data']['asset'];assert a['sha256'] and a['status']=='pending_inspection'
    other,oid=s.person(2);assert s.client.get('/v1/events/'+s.id+'/evidence/'+a['id']+'/content',headers=s.headers(other)).status_code==404
    assert s.client.get('/v1/events/'+s.id+'/evidence/'+a['id']+'/content',headers=s.headers()).status_code==404
    r=s.call('/reports/'+r['id']+'/submit',{'report_revision':created['report_revision']},s.subject)['report']
    s.call('/reports/'+r['id']+'/review',{'report_revision':r['revision'],'decision':'accept','note':'Not yet inspected','verified_percent':100,'evidence_versions':{a['id']:a['revision']}},expected=409)
    assert s.client.get('/v1/events/'+s.id+'/evidence/'+a['id']+'/content',headers=s.headers()).content==raw
    a=s.call('/evidence/'+a['id']+'/inspection',{'expected_revision':a['revision'],'decision':'accept_for_review','note':'Reviewed original source type and relevance'})['asset']
    review(s,r,100,versions={a['id']:a['revision']});s.call('/execution/work/'+s.work+'/complete',{'reason':'Original report and field notes confirmed'})
    s.call('/evidence/'+a['id']+'/inspection',{'expected_revision':a['revision'],'decision':'retract','note':'Original note identified as incorrect'},s.subject)
    assert state(s)['work'][0]['verified_percent']==0 and s.client.get('/v1/events/'+s.id+'/evidence/'+a['id']+'/content',headers=s.headers()).status_code==404
    assert 'notes.pdf' not in str(s.client.get('/v1/events/'+s.id+'/profile').json())

def test_missing_storage_bad_filename_and_unavailable_transcript(run):
    s=run;r=report(s)
    s.call('/evidence/uploads',{'report_id':r['id'],'report_revision':r['revision'],'kind':'document','name':'../escape.pdf','mime':'application/pdf','size':4},s.subject,expected=422)
    a=s.call('/evidence/uploads',{'report_id':r['id'],'report_revision':r['revision'],'kind':'audio','name':'voice.wav','mime':'audio/wav','size':4},s.subject)['asset']
    v=s.client.get('/v1/events/'+s.id+'/participation/me',headers=s.headers(s.subject)).json()['meta']['version']
    response=s.client.put('/v1/events/'+s.id+'/evidence/'+a['id']+'/content',content=b'WAVE',headers=s.headers(s.subject,key='no-storage',version=str(v)));assert response.status_code==503
    assert s.client.post('/v1/events/'+s.id+'/media/'+a['id']+'/transcription-runs',headers=s.headers(s.subject)).status_code==503
    s.call('/evidence/'+a['id']+'/inspection',{'expected_revision':a['revision'],'decision':'retract','note':'Upload unavailable; keep text report only'},s.subject)
    current=state(s,s.subject)['reports'][0];assert current['evidence_ids']==[]
    s.call('/reports/'+r['id']+'/submit',{'report_revision':current['revision']},s.subject)

def test_attendance_acceptance_is_not_presence(run):
    s=run;b={'assignment_id':s.assignment['id'],'action':'verify','note':'No checkin yet'};s.call('/attendance',b,expected=409)
    claim=s.call('/attendance',{'assignment_id':s.assignment['id'],'action':'claim','note':'Arrived for session'},s.subject);assert claim.get('verified_at') is None and claim.get('verified_present') is None
    pending=state(s)['attendance'][0];assert pending['verified_present'] is None
    verified=s.call('/attendance',{**b,'expected_revision':pending['revision']});assert verified['verified_present'] is True
    corrected=s.call('/attendance',{**b,'action':'correct','expected_revision':verified['revision'],'note':'Incorrect check-in timing'});assert corrected['verified_present'] is None

def test_consumption_report_not_stock_concurrent_verify_and_reversal(run):
    s=run;s.call('/resource-receipts',{'resource_id':s.resource,'quantity':10,'unit':'books','reference':'books-receipt','evidence_reference':'Delivery checked'})
    reservation=s.call('/resource-reservations',{'resource_id':s.resource,'work_id':s.work,'quantity':8,'unit':'books','expected_plan_id':s.plan})['reservation_id']
    r=submitted(s,usage=[{'resource_id':s.resource,'quantity':6,'unit':'books','kind':'consumable'}]);assert s.client.get('/v1/events/'+s.id+'/resources',headers=s.headers()).json()['data']['resources'][0]['on_hand']==10
    body={'report_id':r['id'],'usage_id':r['resource_usage'][0]['id'],'reservation_id':reservation,'quantity':6,'confirm':True,'reference':'consume-1'}
    v=s.flow.get('').json()['data']['version']
    def verify(i):return s.client.post('/v1/events/'+s.id+'/resource-usage/consumption',json={**body,'reference':'consume-'+str(i)},headers=s.headers(key='concurrent-usage-'+str(i),version=str(v))).status_code
    with ThreadPoolExecutor(2) as pool:assert sorted(pool.map(verify,[1,2]))==[200,409]
    resource=s.client.get('/v1/events/'+s.id+'/resources',headers=s.headers()).json()['data']['resources'][0];assert resource['on_hand']==4 and resource['consumed']==6 and resource['available']==2
    with s.factory() as db:op=db.scalar(select(ResourceOperation).where(ResourceOperation.kind=='consume')).id
    s.call('/resource-usage/'+op+'/reversals',{'reason':'Usage was overstated'});assert s.client.get('/v1/events/'+s.id+'/resources',headers=s.headers()).json()['data']['resources'][0]['on_hand']==10

def test_issue_handling_is_not_condition_clearance(run):
    s=run;issue=s.call('/issues',{'work_id':s.work,'description':'Missing workbook pack','severity':'impossible'},s.subject)['blocker']
    s.call('/execution/work/'+s.work+'/start',{},s.subject,expected=409)
    for step in ['acknowledged','investigating','closed']:
        issue=s.call('/issues/'+issue['id']+'/review',{'expected_revision':issue['revision'],'state':step,'condition_cleared':False,'note':'Handling without proof of clearance'})['blocker']
    assert state(s)['work'][0]['execution_status']=='blocked'
    issue=s.call('/issues/'+issue['id']+'/review',{'expected_revision':issue['revision'],'state':'investigating','note':'Reinvestigate'})['blocker']
    s.call('/issues/'+issue['id']+'/review',{'expected_revision':issue['revision'],'state':'resolved','condition_cleared':True,'note':'Actual replacement pack checked'})
    s.call('/execution/work/'+s.work+'/start',{},s.subject)

def test_meetings_discussions_visibility_rsvp_and_no_delivery(run):
    s=run;other,oid=s.person(2)
    internal=s.call('/coordination',{'kind':'note','title':'Private internal note','audience':'internal','status':'published'})['record']
    discussion=s.call('/coordination',{'kind':'discussion','title':'Work-linked question','work_ids':[s.work],'status':'published'},s.subject)['record']
    meeting=s.call('/coordination',{'kind':'meeting','title':'Session review','body':'Discuss learner feedback','invited_account_ids':[s.person_id],'schedule':{'start_day':1,'end_day':1,'start_minute':700,'end_minute':730,'timezone':'Asia/Kolkata'}})['record']
    meeting=s.call('/coordination/'+meeting['id']+'/actions',{'expected_revision':meeting['revision'],'action':'confirm'})['record'];assert meeting['invitation_delivery']=='not_sent'
    s.call('/coordination/'+meeting['id']+'/actions',{'expected_revision':meeting['revision'],'action':'rsvp','response':'going'},s.subject)
    items=s.client.get('/v1/events/'+s.id+'/coordination',headers=s.headers(s.subject)).json()['data']['items'];assert internal['id'] not in {x['id'] for x in items} and discussion['id'] in {x['id'] for x in items}
    assert s.client.get('/v1/events/'+s.id+'/coordination',headers=s.headers(other)).json()['data']['items']==[]
    action=s.call('/coordination',{'kind':'action','title':'Check the follow-up','parent_id':meeting['id'],'status':'open'})['record']
    approved=s.call('/coordination/'+action['id']+'/actions',{'expected_revision':action['revision'],'action':'approve_action','note':'Human authorizes this follow-up'})['record'];assert approved['status']=='approved'
    finished=s.call('/coordination/'+action['id']+'/actions',{'expected_revision':approved['revision'],'action':'complete_action','note':'Actual follow-up performed and checked'})['record'];assert finished['status']=='completed'

class Observer:
    model_profile='group4-non-live-test'
    live_provider=False
    def propose(self,r):
        c=r.authoritative_current['execution_evidence'];assert c['media_input']=='metadata_only' and c['accepted_terms'] and c['work']['id']
        return {'observations':[{'classification':'reported_fact','text':'Participant reports a reading session','supporting_quote':'Held a reading practice session','evidence_ids':[]}],'media_input':'metadata_only','clarification_required':True,'questions':['What feedback is still pending?']}
@pytest.mark.parametrize('failure',[None,'invalid','timeout','stale'])
def test_ai_observations_never_verify_or_mutate_work(run,app,failure):
    s=run;r=submitted(s)
    class Adapter(Observer):
        def propose(self,req):
            if failure=='invalid':return {'verify_work':True}
            if failure=='timeout':time.sleep(.04)
            if failure=='stale':s.call('/reports/'+r['id']+'/review',{'report_revision':r['revision'],'decision':'clarify','note':'Please clarify','evidence_versions':{}})
            return super().propose(req)
    app.state.planning_adapter=Adapter();runinfo=s.call('/execution-assessments',{'report_id':r['id'],'report_revision':r['revision']},expected=202)
    assert bool(work_ai_once(s.factory,app.state.planning_adapter,timeout_seconds=.01 if failure=='timeout' else 30))==(failure is None)
    assert state(s)['work'][0]['verified_percent']==0
    with s.factory() as db:
        ai=db.get(AIRun,runinfo['run_id']);assert (ai.proposal_id is not None)==(failure is None)


def test_equipment_issue_partial_return_and_no_duplicate_return(scenario):
    s=scenario.build(resource=True);f=s.flow
    f.call('/planning/items/resources/'+s.resource,{'kind':'equipment','unit':'sets'},method='PATCH');f.confirm('work');roles=f.call('/planning/actor-derivations',{})['requirements'];s.role=roles[0]['id'];f.call('/planning/actor-requirements/'+s.role,{'headcount':2},method='PATCH');f.confirm('actor');f.call('/setup/draft',{});f.call('/setup/sections/participation',{'data':{'visibility':'public','approval_required':True,'allow_groups':False,'show_open_roles':True,'registration_open':True}},method='PATCH');setup=f.get('/setup').json()['data'];fid=f.call('/finalizations',{'confirm_review':True,'expected_setup_version':setup['configuration']['revision'],'expected_plan_id':setup['plan_id']})['finalization_id'];f.call('/publications',{'finalization_id':fid});s.plan=setup['plan_id']
    subject,id=s.person(1);s.subject=subject;a=s.apply(subject);s.approve(a);o=s.offer(a);s.call('/assignments/'+o['id']+'/accept',{'terms_key':o['terms_key']},subject)
    s.call('/resource-receipts',{'resource_id':s.resource,'quantity':2,'unit':'sets','reference':'equipment-receipt','evidence_reference':'Custody checked'})
    res=s.call('/resource-reservations',{'resource_id':s.resource,'work_id':s.work,'quantity':2,'unit':'sets','expected_plan_id':s.plan})['reservation_id']
    r=submitted(s,usage=[{'resource_id':s.resource,'quantity':2,'unit':'sets','kind':'equipment'}]);b={'report_id':r['id'],'usage_id':r['resource_usage'][0]['id'],'reservation_id':res,'quantity':2,'confirm':True,'reference':'issue-two'}
    s.call('/resource-usage/checkouts',b);s.call('/resource-usage/checkouts',{**b,'reference':'extra-issue'},expected=409)
    s.call('/resource-reservations/'+res+'/release',{},expected=409)
    review(s,r,None,'request_correction')  # Existing custody must still be returnable during report correction.
    s.call('/resource-usage/returns',{**b,'quantity':1,'reference':'return-one'});s.call('/resource-usage/returns',{**b,'quantity':2,'reference':'over-return'},expected=409)
    s.call('/resource-usage/returns',{**b,'quantity':1,'reference':'return-second'});s.call('/resource-reservations/'+res+'/release',{})
    resource=s.client.get('/v1/events/'+s.id+'/resources',headers=s.headers()).json()['data']['resources'][0];assert resource['on_hand']==2 and resource['consumed']==0 and resource['available']==2


def test_scoped_reviewer_cannot_review_self_or_ungranted_stage(run):
    s=run;other,oid=s.person(2);a=s.apply(other);s.approve(a);o=s.offer(a);s.call('/assignments/'+o['id']+'/accept',{'terms_key':o['terms_key']},other)
    stage=state(s)['work'][0]['stage_id'];r=submitted(s)
    s.call('/reports/'+r['id']+'/review',{'report_revision':r['revision'],'decision':'accept','note':'Without grant','verified_percent':10},other,expected=404)
    s.call('/execution/review-grants',{'account_id':oid,'stage_id':stage,'confirm':True})
    s.call('/reports/'+r['id']+'/review',{'report_revision':r['revision'],'decision':'accept','note':'Scoped stage review','verified_percent':10},other)
    s.subject=other;r=submitted(s)
    s.call('/reports/'+r['id']+'/review',{'report_revision':r['revision'],'decision':'accept','note':'Cannot self verify','verified_percent':20},other,expected=404)


def test_memory_source_correction_invalidates_verified_execution_source(run):
    from app.shared.source_resolver import resolve
    from app.memory.schemas import SourceRef
    from app.api.errors import DomainError
    s=run;r=submitted(s,'completion');review(s,r,100);s.call('/execution/work/'+s.work+'/complete',{'reason':'Verified exact session outcome'})
    with unit_of_work(s.factory) as db:
        row=db.scalar(select(ExecutionRevision).where(ExecutionRevision.event_id==s.id,ExecutionRevision.kind=='work.complete'));ref=SourceRef(source_kind='execution',source_id=row.id,source_revision=row.sequence,source_digest=row.digest);source=resolve(db,db.get(Event,s.id).creator_id,s.id,ref);assert source.evidence_stage=='verified' and source.outcome=='inconclusive'
        from app.memory.projections import project
        from app.memory.service import store_candidate
        memory=store_candidate(db,db.get(Event,s.id).creator_id,s.id,project([source])[0],'deterministic');memory_id=memory.id
    s.call('/execution/work/'+s.work+'/reopen',{'reason':'Original outcome now disputed'})
    with s.factory() as db:
        with pytest.raises(DomainError,match='stale_source'):resolve(db,db.get(Event,s.id).creator_id,s.id,ref)
        from app.memory.retrieval import get_memory
        with pytest.raises(DomainError,match='not_found'):get_memory(db,db.get(Event,s.id).creator_id,s.id,memory_id)


def test_media_signature_and_cross_event_references(run,app):
    s=run;r=report(s);app.state.evidence_storage=LocalPrivateStorage(__import__('pathlib').Path(__file__).resolve().parents[1]/'.tmp'/('group4-media-'+uuid.uuid4().hex))
    a=s.call('/evidence/uploads',{'report_id':r['id'],'report_revision':r['revision'],'kind':'image','name':'fake.png','mime':'image/png','size':4},s.subject)['asset']
    v=s.client.get('/v1/events/'+s.id+'/participation/me',headers=s.headers(s.subject)).json()['meta']['version'];response=s.client.put('/v1/events/'+s.id+'/evidence/'+a['id']+'/content',content=b'FAKE',headers=s.headers(s.subject,key='bad-image',version=str(v)));assert response.status_code==422
    old=s.id;s.build();assert s.client.get('/v1/events/'+s.id+'/reports/'+r['id']+'/revisions',headers=s.headers()).status_code==404


def test_dependency_readiness_effort_weight_stage_review_and_measured_impact(scenario):
    s=scenario.build();f=s.flow;stage=next(iter(f.planning()['planning']['stages']))
    second=f.call('/planning/items/work',{'stage_id':stage,'title':'Collect learning feedback','dependency_ids':[s.work],'effort':{'value':6,'unit':'person_hours'},'schedule':{'start_day':1,'end_day':1,'start_minute':660,'end_minute':720,'timezone':'Asia/Kolkata'}},expected=201)['id'];f.confirm('work');roles=f.call('/planning/actor-derivations',{})['requirements'];f.confirm('actor');f.call('/setup/draft',{});f.call('/setup/sections/participation',{'data':{'visibility':'public','approval_required':True,'allow_groups':False,'show_open_roles':True,'registration_open':True}},method='PATCH');setup=f.get('/setup').json()['data'];fid=f.call('/finalizations',{'confirm_review':True,'expected_setup_version':setup['configuration']['revision'],'expected_plan_id':setup['plan_id']})['finalization_id'];f.call('/publications',{'finalization_id':fid});s.plan=setup['plan_id'];s.role=roles[0]['id']
    subject,id=s.person(1);s.subject=subject;a=s.apply(subject,roles=[r['id'] for r in roles]);s.approve(a,roles=[r['id'] for r in roles]);o=s.offer(a);s.call('/assignments/'+o['id']+'/accept',{'terms_key':o['terms_key']},subject)
    secondrole=next(r for r in roles if second in r['work_ids']);o=s.offer(a,role_id=secondrole['id'],work_ids=[second],schedule={'start_day':1,'end_day':1,'start_minute':660,'end_minute':720,'timezone':'Asia/Kolkata'});s.call('/assignments/'+o['id']+'/accept',{'terms_key':o['terms_key']},subject)
    s.call('/execution/work/'+second+'/start',{},subject,expected=409)
    r=submitted(s,'completion');review(s,r,100);s.call('/execution/work/'+s.work+'/complete',{'reason':'First session criteria confirmed'})
    assert state(s)['stages'][0]['verified_progress_percent']==25
    s.call('/execution/work/'+second+'/start',{},subject)
    r=s.call('/reports/draft',{'work_id':second,'body':'Feedback from four learners recorded','claim':'completion','measurements':[{'metric':'learners_feedback_received','value':4,'unit':'people'}]},subject)['report'];r=s.call('/reports/'+r['id']+'/submit',{'report_revision':r['revision']},subject)['report'];r=review(s,r,100)
    profile=s.client.get('/v1/events/'+s.id+'/profile').json()['data'];assert profile['impact']['verified_outputs']==[]
    s.call('/reports/'+r['id']+'/measurements',{'metric':'learners_feedback_received','confirm':True,'note':'Four actual feedback forms checked'})
    s.call('/execution/work/'+second+'/complete',{'reason':'Feedback work verified'})
    assert state(s)['stages'][0]['status']=='ready_for_completion'
    s.call('/execution/stages/'+stage+'/complete',{'reason':'Both work outcomes verified'})
    profile=s.client.get('/v1/events/'+s.id+'/profile').json()['data'];assert profile['stages'][0]['execution_status']=='completed' and profile['impact']['verified_outputs'][0]['value']==4 and profile['impact']['waste_collected_kg'] is None
    s.call('/execution/work/'+s.work+'/reopen',{'reason':'Additional source-specific feedback requires separate review'})
    r=s.call('/reports/draft',{'work_id':s.work,'body':'Two additional source-specific feedback records','measurements':[{'metric':'learners_feedback_received','value':2,'unit':'people'}]},subject)['report'];r=s.call('/reports/'+r['id']+'/submit',{'report_revision':r['revision']},subject)['report'];r=review(s,r,100)
    s.call('/reports/'+r['id']+'/measurements',{'metric':'learners_feedback_received','confirm':True,'note':'Two source-specific forms checked; overlap with other reports not established'})
    profile=s.client.get('/v1/events/'+s.id+'/profile').json()['data'];assert len(profile['impact']['verified_outputs'])==2 and profile['stages'][0]['execution_status']=='planned'


def test_distinct_valid_writes_cannot_share_stale_event_version(run):
    s=run;version=s.flow.get('').json()['data']['version']
    def create(i):
        return s.client.post('/v1/events/'+s.id+'/coordination',json={'kind':'note','title':'Independent note '+str(i),'body':'No capacity conflict needed to detect stale version','audience':'internal','status':'published'},headers=s.headers(key='version-race-'+str(i),version=str(version))).status_code
    with ThreadPoolExecutor(2) as pool:assert sorted(pool.map(create,[1,2]))==[200,409]
