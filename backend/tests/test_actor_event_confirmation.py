from copy import deepcopy
from types import SimpleNamespace
import pytest
from app.api.errors import DomainError
from app.planning.schemas import PlanContent,Stage,Work,Schedule,ActorRequirement
from app.planning.service import merge_actor_plans,confirm_event_actors,versions

def plans():
    base=PlanContent(stages=[Stage(id='s1',title='Setup'),Stage(id='s2',title='Close')],work=[Work(id='w1',stage_id='s1',title='Inspect'),Work(id='w2',stage_id='s2',title='Document')]).model_dump()
    candidates=[]
    for i in (1,2):
        plan=deepcopy(base)
        plan['roles']=[ActorRequirement(id=f'r{i}',title=f'Team {i}',stage_ids=[f's{i}'],work_ids=[f'w{i}'],source_work_ids=[f'w{i}'],proposed_headcount=i).model_dump()]
        candidates.append((f's{i}',plan))
    return base,candidates

def test_merges_all_stage_actors_without_rewriting_work_or_mutating_candidates():
    base,candidates=plans();before=deepcopy(candidates)
    merged=merge_actor_plans(base,candidates)
    assert {r['id'] for r in merged['roles']}=={'r1','r2'}
    assert merged['stages']==base['stages'] and not base['roles'] and candidates==before
    for actual,original in zip(merged['work'],base['work']):
        assert {k:v for k,v in actual.items() if k!='role_requirement_ids'}=={k:v for k,v in original.items() if k!='role_requirement_ids'}

def test_shared_actor_identity_is_merged_without_adding_people():
    base,candidates=plans()
    for _,plan in candidates:
        plan['roles'][0].update(id='shared',title='Shared team',proposed_headcount=3)
    merged=merge_actor_plans(base,candidates)
    assert len(merged['roles'])==1 and merged['roles'][0]['proposed_headcount']==3
    assert set(merged['roles'][0]['stage_ids'])=={'s1','s2'}
    assert set(merged['roles'][0]['source_work_ids'])=={'w1','w2'}
    candidates[1][1]['roles'][0]['proposed_headcount']=4
    with pytest.raises(DomainError,match='shared_actor_conflict'):merge_actor_plans(base,candidates)

def test_missing_stage_and_work_rewrites_fail_before_mutation():
    base,candidates=plans()
    with pytest.raises(DomainError):merge_actor_plans(base,candidates[:1])
    candidates[1][1]['work'][0]['title']='AI rewrote work'
    with pytest.raises(DomainError):merge_actor_plans(base,candidates)
    assert not base['roles']

def test_every_proposal_is_validated_before_any_application(monkeypatch):
    import app.planning.service as service
    base,candidates=plans()
    event=SimpleNamespace(id='e',version=1,active_context_revision_id='c',active_plan_id=None)
    draft=SimpleNamespace(content=base,work_confirmed=True,version=1,stage_revision=1,work_revision=1)
    proposals={f'p{i}':SimpleNamespace(id=f'p{i}',event_id='e',kind='actors',status='pending',digest=str(i)*64,source_versions=versions(event,draft),payload={'stage_id':scope,'plan':plan},run_id=None) for i,(scope,plan) in enumerate(candidates,1)}
    proposals['p2'].source_versions={}
    monkeypatch.setattr(service,'draft_for',lambda *_:draft)
    session=SimpleNamespace(get=lambda _,pid:proposals[pid])
    with pytest.raises(DomainError):confirm_event_actors(session,'owner',event,[{'proposal_id':p.id,'reviewed_digest':p.digest} for p in proposals.values()])
    assert event.version==1 and draft.content==base
    assert all(p.status=='pending' for p in proposals.values())

# PostgreSQL integration: all stage proposals share one source version until the single commit.
from tests.test_group2 import flow
from tests.test_prompt3_planning import ready,propose,apply
from tests.test_stage_scoped_planning import StageMuse,scoped,confirm_stage

def test_one_http_confirmation_commits_every_stage_and_rejects_partial_reviews(flow,app):
    ready(flow,app);app.state.planning_adapter=StageMuse()
    apply(flow,propose(flow,'stage-proposals'));flow.confirm('stage')
    for sid in ('S1','S2','S3'):
        apply(flow,scoped(flow,'work-proposals',sid));confirm_stage(flow,'work',sid)
    candidates=[scoped(flow,'actor-proposals',sid) for sid in ('S1','S2','S3')]
    before=flow.planning()
    reviews=[{'proposal_id':p['id'],'reviewed_digest':p['digest']} for p in candidates]
    invalid=deepcopy(reviews);invalid[-1]['reviewed_digest']='0'*64
    flow.call('/planning/actor-confirmations',{'expected_draft_version':before['draft_version'],'actor_proposals':invalid},expected=409)
    assert flow.planning()['planning']==before['planning']
    flow.call('/planning/actor-confirmations',{'expected_draft_version':before['draft_version'],'actor_proposals':reviews})
    final=flow.planning()
    assert final['planning']['actors_confirmed'] and len(final['planning']['roles'])==3
    assert final['planning']['actor_confirmed_stage_ids']==['S1','S2','S3']
    assert final['planning']['work']==before['planning']['work'] or all({k:v for k,v in w.items() if k!='role_requirement_ids'}=={k:v for k,v in before['planning']['work'][wid].items() if k!='role_requirement_ids'} for wid,w in final['planning']['work'].items())
