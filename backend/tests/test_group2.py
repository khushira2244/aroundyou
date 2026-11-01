from copy import deepcopy
from sqlalchemy import select,func,text
from sqlalchemy.exc import DBAPIError
import pytest
from app.events.models import Event,ContextRevision
from app.planning.models import PlanVersion
from app.planning.draft_models import PlanningDraft
from app.ai.models import AIProposal,AIRun
from app.ai.service import work_ai_once
from app.publication.models import Publication,SetupRevision,PublishedRole
from app.access.models import User
from app.shared.unit_of_work import unit_of_work
from app.shared.outbox import dispatch_one
from app.memory.worker import work_once
from app.memory.retrieval import retrieve

FORM={'title':'Community reading workshop','category':'Education','purpose':'Practice reading together','goal':'Run reading sessions for local adults','format':'in_person','startDate':'2026-11-05','endDate':'2026-11-07','startTime':'09:00','endTime':'12:00','timezone':'Asia/Kolkata','venue':'Library','area':'Town center','city':'Hazaribagh','country':'India','workScope':'Run a reading workshop','executionIntent':'  Original private explanation: projector status is unconfirmed.  ','intentSource':'written','outcomes':'Practice reading and record reviewed feedback','targetGroups':['Adults'],'confirmAccuracy':True,'confirmPlanning':True,'confirmContinue':True}

class Flow:
    def __init__(self,client,headers):self.client=client;self.headers=headers;self.id=None
    def get(self,suffix):return self.client.get('/v1/events/'+self.id+suffix,headers=self.headers())
    def call(self,suffix,body=None,method='POST',expected=200):
        version=self.get('').json()['data']['version'];key=__import__('uuid').uuid4().hex
        h=self.headers(key=key,version=str(version))
        result=self.client.request(method,'/v1/events/'+self.id+suffix,json=body,headers=h)
        assert result.status_code==expected,result.text
        return result.json().get('data')
    def new(self,title=None):
        result=self.client.post('/v1/events/drafts',json={},headers=self.headers(key=__import__('uuid').uuid4().hex));assert result.status_code==201,result.text
        self.id=result.json()['data']['event']['id']
        form={**FORM,'title':title or FORM['title']}
        self.call('/draft',{'step':4,'form':form},method='PATCH')
        return self.id
    def create(self):
        version=self.get('').json()['data']['version'];return self.call('/confirm-creation',{'expected_draft_version':version})
    def planning(self):return self.get('/planning').json()['data']
    def confirm(self,level):
        p=self.planning();return self.call('/planning/'+level+'-confirmations',{'expected_draft_version':p['draft_version']})
    def basic_plan(self):
        self.call('/planning/draft',{})
        stage=self.call('/planning/items/stages',{'title':'Learning session','relative_start':1,'relative_end':3},expected=201)['id']
        self.confirm('stage')
        work=self.call('/planning/items/work',{'stage_id':stage,'title':'Reading practice','effort':{'value':6,'unit':'person_hours'},'schedule':{'start_day':1,'end_day':1,'start_minute':540,'end_minute':660,'timezone':'Asia/Kolkata'},'skills':['Teaching'],'evidence_requirements':['Reviewed session notes']},expected=201)['id']
        return stage,work
    def confirmed(self):
        self.basic_plan();self.confirm('work');self.call('/planning/actor-derivations',{});self.confirm('actor');self.call('/setup/draft',{})
    def finalize(self,visibility='public'):
        self.call('/setup/sections/participation',{'data':{'visibility':visibility,'approval_required':True,'allow_groups':False,'show_open_roles':True,'registration_open':False}},method='PATCH')
        s=self.get('/setup').json()['data']
        return self.call('/finalizations',{'confirm_review':True,'expected_setup_version':s['configuration']['revision'],'expected_plan_id':s['plan_id']})['finalization_id']
    def publish(self,visibility='public'):
        fid=self.finalize(visibility);return self.call('/publications',{'finalization_id':fid})

@pytest.fixture
def flow(seeded,client,headers):return Flow(client,headers)

