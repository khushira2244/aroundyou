from copy import deepcopy
import pytest
from sqlalchemy import select,func
from tests.test_group2 import flow,FORM
from app.ai.models import AIRun,AIProposal
from app.planning.schemas import Stage,Work,WorkGroup,ActorRequirement,Schedule,PlanContent
from app.planning.models import PlanVersion
from app.planning.intelligence import validate,marked

class ScopedMuse:
    stage_scope_required=False # Legacy whole-plan regression adapter, never used in HTTP runtime.
    live_provider=True
    scoped_planning=True
    accepted_kinds=('stages','work','actors','planning_chat')
    model_profile='offline-scoped-test-only'
    def __init__(self):self.calls=[]
    def propose(self,r):
        self.calls.append(r)
        assert r.authoritative_current['confirmed_context']
        if r.kind=='stages':
            pending=r.authoritative_current.get('pending_human_stage_edit')
            stages=deepcopy(pending['plan']['stages']) if pending else [Stage(id='S'+str(i),title=t,relative_start=i,relative_end=i,dependency_ids=['S'+str(i-1)] if i>1 else []).model_dump() for i,t in enumerate(['Venue preparation','Reading sessions','Feedback review'],1)]
            for i,s in enumerate(stages):
                if i:s['relative_start']=max(s['relative_start'],stages[i-1]['relative_end']+1);s['relative_end']=s['relative_start']
            return {'stages':stages,'message':'Offline stage proposal; capacity unverified.'}
        base=r.authoritative_current['planning_draft']
        if r.kind=='work':
            return {'work':[Work(id='W'+str(i),stage_id=s['id'],work_group_id='G'+str(i),title=s['title']+' work',schedule=Schedule(start_day=s['relative_start'],end_day=s['relative_start']),skills=['Facilitation'],effort={'value':4,'unit':'person_hours'},duration={'value':2,'unit':'hours'}).model_dump() for i,s in enumerate(base['stages'],1)],'groups':[WorkGroup(id='G'+str(i),stage_id=s['id'],title=s['title']).model_dump() for i,s in enumerate(base['stages'],1)],'message':'Offline work design'}
        if r.kind=='actors':
            return {'roles':[ActorRequirement(id='R'+str(i),title='Workshop facilitator '+str(i),stage_ids=[w['stage_id']],work_ids=[w['id']],source_work_ids=[w['id']],schedule_intervals=[w['schedule']],proposed_headcount=2,headcount_basis='Four person-hours in a two-hour window; skills unverified',required_capabilities=w['skills'],effort_person_hours=4).model_dump() for i,w in enumerate(base['work'],1)],'message':'Offline demand recommendations, no assignments'}
        return {'message':'The reading event needs venue preparation before the sessions. Capacity is unverified.','proposed_stages':None}

def ready(flow,app):
    flow.new();ctx=flow.get('/creation').json()['data']['context']
    flow.call('/context-interpretations',{'context_version':ctx['version'],'interpretation':{'scope':['Reading workshop'],'unknowns':['Venue permission']}});flow.create();flow.call('/planning/draft',{})
    adapter=ScopedMuse();app.state.planning_adapter=adapter;return adapter

def propose(flow,path):
    run=flow.call('/planning/'+path,{},expected=202)
    result=flow.client.get('/v1/ai-runs/'+run['run_id'],headers=flow.headers()).json()['data']
    assert result['status']=='succeeded',result
    return result['proposal']

def apply(flow,p):return flow.call('/planning/proposals/'+p['id']+'/apply',{'reviewed_digest':p['digest']})

