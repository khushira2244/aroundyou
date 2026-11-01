from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import time,uuid
import pytest
from sqlalchemy import select,text,func
from sqlalchemy.exc import DBAPIError
from tests.test_group3 import scenario
from app.ai.models import AIRun
from app.events.models import Event
from app.ai.service import work_ai_once
from app.participation.models import AssignmentTerms,OperationalSource
from app.sponsorship.models import OrganizationMembership,SupportOfferRevision
from app.shared.unit_of_work import unit_of_work


def test_multiple_roles_partial_review_and_schedule_overlap(scenario):
    s=scenario.build();subject,id=s.person(1)
    # A second work-linked role is derived and explicitly published before applying.
    f=s.flow;stage=next(iter(f.planning()['planning']['stages']))
    work=f.call('/planning/items/work',{'stage_id':stage,'title':'Welcome participants','effort':{'value':2,'unit':'person_hours'},'schedule':{'start_day':1,'end_day':1,'start_minute':540,'end_minute':660,'timezone':'Asia/Kolkata'}},expected=201)['id']
    f.confirm('work');roles=f.call('/planning/actor-derivations',{})['requirements'];f.confirm('actor');f.call('/setup/draft',{})
    f.call('/setup/sections/participation',{'data':{'visibility':'public','approval_required':True,'allow_groups':False,'show_open_roles':True,'registration_open':True}},method='PATCH')
    setup=f.get('/setup').json()['data'];fid=f.call('/finalizations',{'confirm_review':True,'expected_setup_version':setup['configuration']['revision'],'expected_plan_id':setup['plan_id']})['finalization_id'];f.call('/publications',{'finalization_id':fid});s.plan=setup['plan_id'];s.role=roles[0]['id'];other=roles[1]['id']
    app=s.apply(subject,roles=[s.role,other]);result=s.approve(app,roles=[s.role])
    assert result['application']['approved_role_ids']==[s.role] and set(result['application']['role_requirement_ids'])=={s.role,other}
    offered=s.offer(app);s.call('/assignments/'+offered['id']+'/accept',{'terms_key':offered['terms_key']},subject)
    s.call('/applications/'+app+'/assignment-offers',{'role_id':other,'work_ids':[work],'schedule':{'start_day':1,'end_day':1,'start_minute':540,'end_minute':660,'timezone':'Asia/Kolkata'},'expected_plan_id':s.plan},expected=409)


def test_cross_event_actual_datetime_conflicts_and_own_isolation(scenario):
    s=scenario.build();subject,id=s.person(1);a=s.apply(subject);s.approve(a);o=s.offer(a);s.call('/assignments/'+o['id']+'/accept',{'terms_key':o['terms_key']},subject);first=s.id
    s.build();a=s.apply(subject);s.approve(a)
    s.call('/applications/'+a+'/assignment-offers',{'role_id':s.role,'work_ids':[s.work],'schedule':{'start_day':1,'end_day':1,'start_minute':540,'end_minute':660,'timezone':'Asia/Kolkata'},'expected_plan_id':s.plan},expected=409)
    assert first!=s.id


def test_expiry_and_withdrawn_offer_cannot_be_accepted(scenario):
    s=scenario.build();subject,id=s.person(1);a=s.apply(subject);s.approve(a);o=s.offer(a)
    s.call('/assignments/'+o['id']+'/withdraw',{})
    s.call('/assignments/'+o['id']+'/accept',{'terms_key':o['terms_key']},subject,expected=409)
    # Exact immutable terms cannot be edited to manufacture a later expiry.
    with pytest.raises(DBAPIError):
        with unit_of_work(s.factory) as db:db.execute(text("UPDATE assignment_terms SET expires_at=now() WHERE assignment_id=:id"),{'id':o['id']})