def test_creation_durable_two_events_and_original_text(flow,factory):
    a=flow.new('A');assert flow.get('/creation').json()['data']['context']['original_text']==FORM['executionIntent']
    flow.create();assert flow.get('/creation').json()['data']['runtime']['publication']=='unpublished'
    b=flow.new('B');assert b!=a
    flow.call('/context-revisions',{'text':'Reviewed transcript exact text','source':'reviewed_transcript'})
    with factory() as db:
        assert db.get(Event,a).title=='A';assert db.get(Event,b).title=='B'
        originals=list(db.scalars(select(ContextRevision).where(ContextRevision.event_id==b)))
        assert len(originals)==2 and any(x.original_text==FORM['executionIntent'] for x in originals)
    assert flow.client.get('/v1/events/'+a+'/creation',headers=flow.headers()).json()['data']['event']['title']=='A'

def test_partial_draft_resume_and_required_fields(flow):
    r=flow.client.post('/v1/events/drafts',json={},headers=flow.headers(key='partial'));flow.id=r.json()['data']['event']['id']
    flow.call('/draft',{'step':1,'form':{'title':'Partially entered'}},method='PATCH')
    saved=flow.get('/creation').json()['data'];assert saved['runtime']['draft']['creation_details']['title']=='Partially entered'
    version=flow.get('').json()['data']['version'];flow.call('/confirm-creation',{'expected_draft_version':version},expected=422)

def test_manual_interpretation_keeps_original(flow):
    flow.new();ctx=flow.get('/creation').json()['data']['context']
    flow.call('/context-interpretations',{'context_version':ctx['version'],'interpretation':{'scope':['Reading sessions'],'unknowns':['Projector availability']}})
    read=flow.get('/creation').json()['data'];assert read['context']['approved_interpretation']['source']=='human_reviewed';assert read['context']['original_text']==FORM['executionIntent']
    flow.call('/context-revisions',{'text':'A changed original','source':'written'})
    assert flow.get('/creation').json()['data']['context']['approved_interpretation'] is None

def test_creation_idempotency_and_stale_commands(flow):
    h=flow.headers(key='create-repeat')
    a=flow.client.post('/v1/events/drafts',json={},headers=h);b=flow.client.post('/v1/events/drafts',json={},headers=h);assert a.json()==b.json()
    flow.id=a.json()['data']['event']['id']
    response=flow.client.patch('/v1/events/'+flow.id+'/draft',json={'step':1,'form':{'title':'One'}},headers=flow.headers(key='stale',version='999'));assert response.status_code==409
    response=flow.client.post('/v1/events/drafts',json={'format':'online'},headers=h);assert response.status_code==409

def test_manual_stage_work_actor_lifecycle_and_no_fake_people(flow,factory):
    flow.new();flow.create();stage,work=flow.basic_plan()
    assert flow.planning()['planning']['stage_confirmed']
    flow.confirm('work');roles=flow.call('/planning/actor-derivations',{})['requirements'];assert roles[0]['proposed_headcount']==3;assert roles[0]['source_work_ids']==[work]
    flow.confirm('actor');assert flow.get('/creation').json()['data']['runtime']['lifecycle']=='planned'
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(User))==3
        assert db.scalar(select(func.count()).select_from(PlanVersion).where(PlanVersion.event_id==flow.id))==3
        assert db.get(Event,flow.id).active_plan_id
    flow.call('/planning/items/work/'+work,{'skills':['Teaching','First aid']},method='PATCH')
    p=flow.planning()['planning'];assert not p['work_confirmed'] and not p['actors_confirmed'] and p['derived_from'] is None

def test_plan_graph_rejects_cycles_missing_refs_timing_units(flow):
    flow.new();flow.create();stage,work=flow.basic_plan()
    for patch in [{'dependency_ids':[work]},{'dependency_ids':['foreign']},{'volume':{'value':-1,'unit':'people'}},{'effort':{'value':2,'unit':'kg'}},{'schedule':{'start_day':4,'end_day':4,'start_minute':540,'end_minute':660}},{'resource_requirement_ids':['other']}]:
        flow.call('/planning/items/work/'+work,patch,method='PATCH',expected=422)
    flow.call('/planning/items/stages/'+stage,{'dependency_ids':['missing']},method='PATCH',expected=422)
    assert flow.planning()['planning']['work'][work]['dependency_ids']==[]

