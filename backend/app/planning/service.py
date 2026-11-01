from copy import deepcopy
from math import ceil
from sqlalchemy import select
from app.planning.draft_models import PlanningDraft
from app.planning.schemas import PlanContent,Stage,Work,WorkGroup,Resource,Zone,ActorRequirement
from app.events.source_revisions import append_plan
from app.shared.types import uid,digest
from app.shared.audit import audit
from app.shared.models import ReviewDecision
from app.ai.models import AIProposal
from app.api.errors import DomainError

def draft_for(session,event,initialize=False):
    draft=session.scalar(select(PlanningDraft).where(PlanningDraft.event_id==event.id))
    if not draft and initialize:
        if event.lifecycle=='draft' or not event.active_context_revision_id:raise DomainError('invalid_state','Create the event with original context before planning')
        draft=PlanningDraft(id=uid(),event_id=event.id,context_revision_id=event.active_context_revision_id,content=PlanContent().model_dump())
        session.add(draft);session.flush()
    if not draft:raise DomainError('not_found','Open a planning draft first',404)
    return draft

def versions(event,draft=None):
    return {'event_version':event.version,'context_revision':event.active_context_revision_id,'active_plan_id':event.active_plan_id,'draft_version':draft.version if draft else None,'stage_revision':draft.stage_revision if draft else 0,'work_revision':draft.work_revision if draft else 0}

def store_content(session,actor,event,draft,content,level):
    if level in ('stages','work'):
        content=deepcopy(content);content['roles']=[]
        for w in content['work']:w['role_requirement_ids']=[]
    validated=PlanContent.model_validate(content).model_dump()
    from app.resources.invariants import guard_plan
    guard_plan(session,event,validated)
    previous={w['id']:w for w in draft.content['work']}
    for w in validated['work']:
        old=previous.get(w['id'])
        meaningful=lambda item:{k:v for k,v in item.items() if k not in ('revision','role_requirement_ids')}
        w['revision']=(old['revision']+(meaningful(w)!=meaningful(old))) if old else 1
    draft.content=validated;draft.version+=1;draft.context_revision_id=event.active_context_revision_id
    if level=='stages':draft.stage_revision+=1;draft.stage_confirmed=False;draft.work_confirmed=False
    if level in ('stages','work'):draft.work_revision+=1;draft.work_confirmed=False;draft.derived_from=None
    draft.actors_confirmed=False;event.current_finalization_id=None;event.version+=1
    if event.lifecycle!='draft':event.lifecycle='created_unpublished'
    audit(session,actor,event.id,'planning.edit.'+level,draft.id)
    return draft

def manual_add(session,actor,event,kind,payload):
    draft=draft_for(session,event,True);content=deepcopy(draft.content)
    spec={'stages':Stage,'work':Work,'groups':WorkGroup,'resources':Resource,'zones':Zone}
    if kind not in spec:raise DomainError('invalid_kind','Unsupported plan entity',422)
    item=spec[kind].model_validate({**payload,'id':uid()})
    content[kind].append(item.model_dump())
    store_content(session,actor,event,draft,content,'stages' if kind=='stages' else 'work')
    return {'id':item.id,'draft_version':draft.version}

def manual_update(session,actor,event,kind,item_id,payload):
    draft=draft_for(session,event);content=deepcopy(draft.content)
    if kind not in ('stages','work','groups','resources','zones'):raise DomainError('invalid_kind','Unsupported plan entity',422)
    target=next((x for x in content[kind] if x['id']==item_id),None)
    if not target:raise DomainError('not_found','Plan item not found',404)
    if 'id' in payload and payload['id']!=item_id:raise DomainError('invalid_id','Cannot replace a stable ID',422)
    target.update(payload)
    store_content(session,actor,event,draft,content,'stages' if kind=='stages' else 'work')
    return {'saved':True,'draft_version':draft.version}

def manual_delete(session,actor,event,kind,item_id):
    draft=draft_for(session,event);content=deepcopy(draft.content)
    if kind not in ('stages','work','groups','resources','zones'):raise DomainError('invalid_kind','Unsupported plan entity',422)
    if not any(x['id']==item_id for x in content[kind]):raise DomainError('not_found','Plan item not found',404)
    content[kind]=[x for x in content[kind] if x['id']!=item_id]
    store_content(session,actor,event,draft,content,'stages' if kind=='stages' else 'work')
    return {'removed':True,'draft_version':draft.version}

def manual_proposal(session,actor,event,content,message='Manual timing proposal'):
    draft=draft_for(session,event)
    content=PlanContent.model_validate(content).model_dump()
    payload={'plan':content,'message':message}
    proposal=AIProposal(id=uid(),event_id=event.id,kind='manual_plan',source_versions=versions(event,draft),payload=payload,digest=digest(payload),provenance={'source':'human_proposed','model_execution':False,'requires_human_confirmation':True})
    session.add(proposal);session.flush();audit(session,actor,event.id,'planning.proposal.manual',proposal.id)
    return proposal

def assert_current(event,draft,proposal):
    if proposal.source_versions!=versions(event,draft):raise DomainError('stale_proposal','Proposal does not match current event/context/plan/draft versions')

