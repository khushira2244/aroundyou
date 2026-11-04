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

def stage_fingerprint(content,stage_id,level):
    works=[w for w in content['work'] if w['stage_id']==stage_id]
    ids={w['id'] for w in works}
    # Actor linkage is derived and does not invalidate confirmed work.
    work=[{k:v for k,v in w.items() if k not in ('role_requirement_ids','revision')} for w in works]
    body={'stage':next((s for s in content['stages'] if s['id']==stage_id),None),'work':work,'resources':[r for r in content['resources'] if ids.intersection(r['work_ids'])],'groups':[g for g in content['groups'] if g['stage_id']==stage_id]}
    if level=='actors':body['roles']=[r for r in content['roles'] if stage_id in r['stage_ids']]
    return digest(body)

def preserve_reviews(draft):
    reviews=deepcopy(draft.stage_reviews or {})
    for level,flag in [('work',draft.work_confirmed),('actors',draft.actors_confirmed)]:
        if level not in reviews:reviews[level]={s['id']:stage_fingerprint(draft.content,s['id'],level) for s in draft.content['stages']} if flag else {}
    draft.stage_reviews=reviews

def reviewed_stages(draft,level):
    reviews=draft.stage_reviews or {}
    if level not in reviews:return [s['id'] for s in draft.content['stages']] if getattr(draft,'work_confirmed' if level=='work' else 'actors_confirmed') else []
    return [s['id'] for s in draft.content['stages'] if reviews[level].get(s['id'])==stage_fingerprint(draft.content,s['id'],level) and any(w['stage_id']==s['id'] for w in draft.content['work']) and not any(w['stage_id']==s['id'] and w['id'] in draft.content.get('stale_work_ids',[]) for w in draft.content['work'])]

def store_content(session,actor,event,draft,content,level,stage_id=None):
    preserve_reviews(draft)
    if level=='work':
        content=deepcopy(content)
        affected={stage_id} if stage_id else {s['id'] for s in content['stages'] if stage_fingerprint(content,s['id'],'work')!=stage_fingerprint(draft.content,s['id'],'work')}
        content['roles']=[r for r in content['roles'] if not affected.intersection(r['stage_ids'])]
        for w in content['work']:
            if w['stage_id'] in affected:w['role_requirement_ids']=[]
    from app.planning.intelligence import marked
    content=marked(content)
    if level!='stages':content['stale_work_ids']=[w for w in content['stale_work_ids'] if w in draft.content.get('stale_work_ids',[])]
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
    draft=draft_for(session,event,True)
    payload=deepcopy(payload);base_id=payload.pop('base_proposal_id',None)
    content=stage_edit_base(session,event,draft,base_id) if kind=='stages' else work_edit_base(session,event,draft,base_id) if kind=='work' else deepcopy(draft.content)
    spec={'stages':Stage,'work':Work,'groups':WorkGroup,'resources':Resource,'zones':Zone}
    if kind not in spec:raise DomainError('invalid_kind','Unsupported plan entity',422)
    item=spec[kind].model_validate({**payload,'id':uid()})
    content[kind].append(item.model_dump())
    if base_id and kind in ('stages','work'):
        proposal=manual_proposal(session,actor,event,content,'Human-proposed additional '+('stage' if kind=='stages' else 'work'))
        if kind=='work':
            proposal.payload={**proposal.payload,'stage_id':item.stage_id};proposal.digest=digest(proposal.payload)
        return {'id':item.id,'proposal_id':proposal.id,'draft_version':draft.version}
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
    from app.planning.intelligence import marked
    if content['stages']==draft.content['stages']:
        content=marked(content);content['stale_work_ids']=[w for w in content['stale_work_ids'] if w in draft.content.get('stale_work_ids',[])]
    content=PlanContent.model_validate(content).model_dump()
    payload={'plan':content,'message':message}
    proposal=AIProposal(id=uid(),event_id=event.id,kind='manual_plan',source_versions=versions(event,draft),payload=payload,digest=digest(payload),provenance={'source':'human_proposed','model_execution':False,'requires_human_confirmation':True})
    session.add(proposal);session.flush();audit(session,actor,event.id,'planning.proposal.manual',proposal.id)
    return proposal

def assert_current(event,draft,proposal):
    if proposal.source_versions!=versions(event,draft):raise DomainError('stale_proposal','Proposal does not match current event/context/plan/draft versions')

