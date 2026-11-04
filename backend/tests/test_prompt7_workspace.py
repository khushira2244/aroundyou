import json
from copy import deepcopy
import httpx,pytest
from sqlalchemy import select
from tests.test_group3 import scenario
from app.events.models import Event
from app.planning.models import PlanVersion
from app.memory.modal_adapter import ModalHTTPExtractor,MODEL,REVISION
from app.memory.ports import ExtractionInput
from app.memory.schemas import SourceRef
from app.shared.source_resolver import ResolvedSource
from app.api.errors import DomainError

def confirmed(s,subject=None,category='other'):
    issue=s.call('/issues',{'work_id':s.work,'category':category,'description':'Operational availability changes; no personal explanation required','severity':'delayed','can_continue':True},subject or 'owner-subject')['blocker']
    s.call('/recovery/issues/'+issue['id']+'/confirm',{'expected_revision':issue['revision'],'reason':'Human checked exact operational constraint'})
    return issue

def test_adaptive_private_issue_counts_and_no_automatic_blocker(scenario):
    s=scenario.build(3,resource=True);people=[]
    for n in (1,2):
        subject,pid=s.person(n);a=s.apply(subject);s.approve(a);o=s.offer(a);s.call('/assignments/'+o['id']+'/accept',{'terms_key':o['terms_key']},subject);people.append(subject)
    issue=s.call('/issues',{'work_id':s.work,'category':'personal_unavailability','description':'Unavailable for the final thirty minutes','can_continue':True},people[0])['blocker']
    assert issue['blocking'] is False and not issue['protective_hold']
    visible=s.client.get('/v1/events/'+s.id+'/execution',headers=s.headers(people[1])).json()['data'];assert issue['id'] not in [x['id'] for x in visible['blockers']]
    s.call('/issues',{'work_id':s.work,'category':'resource_missing','resource_ids':[s.resource],'resource_count':{'resource_id':s.resource,'required':10,'available':4,'unit':'boxes','source':'Reported manual count'},'description':'Insufficient workbooks for planned session'},people[0],expected=409)
    result=s.call('/issues',{'work_id':s.work,'category':'resource_missing','resource_ids':[s.resource],'resource_count':{'resource_id':s.resource,'required':10,'available':4,'unit':'books','source':'Participant manual count, not verified stock'},'description':'Insufficient workbooks for planned session'},people[0])['blocker'];assert result['resource_count']['available']==4
    s.call('/issues/'+issue['id']+'/review',{'expected_revision':issue['revision'],'state':'nonblocking','note':'Only an operational update'},expected=200)

def test_local_review_restore_communication_atomic_approval_and_consent(scenario):
    s=scenario.build(1,resource=True);subject,pid=s.person(1);a=s.apply(subject);s.approve(a);offer=s.offer(a);s.call('/assignments/'+offer['id']+'/accept',{'terms_key':offer['terms_key']},subject)
    s.call('/resource-receipts',{'resource_id':s.resource,'quantity':10,'unit':'books','reference':'actual-test-receipt','evidence_reference':'Verified synthetic test accounting source'})
    issue=confirmed(s,subject)
    hub=s.call('/recovery/workspaces',{'issue_ids':[issue['id']],'expected_plan_id':s.plan})
    assert all(n['status']=='needs_review' for n in hub['nodes'])
    old=hub['revision'];work=next(n for n in hub['nodes'] if n['key']=='work:'+s.work)
    schedule={**work['original']['schedule'],'start_minute':570,'end_minute':690}
    for node in hub['nodes']:
        patch={'schedule':schedule} if node['key'].startswith('work:') else {'purpose':'Reviewed preparation conditions'} if node['key'].startswith('stage:') else {}
        hub=s.call('/recovery/workspaces/'+hub['id']+'/local-review',{'expected_revision':hub['revision'],'node_key':node['key'],'patch':patch,'status':'confirmed_local_change' if patch else 'reviewed_no_change','note':'Reviewed exact local proposed values'})
    s.call('/recovery/workspaces/'+hub['id']+'/local-review',{'expected_revision':old,'node_key':work['key'],'patch':{},'status':'reviewed_no_change','note':'Stale edit rejected'},expected=409)
    restored=s.client.get('/v1/events/'+s.id+'/recovery/workspaces/'+hub['id'],headers=s.headers()).json()['data'];assert restored['reviews']==hub['reviews']
    with s.factory() as db:assert db.get(Event,s.id).active_plan_id==s.plan
    stranger,other=s.person(9)
    s.call('/recovery/workspaces/'+hub['id']+'/communication',{'expected_revision':hub['revision'],'mode':'targeted','invited_account_ids':[other]},expected=409)
    hub=s.call('/recovery/workspaces/'+hub['id']+'/communication',{'expected_revision':hub['revision'],'mode':'targeted','invited_account_ids':[pid]})
    inbox=s.client.get('/v1/notifications',headers=s.headers(subject)).json()['data']['items'];assert len(inbox)==1 and inbox[0]['workspace_id']==hub['id']
    assert s.client.get('/v1/notifications',headers=s.headers(stranger)).json()['data']['items']==[]
    result=s.call('/recovery/workspaces/'+hub['id']+'/submit',{'expected_revision':hub['revision'],'title':'Scoped local revisions','rationale':'Organizer reviewed stage, work, resource and actors independently'});p=result['alternative']
    approved=s.call('/recovery/alternatives/'+p['id']+'/review',{'expected_revision':p['revision'],'proposal_digest':p['proposal_digest'],'decision':'approve','rationale':'Approve exact before/after candidate'})
    command={'expected_revision':approved['revision'],'proposal_digest':p['proposal_digest']}
    assert s.call('/recovery/alternatives/'+p['id']+'/activate',command)['activated'] is False
    item=s.client.get('/v1/events/'+s.id+'/recovery/offers/me',headers=s.headers(subject)).json()['data']['items'][0]
    s.call('/recovery/alternatives/'+p['id']+'/assignments/'+offer['id']+'/consent',{'terms_key':item['terms_key'],'decision':'accept'},subject)
    activated=s.call('/recovery/alternatives/'+p['id']+'/activate',command);assert activated['activated']
    with s.factory() as db:
        new=db.get(PlanVersion,activated['plan_id']);oldplan=db.get(PlanVersion,s.plan);assert oldplan.content['resources']==new.content['resources'];assert oldplan.content['work'][0]['schedule']!=new.content['work'][0]['schedule']
    s.call('/recovery/alternatives/'+p['id']+'/outcome',{'expected_revision':approved['revision']+1,'outcome':'successful','criteria':'Must have independent accepted reports','report_ids':['missing']},expected=409)