def test_groups_zones_resources_are_scoped_demand_only(flow):
    flow.new();flow.create();stage,work=flow.basic_plan()
    group=flow.call('/planning/items/groups',{'stage_id':stage,'title':'Tutors'},expected=201)['id']
    zone=flow.call('/planning/items/zones',{'label':'Reading room'},expected=201)['id']
    resource=flow.call('/planning/items/resources',{'title':'Projector','kind':'equipment','quantity':2,'unit':'items','work_ids':[work]},expected=201)['id']
    flow.call('/planning/items/work/'+work,{'work_group_id':group,'zone_ids':[zone],'resource_requirement_ids':[resource]},method='PATCH')
    flow.confirm('work');flow.call('/planning/actor-derivations',{});flow.confirm('actor');flow.call('/setup/draft',{})
    flow.call('/setup/sections/resources',{'data':{'claims':{resource:10}}},method='PATCH')
    r=flow.get('/setup').json()['data']['resources'][0];assert r['required']==2 and r['reported_available']==10 and r['available'] is None and r['delivered']==0 and r['reserved']==0

def test_pending_manual_proposal_reject_and_stale_apply(flow):
    flow.new();flow.create();stage,work=flow.basic_plan()
    proposed=flow.call('/planning/stage-edits',{'stage_id':stage,'start_day':2,'duration_days':3})['proposal']
    assert flow.planning()['planning']['stages'][stage]['relative_start']==1
    flow.call('/planning/proposals/'+proposed['id']+'/reject',{'reviewed_digest':proposed['digest']})
    assert flow.planning()['planning']['stages'][stage]['relative_start']==1
    proposal=flow.call('/planning/stage-edits',{'stage_id':stage,'start_day':2,'duration_days':3})['proposal']
    flow.call('/planning/items/stages/'+stage,{'title':'Revised stage'},method='PATCH')
    flow.call('/planning/proposals/'+proposal['id']+'/apply',{'reviewed_digest':proposal['digest']},expected=409)

def test_approved_manual_diff_and_immutable_plans(flow,factory):
    flow.new();flow.create();stage,work=flow.basic_plan();old_plan=flow.planning()['active_plan_id']
    p=flow.call('/planning/stage-edits',{'stage_id':stage,'start_day':2,'duration_days':3})['proposal']
    flow.call('/planning/proposals/'+p['id']+'/apply',{'reviewed_digest':p['digest']})
    assert flow.planning()['planning']['work'][work]['schedule']['start_day']==2
    assert not flow.planning()['planning']['stage_confirmed']
    flow.confirm('stage')
    with factory() as db:assert db.get(PlanVersion,old_plan).content['stages'][0]['relative_start']==1

def test_governance_is_authorized_internal_and_nonblocking(flow,headers):
    flow.new();flow.create();flow.call('/planning/draft',{})
    ticket=flow.call('/governance/tickets',{})['ticket']
    flow.call('/governance/tickets/'+ticket['id']+'/documents',{'name':'Safety notes.pdf','document_type':'safety','document_reference':'Organizer retained original','size':100,'mime':'application/pdf'})
    flow.call('/governance/tickets/'+ticket['id']+'/reminders',{'email_updates':True,'remind_documents':True},method='PATCH')
    g=flow.get('/governance').json()['data'];assert not g['guidance']['mandatory_gate'] and not g['ticket']['external_submission'];assert g['ticket']['documents'][0]['storage']=='reference_only'
    assert flow.client.get('/v1/events/'+flow.id+'/governance',headers=headers('outsider-subject')).status_code==404
    flow.call('/planning/items/stages',{'title':'Normal planning continues'},expected=201)

def test_finalize_publish_separate_and_private_projection(flow,headers):
    flow.new();flow.create();flow.confirmed()
    flow.call('/setup/invitation-drafts',{'label':'Private invitee','email':'private-invite@example.com'})
    flow.call('/setup/partner-drafts',{'label':'Private sponsor discussion','support_type':'equipment','details':'Unverified promise'})
    flow.call('/setup/sections/location',{'data':{'emergency_contact':'PRIVATE_EMERGENCY','access_instructions':'PRIVATE_ACCESS'}},method='PATCH')
    flow.call('/setup/sections/communications',{'data':{'welcome_message':'Welcome','contact_email':'PRIVATE_ORGANIZER_EMAIL','contact_phone':'PRIVATE_PHONE'}},method='PATCH')
    final=flow.finalize();assert flow.get('/creation').json()['data']['runtime']['publication']=='unpublished'
    assert flow.client.get('/v1/events/'+flow.id+'/profile').status_code==404
    flow.call('/publications',{'finalization_id':final})
    result=flow.client.get('/v1/events/'+flow.id+'/profile');assert result.status_code==200,result.text
    profile=result.json()['data'];assert len(profile['tabs'])==8 and 'Meetings' not in profile['tabs'];assert profile['insights']['counts'] is None
    assert all(x not in result.text for x in ['PRIVATE_EMERGENCY','PRIVATE_ACCESS','PRIVATE_ORGANIZER_EMAIL','PRIVATE_PHONE','Private invitee','Private sponsor discussion','Original private explanation'])
    assert profile['impact']['accepted_participants']==0 and profile['roles'][0]['accepted_positions']==0
    assert profile['event']['context_id'] is None
    assert flow.client.get('/v1/events/'+flow.id+'/profile?preview=organizer',headers=headers('outsider-subject')).status_code==404

