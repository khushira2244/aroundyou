import pytest
from tests.test_group3 import scenario
from app.events.models import Event
from app.planning.models import PlanVersion
from app.participation.models import AssignmentTerms

def alternative(s):
    issue=s.call('/issues',{'work_id':s.work,'description':'Workshop room temporarily inaccessible','severity':'impossible'})['blocker']
    s.call('/recovery/issues/'+issue['id']+'/confirm',{'expected_revision':issue['revision'],'reason':'Organizer checked delayed venue access'})
    return s.call('/recovery/alternatives',{'issue_ids':[issue['id']],'expected_plan_id':s.plan,'title':'Delay session thirty minutes','rationale':'Allow room preparation before learners arrive','schedules':{s.work:{'start_day':1,'end_day':1,'start_minute':570,'end_minute':690,'timezone':'Asia/Kolkata'}}})

def test_recovery_exact_consent_atomic_activation(scenario):
    s=scenario.build();subject,aid=s.person(1);a=s.apply(subject);s.approve(a);offer=s.offer(a);s.call('/assignments/'+offer['id']+'/accept',{'terms_key':offer['terms_key']},subject)
    proposal=alternative(s)
    assert proposal['validation']['status']=='conditional'
    selected=s.call('/recovery/alternatives/'+proposal['id']+'/review',{'expected_revision':proposal['revision'],'proposal_digest':proposal['proposal_digest'],'decision':'approve','rationale':'Reviewed exact changed session time'})
    command={'expected_revision':selected['revision'],'proposal_digest':selected['proposal_digest']}
    assert s.call('/recovery/alternatives/'+selected['id']+'/activate',command)['status']=='deferred'
    offers=s.client.get('/v1/events/'+s.id+'/recovery/offers/me',headers=s.headers(subject)).json()['data']['items'];assert len(offers)==1
    s.call('/recovery/alternatives/'+selected['id']+'/assignments/'+offer['id']+'/consent',{'terms_key':offers[0]['terms_key'],'decision':'accept'},subject)
    result=s.call('/recovery/alternatives/'+selected['id']+'/activate',command);assert result['activated']
    with s.factory() as db:
        e=db.get(Event,s.id);assert e.active_plan_id==result['plan_id'] and db.get(PlanVersion,s.plan)
    workspace=s.client.get('/v1/events/'+s.id+'/participation/me',headers=s.headers(subject)).json()['data'];assert workspace['assignments'][0]['status']=='assignment_accepted'
    s.call('/recovery/alternatives/'+selected['id']+'/activate',command,expected=409)

def test_recovery_decline_does_not_change_original_plan(scenario):
    s=scenario.build();subject,aid=s.person(1);a=s.apply(subject);s.approve(a);offer=s.offer(a);s.call('/assignments/'+offer['id']+'/accept',{'terms_key':offer['terms_key']},subject)
    p=alternative(s);selected=s.call('/recovery/alternatives/'+p['id']+'/review',{'expected_revision':p['revision'],'proposal_digest':p['proposal_digest'],'decision':'approve','rationale':'Select subject to exact consent'})
    item=s.client.get('/v1/events/'+s.id+'/recovery/offers/me',headers=s.headers(subject)).json()['data']['items'][0]
    s.call('/recovery/alternatives/'+p['id']+'/assignments/'+offer['id']+'/consent',{'terms_key':item['terms_key'],'decision':'decline'},subject)
    result=s.call('/recovery/alternatives/'+p['id']+'/activate',{'expected_revision':selected['revision'],'proposal_digest':p['proposal_digest']});assert not result['activated']
    with s.factory() as db:assert db.get(Event,s.id).active_plan_id==s.plan


def test_hold_no_capacity_and_rejected_history(scenario):
    s=scenario.build();p=alternative(s)
    assert p['validation']['status']=='conditional' and any('capacity' in c for c in p['validation']['conditions'])
    rejected=s.call('/recovery/alternatives/'+p['id']+'/review',{'expected_revision':p['revision'],'proposal_digest':p['proposal_digest'],'decision':'reject','rationale':'No committed available staff'})
    assert rejected['status']=='rejected' and rejected['outcome']=='inconclusive'
    s.call('/recovery/alternatives/'+p['id']+'/activate',{'expected_revision':rejected['revision'],'proposal_digest':p['proposal_digest']},expected=409)