def test_complete_scoped_workflow_and_saved_chat_without_calls(flow,app,factory):
    adapter=ready(flow,app);p=propose(flow,'stage-proposals');assert flow.planning()['planning']['stages']=={}
    apply(flow,p);flow.confirm('stage');saved=flow.planning()['planning']['stages'];assert len(saved)==3
    for _ in range(3):assert flow.planning()['planning']['stages']==saved
    assert len(adapter.calls)==1
    work=propose(flow,'work-proposals');apply(flow,work);flow.confirm('work')
    actors=propose(flow,'actor-proposals');assert not flow.planning()['planning']['roles'];apply(flow,actors);flow.confirm('actor')
    state=flow.planning();assert state['planning']['actors_confirmed'] and len(state['planning']['roles'])==3
    p=propose(flow,'conversations');assert p['advisory_only'] is True
    flow.call('/planning/proposals/'+p['id']+'/apply',{'reviewed_digest':p['digest']},expected=422)
    count=len(adapter.calls);assert any(p['kind']=='planning_chat' for p in flow.planning()['proposals']);assert len(adapter.calls)==count
    with factory() as db:assert db.scalar(select(func.count()).select_from(PlanVersion).where(PlanVersion.event_id==flow.id))==3

def test_manual_impact_then_explicit_ai_recalculation(flow,app):
    adapter=ready(flow,app);apply(flow,propose(flow,'stage-proposals'));flow.confirm('stage')
    before=flow.planning()['planning']['stages'];count=len(adapter.calls)
    edit=flow.call('/planning/stage-edits',{'stage_id':'S1','start_day':2,'duration_days':1})
    assert set(edit['impact']['affected_stage_ids'])=={'S1','S2','S3'} and edit['impact']['violations']
    assert flow.planning()['planning']['stages']==before and len(adapter.calls)==count
    flow.call('/planning/proposals/'+edit['proposal']['id']+'/apply',{'reviewed_digest':edit['proposal']['digest']},expected=422)
    p=propose(flow,'stage-proposals');apply(flow,p);flow.confirm('stage')
    assert [s['relative_start'] for s in flow.planning()['planning']['stages'].values()]==[2,3,4]
    assert len(adapter.calls)==count+1

def test_stage_move_never_rewrites_work_and_blocks_stale_confirmation(flow,app):
    ready(flow,app);apply(flow,propose(flow,'stage-proposals'));flow.confirm('stage');apply(flow,propose(flow,'work-proposals'));flow.confirm('work')
    before=flow.planning()['planning']['work'];edit=flow.call('/planning/stage-edits',{'stage_id':'S3','start_day':5,'duration_days':1})
    assert edit['impact']['stale_work_ids']==['W3'];apply(flow,edit['proposal']);flow.confirm('stage')
    state=flow.planning();assert state['planning']['work']==before and state['planning']['stale_work_ids']==['W3']
    flow.call('/planning/work-confirmations',{'expected_draft_version':state['draft_version']},expected=422)
    flow.call('/planning/actor-proposals',{},expected=422)

def test_pending_generated_stages_can_be_edited_without_applying(flow,app):
    ready(flow,app)
    original=propose(flow,'stage-proposals')
    assert not flow.planning()['planning']['stages']
    edited=flow.call('/planning/stage-edits',{'stage_id':'S3','start_day':4,'duration_days':2,'base_proposal_id':original['id']})['proposal']
    assert not flow.planning()['planning']['stages']
    assert edited['preview_plan']['stages'][-1]['relative_end']==5
    flow.call('/planning/stage-edits',{'stage_id':'S3','start_day':4,'duration_days':1,'base_proposal_id':original['id']},expected=409)
    apply(flow,edited)
    flow.confirm('stage')
    assert flow.planning()['planning']['stages']['S3']['relative_end']==5

def test_stage_preview_base_rejects_foreign_and_stale_proposals():
    from types import SimpleNamespace
    from app.planning.service import stage_edit_base,versions
    from app.api.errors import DomainError
    event=SimpleNamespace(id='e',version=2,active_context_revision_id='c',active_plan_id=None)
    draft=SimpleNamespace(content=PlanContent(stages=[Stage(id='s',title='Draft')]).model_dump(),version=1,stage_revision=1,work_revision=1)
    proposal=SimpleNamespace(event_id='other',kind='stages',status='pending',payload={'plan':draft.content},source_versions=versions(event,draft))
    session=SimpleNamespace(get=lambda *_:proposal)
    with pytest.raises(DomainError):stage_edit_base(session,event,draft,'p')
    proposal.event_id='e';proposal.source_versions={}
    with pytest.raises(DomainError):stage_edit_base(session,event,draft,'p')
    proposal.source_versions=versions(event,draft)
    copy=stage_edit_base(session,event,draft,'p');copy['stages'][0]['title']='Changed'
    assert draft.content['stages'][0]['title']=='Draft'