@pytest.mark.parametrize('visibility',['invite_only','community_only'])
def test_nonpublic_publications_hidden_from_discovery(flow,headers,visibility):
    flow.new();flow.create();flow.confirmed();flow.publish(visibility)
    assert flow.client.get('/v1/events/'+flow.id+'/profile').status_code==404
    assert flow.client.get('/v1/events/'+flow.id+'/profile',headers=headers('outsider-subject')).status_code==404
    assert flow.id not in flow.client.get('/v1/events').text
    assert flow.client.get('/v1/events/'+flow.id+'/profile',headers=headers()).status_code==200

def test_setup_change_invalidates_finalization_and_old_release_stays_frozen(flow,factory):
    flow.new();flow.create();flow.confirmed();release=flow.publish()
    flow.call('/setup/sections/communications',{'data':{'welcome_message':'New unpublished text'}},method='PATCH')
    flow.call('/publications',{'finalization_id':release['publication_id']},expected=409)
    assert flow.client.get('/v1/events/'+flow.id+'/profile').json()['data']['communications']['welcome_message']==''
    newer=flow.publish();assert newer['publication_id']!=release['publication_id']
    assert flow.client.get('/v1/events/'+flow.id+'/profile').json()['data']['communications']['welcome_message']=='New unpublished text'
    with pytest.raises(DBAPIError):
        with unit_of_work(factory) as db:db.execute(text("UPDATE publications SET visibility='public'"))

def test_schedule_preferences_do_not_fake_scheduler(flow):
    flow.new();flow.create();flow.confirmed();flow.call('/setup/publication-preferences',{'mode':'scheduled','date':'2026-11-05','time':'09:00'},method='PATCH');fid=flow.finalize();flow.call('/publications',{'finalization_id':fid},expected=503)

def test_context_revision_invalidates_child_confirmations(flow):
    flow.new();flow.create();flow.confirmed();old=flow.get('/setup').json()['data']['plan_id']
    flow.call('/context-revisions',{'text':'Changed scope with original retained','source':'written'})
    assert not flow.planning()['planning']['stage_confirmed'] and not flow.planning()['planning']['actors_confirmed']
    assert flow.planning()['active_plan_id']==old
    flow.call('/setup/draft',{},expected=409)

def test_group2_event_memory_projection(flow,factory):
    flow.new();flow.create();flow.basic_plan()
    for _ in range(20):
        if not dispatch_one(factory):break
    for _ in range(20):
        if work_once(factory) is None:break
    with unit_of_work(factory) as db:
        actor=db.get(Event,flow.id).creator_id;bundle=retrieve(db,actor,flow.id);assert bundle['items'];assert all(x['event_id']==flow.id for x in bundle['items'])

class FakeMuse:
    model_profile='test-adapter-not-live-muse'
    live_provider=False
    def propose(self,r):
        assert 'original_context' in r.authoritative_current
        assert 'memory' in r.cited_historical_memory
        if r.kind=='understanding':return {'scope':['Reading sessions'],'unknowns':['Projector availability']}
        if r.kind=='governance':return {'items':[{'id':'advice','title':'Confirm venue arrangements','detail':'Ask the venue owner; no permission inferred'}]}
        return deepcopy(r.authoritative_current['planning_draft'])