def stage_edit_base(session,event,draft,proposal_id=None):
    """Edit a current pending preview without applying it to authoritative state."""
    if not proposal_id:return deepcopy(draft.content)
    proposal=session.get(AIProposal,proposal_id)
    if not proposal or proposal.event_id!=event.id or proposal.kind not in ('stages','manual_plan','planning_chat'):
        raise DomainError('not_found','Stage proposal not found',404)
    if proposal.status!='pending' or proposal.payload.get('advisory_only') or not proposal.payload.get('plan'):
        raise DomainError('invalid_proposal','Select a pending stage plan',422)
    assert_current(event,draft,proposal)
    return deepcopy(proposal.payload['plan'])


def work_edit_base(session,event,draft,proposal_id=None):
    """Pending work remains a preview until explicit review; stages stay intact."""
    if not proposal_id:return deepcopy(draft.content)
    proposal=session.get(AIProposal,proposal_id)
    if not proposal or proposal.event_id!=event.id or proposal.kind not in ('work','manual_plan'):
        raise DomainError('not_found','Work proposal not found',404)
    if proposal.status!='pending' or proposal.payload.get('advisory_only') or not proposal.payload.get('plan'):
        raise DomainError('invalid_proposal','Select a pending work plan',422)
    assert_current(event,draft,proposal)
    content=proposal.payload['plan']
    if content['stages']!=draft.content['stages']:
        raise DomainError('scope_violation','Work edits must preserve confirmed stages',422)
    return deepcopy(content)


def apply_proposal(session,actor,event,proposal_id,reviewed_digest,accept):
    draft=draft_for(session,event);proposal=session.get(AIProposal,proposal_id)
    if not proposal or proposal.event_id!=event.id or proposal.kind not in ('stages','work','actors','planning_chat','manual_plan'):raise DomainError('not_found','Planning proposal not found',404)
    if proposal.status!='pending' or proposal.digest!=reviewed_digest:raise DomainError('stale_proposal','Review exact pending proposal digest')
    assert_current(event,draft,proposal)
    if accept and (proposal.payload.get('advisory_only') or proposal.payload.get('violations')):raise DomainError('invalid_proposal','Advisory text or invalid timing cannot be applied.',422)
    if accept and proposal.run_id:
        from app.ai.context_builder import MuseSparkContextBuilder
        from app.ai.models import AIRun
        MuseSparkContextBuilder().validate(session,actor,event.id,session.get(AIRun,proposal.run_id).context_manifest,draft=draft)
    if accept:
        level='actors' if proposal.kind=='actors' else 'work' if proposal.kind=='work' or (proposal.kind=='manual_plan' and proposal.payload['plan']['stages']==draft.content['stages']) else 'stages'
        store_content(session,actor,event,draft,proposal.payload['plan'],level,proposal.payload.get('stage_id'))
        if level=='actors':draft.derived_from={'stage_revision':draft.stage_revision,'work_revision':draft.work_revision}
    decision=ReviewDecision(id=uid(),event_id=event.id,actor_id=actor,subject_kind='proposal',subject_id=proposal.id,subject_digest=proposal.digest,decision='apply' if accept else 'reject')
    session.add(decision);session.flush();proposal.review_decision_id=decision.id;proposal.status='approved' if accept else 'rejected'
    audit(session,actor,event.id,'planning.proposal.review',proposal.id,decision_id=decision.id)
    return {'applied':accept,'status':proposal.status,'draft_version':draft.version}