def test_organization_membership_private_profile_versions_and_unverified_registration(scenario):
    s=scenario.build(resource=True);subject,id=s.person(1);outsider,oid=s.person(2)
    profile={'name':'Community books organization','type':'Association','description':'Supplies educational materials','contact_name':'Private Contact','email':'private@example.test','phone':'PRIVATE_PHONE','city':'Hazaribagh','country':'India','focus':['Education'],'capabilities':['materials'],'coverage':['Hazaribagh'],'recognition':{'show_profile':True,'show_contributions':True}}
    h=s.headers(subject,key='org-create');r=s.client.post('/v1/organizations/draft',json={'profile':profile},headers=h);assert r.status_code==200,r.text;org=r.json()['data']['organization_id']
    assert s.client.get('/v1/organizations/'+org+'/sponsor-portal',headers=s.headers(outsider)).status_code==404
    r=s.client.post('/v1/organizations/'+org+'/registration/complete',json={},headers=s.headers(subject,key='org-complete'));assert r.json()['data']['verified'] is False
    portal=s.client.get('/v1/organizations/'+org+'/sponsor-portal',headers=s.headers(subject)).json()['data'];assert portal['membership']['account_id']==id
    r=s.client.patch('/v1/organizations/'+org+'/registration',json={'profile':profile,'expected_version':0},headers=s.headers(subject,key='stale-org'));assert r.status_code==409
    version=s.flow.get('').json()['data']['version'];body={'event_id':s.id,'resource_id':s.resource,'support_type':'materials','description':'Books','quantity':10,'unit':'books','submit':True}
    r=s.client.post('/v1/organizations/'+org+'/offers',json=body,headers=s.headers(subject,key='org-offer',version=str(version)));assert r.status_code==200,r.text
    offer=r.json()['data']['offer'];s.call('/sponsor-offers/'+offer['id']+'/accept',{})
    public=s.client.get('/v1/events/'+s.id+'/profile').json()['data'];assert public['sponsors'][0]['verified_fulfillment']==0;assert 'PRIVATE_PHONE' not in str(public) and 'private@example.test' not in str(public)
    with s.factory() as db:assert db.scalar(select(func.count()).select_from(SupportOfferRevision))==2


def test_reservation_concurrency_exact_units_and_plan_identity(scenario):
    s=scenario.build(resource=True);s.call('/resource-receipts',{'resource_id':s.resource,'quantity':10,'unit':'books','reference':'received-ten','evidence_reference':'Organizer handover verification'})
    version=s.flow.get('').json()['data']['version'];body={'resource_id':s.resource,'work_id':s.work,'quantity':7,'unit':'books','expected_plan_id':s.plan}
    def reserve(i):return s.client.post('/v1/events/'+s.id+'/resource-reservations',json=body,headers=s.headers(key='reserve-'+str(i),version=str(version))).status_code
    with ThreadPoolExecutor(2) as pool:assert sorted(pool.map(reserve,[1,2]))==[200,409]
    s.call('/resource-reservations',{**body,'quantity':1,'unit':'kg'},expected=409)
    s.flow.call('/planning/items/resources/'+s.resource,{'unit':'kg'},method='PATCH',expected=409)

class Advisory:
    model_profile='test-group3-not-live'
    live_provider=False
    def propose(self,r):
        assert r.authoritative_current['original_context'] and 'memory' in r.cited_historical_memory
        c=r.authoritative_current['participation_and_resources'];role=c['published_plan']['roles'][0]
        assert c['applicant']['reported_answers']['skills']=='Self-reported reading experience'
        return {'applicant_understanding':['Experience is self-reported'],'unknowns':['Qualifications not independently established'],'clarification_questions':['What reading activities do you prefer?'],'recommendations':[{'role_id':role['id'],'work_ids':role['work_ids'],'supporting_statements':['Self-reported reading experience'],'explanation':'Discuss reading session participation','missing_information':['Confirm suitability'],'trade_offs':['Schedule must be checked deterministically']}]}


def test_ai_advisory_actual_context_review_staleness_no_automatic_offer(scenario,app):
    s=scenario.build();subject,id=s.person(1);a=s.apply(subject)
    s.call('/participation-assessments',{'application_id':a},expected=503)
    app.state.planning_adapter=Advisory();run=s.call('/participation-assessments',{'application_id':a},expected=202)
    assert work_ai_once(s.factory,app.state.planning_adapter)
    p=s.client.get('/v1/ai-runs/'+run['run_id'],headers=s.headers()).json()['data']['proposal'];assert not p['provenance']['model_execution']
    state=s.client.get('/v1/events/'+s.id+'/organizer/participants',headers=s.headers()).json()['data'];assert state['assignments']==[] and state['applications'][0]['intelligence']['assessment']['review_status']=='pending'
    s.call('/participation-proposals/'+p['id']+'/review',{'decision':'accept','reviewed_digest':p['digest']})
    s.call('/applications/'+a+'/information-revisions',{'answers':{'skills':'A corrected original statement'}},subject)
    state=s.client.get('/v1/events/'+s.id+'/organizer/participants',headers=s.headers()).json()['data'];assert state['applications'][0]['intelligence']['status']=='stale' and state['assignments']==[]