def test_stale_sources_block_review(scenario):
    s=scenario.build();p=alternative(s)
    issue=s.client.get('/v1/events/'+s.id+'/execution',headers=s.headers()).json()['data']['blockers'][0]
    s.call('/issues/'+issue['id']+'/review',{'expected_revision':issue['revision'],'state':'acknowledged','note':'Condition needs another investigation'})
    s.call('/recovery/alternatives/'+p['id']+'/review',{'expected_revision':p['revision'],'proposal_digest':p['proposal_digest'],'decision':'approve','rationale':'Old review'},expected=409)

def test_recovery_provider_unavailable_does_not_fabricate(scenario):
    s=scenario.build();s.call('/recovery/ai-runs',{'issue_id':'unknown','message':'Suggest a repair'},expected=503)


def test_nonlive_recovery_worker_typed_proposal_only(scenario,app):
    from app.ai.service import work_ai_once
    from app.ai.models import AIRun,AIProposal
    s=scenario.build();p=alternative(s);iid=p['issue_ids'][0]
    class Adapter:
        model_profile='non-live-recovery-test'
        def propose(self,request):
            assert request.kind=='recovery' and request.cited_historical_memory['memory']['policy_version']=='event-only-v1'
            return {'alternatives':[{'title':'Wait for access','rationale':'Delay the unavailable session','schedules':{},'assumptions':['Venue may reopen'],'risks':['Reopening uncertain'],'unknowns':['Confirmed reopening time'],'conditions':['Organizer verification'],'cited_issue_ids':[iid]}],'questions':['When can the venue reopen?']}
    app.state.planning_adapter=Adapter()
    run=s.call('/recovery/ai-runs',{'issue_id':iid,'message':'Consider a delay'})
    assert work_ai_once(s.factory,Adapter()) is True
    with s.factory() as db:
        row=db.get(AIRun,run['run_id']);assert row.status=='succeeded'
        proposal=db.get(AIProposal,row.proposal_id);assert proposal.status=='pending'
        assert db.get(Event,s.id).active_plan_id==s.plan


def ready_alternative(s):
    subject,aid=s.person(4);a=s.apply(subject);s.approve(a);offer=s.offer(a);s.call('/assignments/'+offer['id']+'/accept',{'terms_key':offer['terms_key']},subject)
    p=alternative(s);selected=s.call('/recovery/alternatives/'+p['id']+'/review',{'expected_revision':p['revision'],'proposal_digest':p['proposal_digest'],'decision':'approve','rationale':'Reviewed'})
    item=s.client.get('/v1/events/'+s.id+'/recovery/offers/me',headers=s.headers(subject)).json()['data']['items'][0]
    s.call('/recovery/alternatives/'+p['id']+'/assignments/'+offer['id']+'/consent',{'terms_key':item['terms_key'],'decision':'accept'},subject)
    return selected

def test_concurrent_activation_one_commit(scenario):
    from concurrent.futures import ThreadPoolExecutor
    import uuid
    s=scenario.build();p=ready_alternative(s)
    version=s.client.get('/v1/events/'+s.id,headers=s.headers()).json()['data']['version']
    def activate(_):return s.client.post('/v1/events/'+s.id+'/recovery/alternatives/'+p['id']+'/activate',json={'expected_revision':p['revision'],'proposal_digest':p['proposal_digest']},headers=s.headers(key=uuid.uuid4().hex,version=str(version))).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(activate,range(2)))==[200,409]

def test_activation_rollback_preserves_publication_and_terms(scenario,monkeypatch):
    from app.recovery import lifecycle
    from app.api.errors import DomainError
    from app.participation.models import Assignment
    s=scenario.build();p=ready_alternative(s)
    with s.factory() as db:
        e=db.get(Event,s.id);before=(e.active_plan_id,e.current_publication_id);terms=[a.current_terms_id for a in db.query(Assignment).filter_by(event_id=s.id)]
    def failed_record(*args,**kwargs):raise DomainError('forced_rollback','Test transaction rollback')
    monkeypatch.setattr(lifecycle,'record',failed_record)
    s.call('/recovery/alternatives/'+p['id']+'/activate',{'expected_revision':p['revision'],'proposal_digest':p['proposal_digest']},expected=409)
    with s.factory() as db:
        e=db.get(Event,s.id);assert (e.active_plan_id,e.current_publication_id)==before
        assert [a.current_terms_id for a in db.query(Assignment).filter_by(event_id=s.id)]==terms