def test_ai_unconfigured_and_controlled_understanding_review(flow,app,factory):
    flow.new();flow.call('/context-proposals',{},expected=503)
    app.state.planning_adapter=FakeMuse()
    run=flow.call('/context-proposals',{},expected=202)
    assert work_ai_once(factory,app.state.planning_adapter) is True
    result=flow.client.get('/v1/ai-runs/'+run['run_id'],headers=flow.headers()).json()['data'];p=result['proposal']
    assert not p['provenance']['model_execution'] and p['status']=='pending'
    assert flow.get('/creation').json()['data']['context']['approved_interpretation'] is None
    flow.call('/context-proposals/'+p['id']+'/review',{'decision':'accept','reviewed_digest':p['digest']})
    assert flow.get('/creation').json()['data']['context']['approved_interpretation']['scope']==['Reading sessions']

def test_ai_reject_malformed_stale_and_no_automatic_plan_mutation(flow,app,factory):
    flow.new();flow.create();stage,work=flow.basic_plan();app.state.planning_adapter=FakeMuse()
    run=flow.call('/planning/stage-proposals',{},expected=202);assert work_ai_once(factory,app.state.planning_adapter) is True
    result=flow.client.get('/v1/ai-runs/'+run['run_id'],headers=flow.headers()).json()['data'];p=result['proposal']
    before=flow.planning()['draft_version'];assert p['status']=='pending';assert flow.planning()['draft_version']==before
    flow.call('/planning/proposals/'+p['id']+'/reject',{'reviewed_digest':p['digest']})
    run=flow.call('/planning/stage-proposals',{},expected=202)
    flow.call('/planning/items/stages/'+stage,{'title':'Changed during run'},method='PATCH')
    assert work_ai_once(factory,app.state.planning_adapter) is False
    assert flow.client.get('/v1/ai-runs/'+run['run_id'],headers=flow.headers()).json()['data']['status']=='stale'
    class Bad(FakeMuse):
        def propose(self,r):return {'approved':True,'rewrite_plan':True}
    flow.confirm('stage');app.state.planning_adapter=Bad();run=flow.call('/planning/work-proposals',{},expected=202)
    assert work_ai_once(factory,app.state.planning_adapter) is False
    with factory() as db:assert db.get(AIRun,run['run_id']).proposal_id is None

def test_actor_configuration_and_optional_questions(flow):
    flow.new();flow.create();flow.confirmed();p=flow.planning();role=next(iter(p['planning']['roles']))
    flow.call('/planning/actor-requirements/'+role,{'headcount':2,'capabilities':['Teaching']},method='PATCH');assert not flow.planning()['planning']['actors_confirmed']
    flow.confirm('actor');flow.call('/setup/draft',{})
    flow.call('/setup/participant-configuration',{'collect_insights':True,'public_aggregates':True,'fields':{'age_range':True}},method='PUT')
    flow.call('/setup/participant-configuration',{'questions':[{'id':'q','text':'Age?','optional':False}]},method='PUT',expected=422)

def test_foreign_ids_cannot_reuse_plan_items_or_setup_roles(flow,headers):
    a=flow.new();flow.create();stage,work=flow.basic_plan();b=flow.new('Second');flow.create();flow.call('/planning/draft',{})
    flow.call('/planning/items/work',{'title':'Foreign stage','stage_id':stage},expected=422)
    assert flow.client.get('/v1/events/'+a+'/planning',headers=headers('outsider-subject')).status_code==404

def test_development_cors_is_scoped(client):
    allowed=client.options('/v1/events/drafts',headers={'Origin':'http://127.0.0.1:5173','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Authorization,If-Match,Idempotency-Key'})
    assert allowed.headers.get('access-control-allow-origin')=='http://127.0.0.1:5173'
    denied=client.options('/v1/events/drafts',headers={'Origin':'https://untrusted.invalid','Access-Control-Request-Method':'POST'})
    assert 'access-control-allow-origin' not in denied.headers


def test_reviewed_governance_stays_advisory_and_becomes_stale_on_context_change(flow,app,factory):
    flow.new();flow.create();app.state.planning_adapter=FakeMuse()
    run=flow.call('/governance/assessments',{},expected=202);assert work_ai_once(factory,app.state.planning_adapter) is True
    p=flow.client.get('/v1/ai-runs/'+run['run_id'],headers=flow.headers()).json()['data']['proposal']
    assert flow.get('/governance').json()['data']['items']==[]
    flow.call('/governance/proposals/'+p['id']+'/review',{'decision':'accept','reviewed_digest':p['digest']})
    state=flow.get('/governance').json()['data'];assert state['items'] and state['guidance']['permission_status']=='not_verified'
    flow.call('/context-revisions',{'text':'Changed event scope','source':'written'})
    assert flow.get('/governance').json()['data']['items']==[]