def merge_actor_plans(base, candidates):
    """Merge selected-stage role candidates without rewriting confirmed work or summing people."""
    content=deepcopy(base);roles={r['id']:r for r in content['roles']};scopes=set()
    work_shape=lambda plan:[{k:v for k,v in w.items() if k not in ('role_requirement_ids','revision')} for w in plan['work']]
    for scope,plan in candidates:
        if scope in scopes:raise DomainError('duplicate_scope','Review one actor proposal per stage',422)
        scopes.add(scope)
        if any(plan[k]!=base[k] for k in ('stages','groups','resources','zones','dependencies','stale_work_ids')) or work_shape(plan)!=work_shape(base):
            raise DomainError('scope_violation','Actor proposals cannot change confirmed work or stages',422)
        if scope and scope not in {s['id'] for s in base['stages']}:raise DomainError('invalid_stage','Actor stage not found',422)
        selected=[r for r in plan['roles'] if not scope or scope in r['stage_ids']]
        if not selected:raise DomainError('missing_coverage','Stage has no proposed actors',422)
        for rid,role in list(roles.items()):
            if not scope or role['stage_ids']==[scope]:del roles[rid]
        for role in selected:
            old=roles.get(role['id'])
            if old:
                if any(old[k]!=role[k] for k in ('title','proposed_headcount','effort_person_hours')):
                    raise DomainError('shared_actor_conflict','Shared actor estimates conflict; review before confirming',422)
                merged=deepcopy(role)
                for key in ('stage_ids','work_ids','source_work_ids','schedule_intervals','responsibilities','coordination_needs','resource_responsibilities','required_capabilities','capacity_assumptions','safety_considerations'):
                    merged[key]=deepcopy(old[key])+[x for x in role[key] if x not in old[key]]
                roles[role['id']]=merged
            else:roles[role['id']]=deepcopy(role)
    content['roles']=list(roles.values())
    for work in content['work']:work['role_requirement_ids']=[r['id'] for r in content['roles'] if work['id'] in r['work_ids']]
    validated=PlanContent.model_validate(content).model_dump()
    if {w for r in validated['roles'] for w in r['source_work_ids']}!={w['id'] for w in validated['work']}:
        raise DomainError('missing_coverage','Generate or add actors covering all confirmed work first',422)
    return validated


def confirm_event_actors(session,actor,event,reviews):
    """One transaction validates every candidate before any source version changes."""
    draft=draft_for(session,event)
    if not draft.work_confirmed or draft.content.get('stale_work_ids'):raise DomainError('invalid_state','Confirm all stage work first',422)
    ids=[r['proposal_id'] for r in reviews]
    if len(set(ids))!=len(ids):raise DomainError('duplicate_proposal','Duplicate actor review',422)
    proposals=[]
    for review in reviews:
        proposal=session.get(AIProposal,review['proposal_id'])
        if not proposal or proposal.event_id!=event.id or proposal.kind!='actors':raise DomainError('not_found','Actor proposal not found',404)
        if proposal.status!='pending' or proposal.digest!=review['reviewed_digest']:raise DomainError('stale_proposal','Review the exact pending actor proposal')
        assert_current(event,draft,proposal)
        if proposal.payload.get('advisory_only') or proposal.payload.get('violations'):raise DomainError('invalid_proposal','Invalid actor proposal',422)
        if proposal.run_id:
            from app.ai.context_builder import MuseSparkContextBuilder
            from app.ai.models import AIRun
            MuseSparkContextBuilder().validate(session,actor,event.id,session.get(AIRun,proposal.run_id).context_manifest,draft=draft)
        proposals.append(proposal)
    merged=merge_actor_plans(draft.content,[(p.payload.get('stage_id'),p.payload['plan']) for p in proposals])
    if proposals:store_content(session,actor,event,draft,merged,'actors')
    draft.derived_from={'stage_revision':draft.stage_revision,'work_revision':draft.work_revision}
    for proposal in proposals:
        decision=ReviewDecision(id=uid(),event_id=event.id,actor_id=actor,subject_kind='proposal',subject_id=proposal.id,subject_digest=proposal.digest,decision='apply')
        session.add(decision);session.flush();proposal.review_decision_id=decision.id;proposal.status='approved'
        audit(session,actor,event.id,'planning.proposal.review',proposal.id,decision_id=decision.id)
    return confirm(session,actor,event,'actors')