def test_scoped_patches_deny_unaffected_and_inventory_fields(scenario):
    s=scenario.build(resource=True);issue=confirmed(s);hub=s.call('/recovery/workspaces',{'issue_ids':[issue['id']],'expected_plan_id':s.plan})
    s.call('/recovery/workspaces/'+hub['id']+'/local-review',{'expected_revision':hub['revision'],'node_key':'work:does-not-exist','patch':{},'status':'reviewed_no_change','note':'Unknown nodes rejected'},expected=409)
    s.call('/recovery/workspaces/'+hub['id']+'/local-review',{'expected_revision':hub['revision'],'node_key':'resource:'+s.resource,'patch':{'available':1000},'status':'confirmed_local_change','note':'Cannot credit stock in plan editor'},expected=409)

def source(kind='real'):
    ref=SourceRef(source_kind='execution',source_id='outcome-id',source_revision=1,source_digest='a'*64)
    record={'category':'Education','outcome':'mixed','actions_attempted':['work:w1'],'changed_work_ids':['w1'],'data_class':kind}
    return ResolvedSource(ref,json.dumps({'kind':'recovery.outcome','source_record':{'record':record}}),'private','verified','mixed','Human checked independent source',{'category':'Education'})

def test_modal_adapter_minimized_contract_and_hallucination_denial():
    sent=[]
    def handler(request):
        body=json.loads(request.content);sent.append(body);assert 'reports' not in request.content.decode() and 'criteria' not in request.content.decode()
        return httpx.Response(200,json={'model':MODEL,'revision':REVISION,'output':{'lessons':[{'source_id':'outcome-id','title':'Outcome source excerpt','excerpt':'"outcome": "mixed"'}]}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        adapter=ModalHTTPExtractor('https://example.modal.run','fake-key','fake-secret',client)
        out=adapter.extract(ExtractionInput('event',(source(),)));assert out[0].assertions[0].outcome=='mixed' and len(sent)==1
        with pytest.raises(DomainError,match='synthetic_memory'):adapter.extract(ExtractionInput('event',(source('synthetic'),)))
    with pytest.raises(ValueError):ModalHTTPExtractor('http://localhost:123','x','y')

def test_synthetic_events_cannot_be_classified_real(scenario):
    s=scenario.build()
    with s.factory.begin() as db:
        e=db.get(Event,s.id);e.memory_data_class='synthetic'
    s.call('/memory/data-class',{'data_class':'real','reason':'Attempt to promote synthetic test'},expected=422)

def test_persisted_multi_stage_scope_preserves_unrelated_work(scenario):
    s=scenario;f=s.flow;f.new('Selective graph verification');f.create();f.call('/planning/draft',{})
    a=f.call('/planning/items/stages',{'title':'Prepare','relative_start':1,'relative_end':1},expected=201)['id']
    b=f.call('/planning/items/stages',{'title':'Teach','relative_start':2,'relative_end':2,'dependency_ids':[a]},expected=201)['id']
    c=f.call('/planning/items/stages',{'title':'Unrelated outreach','relative_start':1,'relative_end':1},expected=201)['id'];f.confirm('stage')
    ids=[]
    for sid,day,title in [(a,1,'Prepare room'),(b,2,'Teaching'),(c,1,'Independent outreach')]:
        ids.append(f.call('/planning/items/work',{'stage_id':sid,'title':title,'effort':{'value':2,'unit':'person_hours'},'schedule':{'start_day':day,'end_day':day,'start_minute':540,'end_minute':660,'timezone':'Asia/Kolkata'}},expected=201)['id'])
    f.confirm('work');f.call('/planning/actor-derivations',{});f.confirm('actor');f.call('/setup/draft',{});f.call('/setup/sections/participation',{'data':{'visibility':'public','approval_required':True,'registration_open':True,'show_open_roles':True,'allow_groups':False}},method='PATCH');setup=f.get('/setup').json()['data'];s.plan=setup['plan_id'];fid=f.call('/finalizations',{'confirm_review':True,'expected_setup_version':setup['configuration']['revision'],'expected_plan_id':s.plan})['finalization_id'];f.call('/publications',{'finalization_id':fid});s.work=ids[0]
    issue=confirmed(s);scope=s.call('/recovery/impact',{'issue_ids':[issue['id']],'expected_plan_id':s.plan})['scope'];assert set(scope['affected_work_ids'])==set(ids[:2]);assert next(n for n in scope['work'] if n['work_id']==ids[2])['classification']=='unaffected'
    p=s.call('/recovery/alternatives',{'issue_ids':[issue['id']],'expected_plan_id':s.plan,'title':'Revise affected work instructions','rationale':'Do not touch unrelated outreach','patches':{'work:'+ids[0]:{'scope':'Revised bounded setup instructions'}}})
    with s.factory() as db:
        original=db.get(PlanVersion,s.plan).content;candidate=db.get(PlanVersion,p['candidate_plan_id']).content
        assert next(w for w in original['work'] if w['id']==ids[2])==next(w for w in candidate['work'] if w['id']==ids[2])
        assert db.get(Event,s.id).active_plan_id==s.plan

def test_memory_cross_event_reuse_requires_dual_permission(seeded,factory):
    from app.memory.service import store_candidate,review
    from app.memory.retrieval import retrieve
    from app.memory.schemas import Candidate,Assertion,Applicability,ReviewRequest
    from app.access.models import EventGrant
    with factory.begin() as db:
        event=db.get(Event,seeded['event']);event.memory_data_class='real'
        candidate=Candidate(kind='lesson',title='Offline test source-linked lesson',assertions=[Assertion(assertion_id='quoted',text='Reading workshop requires two available projectors',claim_kind='lesson',source_refs=[SourceRef.model_validate(seeded['ref'])])],applicability=Applicability(category='Education',conditions=['indoor']))
        entry=store_candidate(db,seeded['owner'],event.id,candidate,'model',model_profile='offline-test-only');review(db,seeded['owner'],event.id,entry.id,ReviewRequest(decision='publish',reviewed_digest=entry.digest,expected_revision=entry.revision),'test-publish',str(entry.version));mid=entry.id
    with factory.begin() as db:
        assert retrieve(db,seeded['outsider'],seeded['other'],include_reusable=True,category='Education')['items']==[]
        db.add_all([EventGrant(event_id=seeded['other'],user_id=seeded['owner'],permission=p,scope={}) for p in ('event:read','memory:read')]);db.flush()
        assert retrieve(db,seeded['owner'],seeded['other'],include_reusable=False)['items']==[]
        result=retrieve(db,seeded['owner'],seeded['other'],include_reusable=True,category='Education',conditions=['indoor']);assert result['items'][0]['memory_id']==mid
        assert retrieve(db,seeded['owner'],seeded['other'],include_reusable=True,category='Health')['items']==[]
        event=db.get(Event,seeded['event']);event.memory_data_class='synthetic';db.flush();assert retrieve(db,seeded['owner'],seeded['other'],include_reusable=True)['items']==[]

def test_issue_attachment_grants_only_linked_original_not_draft_report(scenario,app,tmp_path):
    from app.execution.storage import LocalPrivateStorage
    from tests.test_prompt56_media import attach
    s=scenario.build();subject,pid=s.person(1);a=s.apply(subject);s.approve(a);o=s.offer(a);s.call('/assignments/'+o['id']+'/accept',{'terms_key':o['terms_key']},subject);s.subject=subject
    app.state.evidence_storage=LocalPrivateStorage(tmp_path)
    r=s.call('/reports/draft',{'work_id':s.work,'body':'Private unrelated draft details'},subject)['report']
    raw=b'%PDF-1.7 Explicit issue source';asset,_=attach(s,r,raw,'document','application/pdf','source.pdf')
    path='/v1/events/'+s.id+'/evidence/'+asset['id']+'/content';assert s.client.get(path,headers=s.headers()).status_code==404
    s.call('/issues',{'work_id':s.work,'description':'Operational issue with optional document','evidence_ids':[asset['id']]},subject)
    assert s.client.get(path,headers=s.headers()).content==raw
    assert s.client.get('/v1/events/'+s.id+'/reports/'+r['id']+'/revisions',headers=s.headers()).status_code==404