def test_pending_work_edits_preserve_stages_and_do_not_apply():
    from types import SimpleNamespace
    from app.planning.service import work_edit_base,versions
    from app.api.errors import DomainError
    event=SimpleNamespace(id='e',version=2,active_context_revision_id='c',active_plan_id=None)
    draft=SimpleNamespace(content=PlanContent(stages=[Stage(id='s',title='Confirmed stage')]).model_dump(),version=1,stage_revision=1,work_revision=1)
    candidate=deepcopy(draft.content);candidate['work']=[Work(id='w',title='Preview work',stage_id='s').model_dump()]
    proposal=SimpleNamespace(event_id='e',kind='work',status='pending',payload={'plan':candidate},source_versions=versions(event,draft))
    session=SimpleNamespace(get=lambda *_:proposal)
    preview=work_edit_base(session,event,draft,'p');preview['work'][0]['title']='Edited'
    assert not draft.content['work'] and candidate['work'][0]['title']=='Preview work'
    candidate['stages'][0]['title']='Unapproved stage change'
    with pytest.raises(DomainError):work_edit_base(session,event,draft,'p')
    proposal.event_id='other'
    with pytest.raises(DomainError):work_edit_base(session,event,draft,'p')

def test_stale_stage_proposal_and_cross_event_auth(flow,app,headers):
    ready(flow,app);p=propose(flow,'stage-proposals');flow.call('/planning/items/stages',{'title':'Human stage'},expected=201)
    flow.call('/planning/proposals/'+p['id']+'/apply',{'reviewed_digest':p['digest']},expected=409)
    assert flow.client.post('/v1/events/'+flow.id+'/planning/conversations',json={'message':'Private?'},headers=headers('outsider-subject')).status_code==404

def test_explicit_stale_markers_cannot_mask_unrelated_invalidity():
    body=PlanContent(stages=[Stage(id='s',title='Stage',relative_start=2,relative_end=2)]).model_dump()
    body['work']=[Work(id='w',title='Work',stage_id='s').model_dump()]
    with pytest.raises(ValueError):PlanContent.model_validate(body)
    valid=PlanContent.model_validate(marked(body));assert valid.stale_work_ids==['w']
    body['work'][0]['dependency_ids']=['not-real']
    with pytest.raises(ValueError):PlanContent.model_validate(marked(body))

def test_model_schema_bounds_reference_strings_and_requires_explicit_schedule():
    from app.planning.intelligence import WorkAdvice
    work=Work(id='w1',title='Prepare',stage_id='s1').model_dump()
    work['zone_ids']=['avatar-context-zone-'*100]
    with pytest.raises(ValueError):WorkAdvice.model_validate({'work':[work],'message':'Invalid long reference'})
    work['zone_ids']=[];work.pop('schedule')
    with pytest.raises(ValueError):WorkAdvice.model_validate({'work':[work],'message':'Missing explicit schedule'})

def test_stage_generation_uses_saved_context_without_ai_understanding(flow,app):
    flow.new()
    flow.create()
    flow.call('/planning/draft',{})

    class SavedContextMuse(ScopedMuse):
        def propose(self,request):
            self.calls.append(request)
            assert request.authoritative_current['original_context']==FORM['executionIntent']
            assert request.authoritative_current['confirmed_context'] is None
            previous=request.authoritative_current.get('previous_pending_stage_proposal')
            if request.instruction.endswith('Rename the stage'):
                assert previous['plan']['stages'][0]['title']=='Preparation'
            return {'stages':[{'id':'S1','title':'Preparation','relative_start':1,'relative_end':1}],'message':'Offline stage proposal'}

    app.state.planning_adapter=SavedContextMuse()
    propose(flow,'stage-proposals')
    flow.call('/planning/stage-proposals',{'message':'Rename the stage'},expected=202)
    assert len(app.state.planning_adapter.calls)==2
    assert flow.planning()['planning']['stages']=={}