def confirm(session,actor,event,level,stage_id=None):
    draft=draft_for(session,event)
    if draft.context_revision_id!=event.active_context_revision_id:raise DomainError('stale_context','Review draft against current context')
    PlanContent.model_validate(draft.content)
    if stage_id and level in ('work','actors'):
        if stage_id not in {s['id'] for s in draft.content['stages']}:raise DomainError('invalid_stage','Selected stage not found.',422)
        if not draft.stage_confirmed:raise DomainError('invalid_state','Confirm stages first.')
        selected=[w for w in draft.content['work'] if w['stage_id']==stage_id]
        if not selected or any(w['id'] in draft.content.get('stale_work_ids',[]) for w in selected):raise DomainError('stale_work','Selected stage needs valid work.',422)
        if level=='actors':
            if stage_id not in reviewed_stages(draft,'work'):raise DomainError('invalid_state','Confirm selected stage work first.',422)
            if {w for r in draft.content['roles'] if stage_id in r['stage_ids'] for w in r['work_ids']}!={w['id'] for w in selected}:raise DomainError('missing_coverage','Selected stage needs actor coverage.',422)
        preserve_reviews(draft);reviews=deepcopy(draft.stage_reviews);reviews[level][stage_id]=stage_fingerprint(draft.content,stage_id,level);draft.stage_reviews=reviews
        draft.work_confirmed=len(reviewed_stages(draft,'work'))==len(draft.content['stages'])
        draft.actors_confirmed=draft.work_confirmed and len(reviewed_stages(draft,'actors'))==len(draft.content['stages'])
        if draft.actors_confirmed:event.lifecycle='planned'
        plan=append_plan(session,actor,event.id,draft.content,event.version);draft.version+=1;event.current_finalization_id=None
        audit(session,actor,event.id,'planning.confirm.'+level+'.stage',plan.id)
        return {'plan_id':plan.id,'stage_id':stage_id,'draft_version':draft.version,'stage_confirmed':True}
    if not draft.content['stages']:raise DomainError('missing_stages','At least one stage required',422)
    if level=='stages':draft.stage_confirmed=True
    elif level=='work':
        if draft.content.get('stale_work_ids'):raise DomainError('stale_work','Review and reconcile the flagged work windows before confirming work.',422)
        if not draft.stage_confirmed or not draft.content['work']:raise DomainError('invalid_state','Confirmed stages and nonempty work required')
        draft.work_confirmed=True
    elif level=='actors':
        expected={'stage_revision':draft.stage_revision,'work_revision':draft.work_revision}
        if not draft.work_confirmed or draft.derived_from!=expected or not draft.content['roles']:raise DomainError('stale_derivation','Derive actor requirements from the exact confirmed work')
        covered={w for r in draft.content['roles'] for w in r['source_work_ids']}
        if covered!={w['id'] for w in draft.content['work']}:raise DomainError('missing_coverage','All work must have requirements',422)
        draft.actors_confirmed=True;event.lifecycle='planned'
    else:raise DomainError('invalid_level','Invalid confirmation',422)
    if level in ('work','actors'):
        preserve_reviews(draft);reviews=deepcopy(draft.stage_reviews);reviews[level]={s['id']:stage_fingerprint(draft.content,s['id'],level) for s in draft.content['stages']};draft.stage_reviews=reviews
    plan=append_plan(session,actor,event.id,draft.content,event.version)
    draft.version+=1;event.current_finalization_id=None
    audit(session,actor,event.id,'planning.confirm.'+level,plan.id)
    return {'plan_id':plan.id,'draft_version':draft.version,level+'_confirmed':True}

def derive_actors(session,actor,event):
    draft=draft_for(session,event)
    if not draft.work_confirmed or draft.content.get('stale_work_ids'):raise DomainError('invalid_state','Confirm reconciled work before deriving roles')
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
    draft=draft_for(session,event);preserve_reviews(draft)
    content=deepcopy(draft.content);role=next((r for r in content['roles'] if r['id']==role_id),None)
    if not role:raise DomainError('not_found','Requirement not found',404)
    role['proposed_headcount']=headcount;role['required_capabilities']=capabilities;role['headcount_basis']='Human reviewed planned demand; no assignment created'
    draft.content=PlanContent.model_validate(content).model_dump();draft.actors_confirmed=False;draft.version+=1;event.version+=1;event.current_finalization_id=None
    audit(session,actor,event.id,'planning.actor.review',role_id)
    return {'requirement':role,'draft_version':draft.version}


def edit_resource_requirements(content,work_id,quantities,new_resources):
    """Build a human review candidate; never change the saved plan in place."""
    content=deepcopy(content)
    work=next((w for w in content['work'] if w['id']==work_id),None)
    if not work:raise DomainError('not_found','Work not found',404)
    remaining=dict(quantities)
    for resource in content['resources']:
        if resource['id'] in remaining:
            if work_id not in resource['work_ids']:raise DomainError('foreign_resource','Resource not linked to this work',422)
            resource['quantity']=remaining.pop(resource['id'])
            Resource.model_validate(resource)
    if remaining:raise DomainError('foreign_resource','Unknown resource',422)
    if not isinstance(new_resources,list) or len(new_resources)>20:raise DomainError('invalid_resource','At most 20 new resources per proposal',422)
    for raw in new_resources:
        resource=Resource.model_validate({**raw,'id':uid(),'work_ids':[work_id]}).model_dump()
        content['resources'].append(resource)
        work['resource_requirement_ids'].append(resource['id'])
    return content