def apply_proposal(session,actor,event,proposal_id,reviewed_digest,accept):
    draft=draft_for(session,event);proposal=session.get(AIProposal,proposal_id)
    if not proposal or proposal.event_id!=event.id or proposal.kind not in ('stages','work','manual_plan'):raise DomainError('not_found','Planning proposal not found',404)
    if proposal.status!='pending' or proposal.digest!=reviewed_digest:raise DomainError('stale_proposal','Review exact pending proposal digest')
    assert_current(event,draft,proposal)
    if accept and proposal.run_id:
        from app.ai.context_builder import MuseSparkContextBuilder
        from app.ai.models import AIRun
        MuseSparkContextBuilder().validate(session,actor,event.id,session.get(AIRun,proposal.run_id).context_manifest,draft=draft)
    if accept:
        level='work' if proposal.kind=='work' or (proposal.kind=='manual_plan' and proposal.payload['plan']['stages']==draft.content['stages']) else 'stages'
        store_content(session,actor,event,draft,proposal.payload['plan'],level)
    decision=ReviewDecision(id=uid(),event_id=event.id,actor_id=actor,subject_kind='proposal',subject_id=proposal.id,subject_digest=proposal.digest,decision='apply' if accept else 'reject')
    session.add(decision);session.flush();proposal.review_decision_id=decision.id;proposal.status='approved' if accept else 'rejected'
    audit(session,actor,event.id,'planning.proposal.review',proposal.id,decision_id=decision.id)
    return {'applied':accept,'status':proposal.status,'draft_version':draft.version}

def confirm(session,actor,event,level):
    draft=draft_for(session,event)
    if draft.context_revision_id!=event.active_context_revision_id:raise DomainError('stale_context','Review draft against current context')
    PlanContent.model_validate(draft.content)
    if not draft.content['stages']:raise DomainError('missing_stages','At least one stage required',422)
    if level=='stages':draft.stage_confirmed=True
    elif level=='work':
        if not draft.stage_confirmed or not draft.content['work']:raise DomainError('invalid_state','Confirmed stages and nonempty work required')
        draft.work_confirmed=True
    elif level=='actors':
        expected={'stage_revision':draft.stage_revision,'work_revision':draft.work_revision}
        if not draft.work_confirmed or draft.derived_from!=expected or not draft.content['roles']:raise DomainError('stale_derivation','Derive actor requirements from the exact confirmed work')
        covered={w for r in draft.content['roles'] for w in r['source_work_ids']}
        if covered!={w['id'] for w in draft.content['work']}:raise DomainError('missing_coverage','All work must have requirements',422)
        draft.actors_confirmed=True;event.lifecycle='planned'
    else:raise DomainError('invalid_level','Invalid confirmation',422)
    plan=append_plan(session,actor,event.id,draft.content,event.version)
    draft.version+=1;event.current_finalization_id=None
    audit(session,actor,event.id,'planning.confirm.'+level,plan.id)
    return {'plan_id':plan.id,'draft_version':draft.version,level+'_confirmed':True}

def derive_actors(session,actor,event):
    draft=draft_for(session,event)
    if not draft.work_confirmed:raise DomainError('invalid_state','Confirm work before deriving roles')
    content=deepcopy(draft.content);content['roles']=[]
    for work in content['work']:
        schedule=Work.model_validate(work).schedule;effort=work['effort']['value'];hours=(schedule.finish-schedule.start)/60
        count=max(0,ceil(effort/hours)) if effort is not None and hours else None
        role=ActorRequirement(id=uid(),title=work['title']+' contributor',stage_ids=[work['stage_id']],work_ids=[work['id']],source_work_ids=[work['id']],required_capabilities=work['skills'],proposed_headcount=count,headcount_basis='Effort divided by scheduled hours; skill/concurrency feasibility unverified' if count is not None else 'Unknown effort; organizer review required',schedule_intervals=[schedule],effort_person_hours=effort,capacity_assumptions=['No accepted participants; estimated demand only'],safety_considerations=work['conditions'])
        content['roles'].append(role.model_dump());work['role_requirement_ids']=[role.id]
    draft.content=PlanContent.model_validate(content).model_dump();draft.derived_from={'stage_revision':draft.stage_revision,'work_revision':draft.work_revision};draft.actors_confirmed=False;draft.version+=1;event.version+=1;event.current_finalization_id=None
    audit(session,actor,event.id,'planning.actors.derive',draft.id)
    return {'requirements':content['roles'],'derived_from':draft.derived_from}

def update_role(session,actor,event,role_id,headcount,capabilities):
    draft=draft_for(session,event)
    content=deepcopy(draft.content);role=next((r for r in content['roles'] if r['id']==role_id),None)
    if not role:raise DomainError('not_found','Requirement not found',404)
    role['proposed_headcount']=headcount;role['required_capabilities']=capabilities;role['headcount_basis']='Human reviewed planned demand; no assignment created'
    draft.content=PlanContent.model_validate(content).model_dump();draft.actors_confirmed=False;draft.version+=1;event.version+=1;event.current_finalization_id=None
    audit(session,actor,event.id,'planning.actor.review',role_id)
    return {'requirement':role,'draft_version':draft.version}