@pytest.mark.parametrize('failure',['malformed','invented_statement','timeout'])
def test_ai_invalid_or_timeout_does_not_create_authority(scenario,app,failure):
    s=scenario.build();subject,id=s.person(1);a=s.apply(subject)
    class Bad(Advisory):
        def propose(self,r):
            if failure=='timeout':time.sleep(.05);return super().propose(r)
            if failure=='malformed':return {'accept_assignment':True}
            data=super().propose(r);data['recommendations'][0]['supporting_statements']=['INVENTED QUALIFICATION'];return data
    app.state.planning_adapter=Bad();run=s.call('/participation-assessments',{'application_id':a},expected=202)
    assert work_ai_once(s.factory,app.state.planning_adapter,timeout_seconds=.01) is False
    with s.factory() as db:assert db.get(AIRun,run['run_id']).proposal_id is None


def test_operational_memory_is_source_backed_proposed_not_work_success(scenario):
    from app.shared.source_resolver import resolve
    from app.memory.schemas import SourceRef
    from app.memory.service import enqueue
    from app.memory.schemas import ExtractionRequest
    from app.memory.worker import work_once
    s=scenario.build();subject,id=s.person(1);a=s.apply(subject)
    with unit_of_work(s.factory) as db:
        event=db.get(Event,s.id);source=db.scalar(select(OperationalSource).where(OperationalSource.aggregate_id==a).order_by(OperationalSource.sequence.desc()))
        ref=SourceRef(source_kind='operational',source_id=source.id,source_revision=source.sequence,source_digest=source.digest)
        value=resolve(db,event.creator_id,event.id,ref);assert value.outcome=='unknown' and value.evidence_stage=='proposed'
        enqueue(db,event.creator_id,event.id,ExtractionRequest(source_refs=[ref]))
    assert work_once(s.factory)


def test_actual_offer_expiry_without_mutating_immutable_terms(scenario,monkeypatch):
    from datetime import timedelta
    from app.participation import service
    s=scenario.build();subject,id=s.person(1);a=s.apply(subject);s.approve(a);o=s.offer(a,expires_in_hours=1)
    clock=service.now();monkeypatch.setattr(service,'now',lambda:clock+timedelta(hours=2))
    state=s.client.get('/v1/events/'+s.id+'/participation/me',headers=s.headers(subject)).json()['data'];assert state['assignments'][0]['status']=='assignment_expired'
    s.call('/assignments/'+o['id']+'/accept',{'terms_key':o['terms_key']},subject,expected=409)

def test_resource_advice_stales_after_receipt_and_invalid_delivery_date_is_422(scenario,app):
    s=scenario.build(resource=True);subject,id=s.person(1)
    s.call('/support-offers/draft',{'resource_id':s.resource,'support_type':'materials','description':'Books','quantity':3,'unit':'books','delivery_date':'2026-99-99'},subject,expected=422)
    class ResourceAdapter:
        model_profile='test-resource-advice-not-live'
        live_provider=False
        def propose(self,r):
            c=r.authoritative_current['participation_and_resources']
            assert c['resources'][0]['on_hand']==0 and c['published_plan_id']==s.plan
            return {'resource_advice':[{'resource_id':s.resource,'explanation':'Obtain verified workbook receipts before reservation','unknowns':['Supplier availability']} ]}
    app.state.planning_adapter=ResourceAdapter();run=s.call('/resource-assessments',{},expected=202)
    assert work_ai_once(s.factory,app.state.planning_adapter)
    p=s.client.get('/v1/ai-runs/'+run['run_id'],headers=s.headers()).json()['data']['proposal']
    s.call('/resource-receipts',{'resource_id':s.resource,'quantity':2,'unit':'books','reference':'new-stock','evidence_reference':'Human receipt record'})
    s.call('/resource-proposals/'+p['id']+'/review',{'decision':'accept','reviewed_digest':p['digest']},expected=409)
    assert s.client.get('/v1/events/'+s.id+'/resources',headers=s.headers()).json()['data']['resources'][0]['on_hand']==2


def test_stale_ai_assessment_remains_readable_after_unpublished_plan_change(scenario,app):
    s=scenario.build();subject,id=s.person(1);a=s.apply(subject)
    app.state.planning_adapter=Advisory();s.call('/participation-assessments',{'application_id':a},expected=202)
    assert work_ai_once(s.factory,app.state.planning_adapter)
    s.flow.call('/planning/items/work/'+s.work,{'title':'Changed reading session'},method='PATCH');s.flow.confirm('work')
    state=s.client.get('/v1/events/'+s.id+'/organizer/participants',headers=s.headers())
    assert state.status_code==200,state.text
    assert state.json()['data']['applications'][0]['intelligence']['status']=='stale'
