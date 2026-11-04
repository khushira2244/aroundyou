from copy import deepcopy
from sqlalchemy import select
from tests.test_group2 import flow
from tests.test_prompt3_planning import ScopedMuse,ready,propose,apply
from app.ai.models import AIRun

class StageMuse(ScopedMuse):
    stage_scope_required=True
    def propose(self,r):
        if r.kind=='stages':return super().propose(r)
        self.calls.append(r)
        c=r.authoritative_current;s=c['selected_stage'];sid=s['id']
        assert len(c['planning_draft']['stages'])==1
        assert all(w['stage_id']==sid for w in c['planning_draft']['work'])
        assert c['plan'] is None and 'unconfirmed_planning_draft' not in c['reported_operating_context']
        if r.kind=='work':return {'work':[{'title':'Stage-specific facilitation','objective':'Facilitate selected stage','outcome':'Record stage outcome','schedule':{'start_day':s['relative_start'],'end_day':s['relative_start'],'start_minute':540,'end_minute':660,'timezone':'Asia/Kolkata'},'effort_person_hours':4,'skills':['Facilitation'],'evidence':['Organizer reviewed notes']}],'message':'One-stage work only'}
        if r.kind=='actors':return {'roles':[{'title':'Stage facilitator','work_ids':[w['id'] for w in c['planning_draft']['work']],'headcount':2,'basis':'Four person hours in two hours; skill feasibility unverified','capabilities':['Facilitation']}],'message':'Demand only'}
        return {'message':'This selected stage needs facilitation; no availability is established.','proposed_stages':None}

def scoped(flow,path,stage):
    run=flow.call('/planning/'+path,{'stage_id':stage},expected=202)
    data=flow.client.get('/v1/ai-runs/'+run['run_id'],headers=flow.headers()).json()['data']
    assert data['status']=='succeeded',data
    return data['proposal']

def confirm_stage(flow,kind,sid):
    flow.call('/planning/'+kind+'-confirmations',{'stage_id':sid,'expected_draft_version':flow.planning()['draft_version']})

def test_saved_original_context_supports_work_actors_and_chat_without_interpretation(flow,app):
    flow.new();flow.create();flow.call('/planning/draft',{})
    sid=flow.call('/planning/items/stages',{'title':'Reading preparation'},expected=201)['id']
    flow.confirm('stage');app.state.planning_adapter=StageMuse()
    pending=scoped(flow,'work-proposals',sid)
    assert not flow.planning()['planning']['work']
    wid=pending['preview_plan']['work'][0]['id']
    edited=flow.call('/planning/work-edits',{'work_id':wid,'base_proposal_id':pending['id'],'patch':{'title':'Review room access'}})['proposal']
    assert not flow.planning()['planning']['work']
    apply(flow,edited);confirm_stage(flow,'work',sid)
    assert scoped(flow,'actor-proposals',sid)['preview_plan']['roles']
    assert scoped(flow,'conversations',sid)['advisory_only']

def test_independent_stage_work_actor_confirmations_and_saved_chat(flow,app):
    ready(flow,app);adapter=StageMuse();app.state.planning_adapter=adapter
    apply(flow,propose(flow,'stage-proposals'));flow.confirm('stage')
    flow.call('/planning/work-proposals',{},expected=422)
    flow.call('/planning/work-proposals',{'stage_id':'foreign-stage'},expected=422)
    flow.call('/planning/actor-proposals',{'stage_id':'S1'},expected=422)
    for sid in ['S1','S2']:
        apply(flow,scoped(flow,'work-proposals',sid));confirm_stage(flow,'work',sid)
        apply(flow,scoped(flow,'actor-proposals',sid));confirm_stage(flow,'actor',sid)
        if sid=='S1':first=deepcopy(flow.planning()['planning']);assert not first['work_confirmed']
    state=flow.planning()['planning']
    assert state['work_confirmed_stage_ids']==['S1','S2'] and state['actor_confirmed_stage_ids']==['S1','S2']
    assert all(state['work'][k]==v for k,v in first['work'].items())
    assert all(state['roles'][k]==v for k,v in first['roles'].items())
    p=scoped(flow,'conversations','S2');assert p['advisory_only'] and p['stage_id']=='S2'
    calls=len(adapter.calls)
    for _ in range(3):assert flow.planning()['planning']==state
    assert len(adapter.calls)==calls
    # Editing one stage's work invalidates only its review fingerprint and roles.
    wid=next(k for k,w in state['work'].items() if w['stage_id']=='S2')
    flow.call('/planning/items/work/'+wid,{'title':'Human revised selected work'},method='PATCH')
    final=flow.planning()['planning']
    assert final['work_confirmed_stage_ids']==['S1'] and final['actor_confirmed_stage_ids']==['S1']
    assert all(final['roles'][k]==v for k,v in first['roles'].items())

def test_invalid_stage_model_schedule_and_cross_stage_actor_links_fail_closed(flow,app):
    ready(flow,app);adapter=StageMuse();app.state.planning_adapter=adapter
    apply(flow,propose(flow,'stage-proposals'));flow.confirm('stage')
    original=adapter.propose
    def bad(r):
        result=original(r)
        if r.kind=='work':result['work'][0]['schedule']['start_day']=1;result['work'][0]['schedule']['end_day']=1
        return result
    adapter.propose=bad
    run=flow.call('/planning/work-proposals',{'stage_id':'S2'},expected=202)
    data=flow.client.get('/v1/ai-runs/'+run['run_id'],headers=flow.headers()).json()['data']
    assert data['status']=='failed' and data['error']['code']=='stale_work'
    assert not flow.planning()['planning']['work']

    adapter.propose=original
    apply(flow,scoped(flow,'work-proposals','S2'));confirm_stage(flow,'work','S2')
    saved=deepcopy(flow.planning()['planning'])
    def bad_actor(r):
        result=original(r)
        if r.kind=='actors':result['roles'][0]['work_ids']=['foreign-work']
        return result
    adapter.propose=bad_actor
    run=flow.call('/planning/actor-proposals',{'stage_id':'S2'},expected=202)
    data=flow.client.get('/v1/ai-runs/'+run['run_id'],headers=flow.headers()).json()['data']
    assert data['status']=='failed' and data['error']['code']=='scope_violation'
    assert flow.planning()['planning']==saved