def test_human_interpretation_revision_invalidates_existing_plan_confirmations(flow):
    flow.new();flow.create();flow.confirmed();ctx=flow.get('/creation').json()['data']['context']
    flow.call('/context-interpretations',{'context_version':ctx['version'],'interpretation':{'scope':['Smaller learning sessions']}})
    state=flow.planning()['planning'];assert not state['stage_confirmed'] and not state['actors_confirmed']


def test_proposal_payload_is_database_immutable(flow,factory):
    flow.new();flow.create();stage,work=flow.basic_plan();p=flow.call('/planning/stage-edits',{'stage_id':stage,'start_day':2,'duration_days':3})['proposal']
    with pytest.raises(DBAPIError):
        with unit_of_work(factory) as db:db.execute(text("UPDATE ai_proposals SET payload='{}'::jsonb WHERE id=:id"),{'id':p['id']})


def test_source_format_and_zero_known_demand(flow):
    flow.new();flow.create();stage,work=flow.basic_plan()
    flow.call('/planning/items/work/'+work,{'effort':{'value':0,'unit':'person_hours'}},method='PATCH')
    flow.confirm('work');roles=flow.call('/planning/actor-derivations',{})['requirements'];assert roles[0]['proposed_headcount']==0


def test_private_source_revocation_blocks_composed_read_and_write_projections(flow,factory):
    flow.new();flow.create();flow.confirmed()
    from app.access.models import EventGrant
    with unit_of_work(factory) as db:
        user=db.get(Event,flow.id).creator_id
        grant=db.scalar(select(EventGrant).where(EventGrant.event_id==flow.id,EventGrant.user_id==user,EventGrant.permission=='source:private'));grant.active=False
    assert flow.get('/setup').status_code==404
    assert flow.get('/creation').status_code==404
    assert flow.get('/planning').status_code==404
    flow.call('/planning/draft',{},expected=404)


def test_ai_source_change_during_model_call_is_rejected_before_review(flow,app,factory):
    flow.new();flow.create();stage,work=flow.basic_plan()
    class Race(FakeMuse):
        def propose(self,request):
            flow.call('/planning/items/stages/'+stage,{'title':'Organizer changed stage during inference'},method='PATCH')
            return super().propose(request)
    app.state.planning_adapter=Race();run=flow.call('/planning/stage-proposals',{},expected=202)
    assert work_ai_once(factory,app.state.planning_adapter) is False
    with factory() as db:
        record=db.get(AIRun,run['run_id']);assert record.status=='stale' and record.proposal_id is None


def test_large_plan_memory_projection_remains_bounded_and_source_linked(flow,factory):
    flow.new();flow.create()
    from app.events.source_revisions import append_plan
    from app.shared.source_resolver import resolve
    from app.memory.schemas import SourceRef
    from app.memory.service import enqueue
    from app.memory.schemas import ExtractionRequest
    with unit_of_work(factory) as db:
        event=db.get(Event,flow.id)
        plan=append_plan(db,event.creator_id,event.id,{'stages':[{'id':'learning','title':'Reading sessions'}],'work':[{'id':'work-'+str(i),'stage_id':'learning','title':'Practice exercise '+str(i),'scope':'Describe the exercise '*30} for i in range(100)]},event.version)
        ref=SourceRef(source_kind='plan',source_id=plan.id,source_revision=plan.sequence,source_digest=plan.digest)
        projected=resolve(db,event.creator_id,event.id,ref);assert len(projected.text)<4000;assert 'work_count' in projected.text and '100' in projected.text
        enqueue(db,event.creator_id,event.id,ExtractionRequest(source_refs=[ref]))
    assert work_once(factory) is True


def test_reviewed_work_edit_preserves_parent_stage_confirmation(flow):
    flow.new();flow.create();stage,work=flow.basic_plan();flow.confirm('work')
    p=flow.call('/planning/work-edits',{'work_id':work,'patch':{'title':'Revised reading practice'}})['proposal']
    flow.call('/planning/proposals/'+p['id']+'/apply',{'reviewed_digest':p['digest']})
    result=flow.planning()['planning'];assert result['stage_confirmed'] and not result['work_confirmed'] and not result['actors_confirmed'];assert result['work'][work]['revision']==2
