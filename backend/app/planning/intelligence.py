"""Scoped proposal contracts and deterministic stage impact, without execution authority."""
from copy import deepcopy
from typing import Annotated,Literal
from pydantic import Field,StringConstraints,model_validator
from app.memory.schemas import StrictModel
from app.planning.schemas import Stage,Work,Resource,WorkGroup,Zone,ActorRequirement,PlanContent,Schedule
from app.api.errors import DomainError

Reference=Annotated[str,StringConstraints(min_length=1,max_length=60,pattern=r'^[A-Za-z0-9_-]+$')]
Note=Annotated[str,StringConstraints(min_length=1,max_length=300)]
class CompactStage(Stage):
    dependency_ids:list[Reference]=Field(default_factory=list,max_length=12)
    intended_outcomes:list[Note]=Field(default_factory=list,max_length=8)
    staffing_assumptions:list[Note]=Field(default_factory=list,max_length=8)
    resource_constraints:list[Note]=Field(default_factory=list,max_length=8)
    risks:list[Note]=Field(default_factory=list,max_length=8)
    assumptions:list[Note]=Field(default_factory=list,max_length=8)
    governance_prerequisites:list[Note]=Field(default_factory=list,max_length=8)
class StageAdvice(StrictModel):
    stages:list[CompactStage]=Field(min_length=1,max_length=12)
    message:str=Field(max_length=2000)
class ExplicitSchedule(Schedule):
    start_day:int=Field(ge=1,le=3660)
    end_day:int=Field(ge=1,le=3660)
    start_minute:int=Field(ge=0,lt=1440)
    end_minute:int=Field(ge=0,le=1440)
    timezone:str=Field(min_length=1,max_length=80)
class ScheduledWork(Work):
    schedule:ExplicitSchedule=Field(...)
    stage_id:Reference
    work_group_id:str=Field(default='',max_length=60)
    dependency_ids:list[Reference]=Field(default_factory=list,max_length=12)
    zone_ids:list[Reference]=Field(default_factory=list,max_length=8)
    resource_requirement_ids:list[Reference]=Field(default_factory=list,max_length=12)
    role_requirement_ids:list[Reference]=Field(default_factory=list,max_length=12)
    skills:list[Note]=Field(default_factory=list,max_length=8)
    exclusion_constraints:list[Note]=Field(default_factory=list,max_length=8)
    conditions:list[Note]=Field(default_factory=list,max_length=8)
    evidence_requirements:list[Note]=Field(default_factory=list,max_length=8)
    scope:str=Field(default='',max_length=800)
    outcome:str=Field(default='',max_length=800)
class ScheduledActor(ActorRequirement):
    schedule_intervals:list[ExplicitSchedule]=Field(min_length=1,max_length=500)
    id:Reference
    stage_ids:list[Reference]=Field(max_length=12)
    work_ids:list[Reference]=Field(max_length=12)
    source_work_ids:list[Reference]=Field(max_length=12)
    required_capabilities:list[Note]=Field(default_factory=list,max_length=8)
    capacity_assumptions:list[Note]=Field(default_factory=list,max_length=8)
    safety_considerations:list[Note]=Field(default_factory=list,max_length=8)
    responsibilities:list[Note]=Field(default_factory=list,max_length=8)
    coordination_needs:list[Note]=Field(default_factory=list,max_length=8)
    resource_responsibilities:list[Note]=Field(default_factory=list,max_length=8)
# AROUNDYOU RESOURCE QUANTITY FIX: strict new inference contract only; saved Resource stays legacy-compatible.
class ResourceEstimate(StrictModel):
    quantity:float|None=Field(...,ge=0,allow_inf_nan=False,strict=True)
    estimation_basis:str|None=Field(...,min_length=1,max_length=400)
    unknown_reason:str|None=Field(...,min_length=1,max_length=400)
    @model_validator(mode='after')
    def justified_quantity(self):
        if self.quantity is None:
            if not self.unknown_reason or self.estimation_basis is not None:
                raise ValueError('Unknown quantity requires unknown_reason and estimation_basis=null')
        elif not self.estimation_basis or self.unknown_reason is not None:
            raise ValueError('Numerical quantity requires estimation_basis and unknown_reason=null')
        return self

class LinkedResource(ResourceEstimate,Resource):
    work_ids:list[Reference]=Field(default_factory=list,max_length=12)
class LinkedGroup(WorkGroup):
    stage_id:Reference
class WorkAdvice(StrictModel):
    work:list[ScheduledWork]=Field(min_length=1,max_length=60)
    groups:list[LinkedGroup]=Field(default_factory=list,max_length=30)
    resources:list[LinkedResource]=Field(default_factory=list,max_length=60)
    zones:list[Zone]=Field(default_factory=list,max_length=30)
    message:str=Field(max_length=2000)
class ActorAdvice(StrictModel):
    roles:list[ScheduledActor]=Field(min_length=1,max_length=60)
    message:str=Field(max_length=2000)
class ChatAdvice(StrictModel):
    message:str=Field(min_length=1,max_length=5000)
    proposed_stages:list[CompactStage]|None=None

CONTRACTS={'stages':StageAdvice,'work':WorkAdvice,'actors':ActorAdvice,'planning_chat':ChatAdvice}

def marked(content):
    content=deepcopy(content);stages={s['id']:s for s in content['stages']}
    content['stale_work_ids']=[w['id'] for w in content['work'] if w['stage_id'] in stages and not stages[w['stage_id']]['relative_start']<=w['schedule']['start_day']<=w['schedule']['end_day']<=stages[w['stage_id']]['relative_end']]
    return content

def impact(base,candidate):
    old={s['id']:s for s in base['stages']};new={s['id']:s for s in candidate['stages']}
    changed={i for i in old.keys()|new.keys() if old.get(i)!=new.get(i)};affected=set(changed)
    while True:
        extra={s['id'] for s in candidate['stages'] if set(s['dependency_ids'])&affected}
        if extra<=affected:break
        affected|=extra
    errors=[]
    try:PlanContent.model_validate(marked(candidate))
    except ValueError as exc:errors=[e['msg'] for e in exc.errors()] if hasattr(exc,'errors') else ['Invalid plan graph']
    return {'changed_stage_ids':sorted(changed),'affected_stage_ids':sorted(affected),'stale_work_ids':marked(candidate)['stale_work_ids'],'violations':errors,'dates':[{'stage_id':s['id'],'start_day':s['relative_start'],'end_day':s['relative_end']} for s in candidate['stages'] if s['id'] in affected],'capacity_feasibility':'unverified','work_intent_rewritten':False}

def validate(kind,result,base):
    value=CONTRACTS[kind].model_validate(result).model_dump()
    if kind=='planning_chat' and value['proposed_stages'] is None:
        return {'message':value['message'],'advisory_only':True,'changes':[],'violations':[]}
    candidate=deepcopy(base);resource_reviews=[]
    # AROUNDYOU RESOURCE QUANTITY FIX: keep rationale in the pending proposal, not legacy plan fields.
    if kind=='work':
        for resource in value['resources']:
            resource_reviews.append({'resource_id':resource['id'],'work_ids':resource['work_ids'],'quantity':resource['quantity'],'estimation_basis':resource.pop('estimation_basis'),'unknown_reason':resource.pop('unknown_reason'),'status':'Needs review' if resource['quantity'] is None else 'Estimated - human review required'})
        for work in value['work']:
            work['conditions']+=['Resource '+r['resource_id']+' Needs review: '+r['unknown_reason'] for r in resource_reviews if r['quantity'] is None and work['id'] in r['work_ids']]
    if kind in ('stages','planning_chat'):candidate['stages']=value['stages' if kind=='stages' else 'proposed_stages']
    elif kind=='work':
        for key in ('work','groups','resources','zones'):candidate[key]=value[key]
        candidate['roles']=[]
        for w in candidate['work']:w['role_requirement_ids']=[]
    else:
        candidate['roles']=value['roles']
        for w in candidate['work']:w['role_requirement_ids']=[r['id'] for r in value['roles'] if w['id'] in r['work_ids']]
        if {w for r in value['roles'] for w in r['work_ids']}!={w['id'] for w in candidate['work']}:raise DomainError('missing_coverage','Actor recommendations must cover all confirmed work.',422)
        works={w['id']:w for w in candidate['work']}
        for role in candidate['roles']:
            windows={__import__('json').dumps(works[w]['schedule'],sort_keys=True) for w in role['work_ids'] if w in works}
            if not role['schedule_intervals'] or any(__import__('json').dumps(window,sort_keys=True) not in windows for window in role['schedule_intervals']):raise DomainError('invalid_actor_window','Role availability windows must come from its confirmed source work.',422)
            if {__import__('json').dumps(window,sort_keys=True) for window in role['schedule_intervals']}!=windows:raise DomainError('invalid_actor_window','Role windows must cover all its source work.',422)
            role['capacity_assumptions'].append('Model-estimated demand only; no accepted participants or assignments are created.')
    if kind in ('stages','planning_chat'):
        for stage in candidate['stages']:
            stage['duration']={'value':stage['relative_end']-stage['relative_start']+1,'unit':'days','confidence':'proposed_schedule','known_subtotal':None}
            for key in ('volume','effort'):
                stage[key]['confidence']='model_estimate' if stage[key]['value'] is not None else 'unknown'
    candidate=marked(candidate)
    if kind in ('work','actors') and candidate['stale_work_ids']:raise DomainError('stale_work','Reconcile work timing with the confirmed stage windows first.',422)
    candidate=PlanContent.model_validate(candidate).model_dump();analysis=impact(base,candidate)
    changes=[f"{x['stage_id']}: Day {x['start_day']}–{x['end_day']}" for x in analysis['dates']]
    if kind=='work':changes=[w['id']+' · '+w['title'] for w in candidate['work']]
    if kind=='actors':changes=[r['id']+' · '+r['title']+' · demand '+str(r['proposed_headcount']) for r in candidate['roles']]
    return {'plan':candidate,'message':value['message'],'changes':changes,'violations':analysis['violations'],'impact':analysis,'advisory_only':False,**({'resource_quantity_reviews':resource_reviews} if kind=='work' else {})}


# Small selected-stage transport. IDs, links and actor windows are server derived.
class StageResourceNeed(ResourceEstimate):
    title:str=Field(min_length=1,max_length=100)
    kind:Literal['consumable','equipment','service','facility','funding']
    unit:str=Field(min_length=1,max_length=40)
class StageWorkUnit(StrictModel):
    title:str=Field(min_length=1,max_length=120)
    objective:str=Field(min_length=1,max_length=400)
    outcome:str=Field(min_length=1,max_length=400)
    schedule:ExplicitSchedule
    effort_person_hours:float|None=Field(default=None,ge=0,allow_inf_nan=False)
    dependency_indexes:list[int]=Field(default_factory=list,max_length=6)
    skills:list[Note]=Field(default_factory=list,max_length=5)
    conditions:list[Note]=Field(default_factory=list,max_length=5)
    evidence:list[Note]=Field(default_factory=list,max_length=5)
    resources:list[StageResourceNeed]=Field(default_factory=list,max_length=4)
class SelectedWorkAdvice(StrictModel):
    work:list[StageWorkUnit]=Field(min_length=1,max_length=6)
    message:str=Field(min_length=1,max_length=800)
class StageActor(StrictModel):
    title:str=Field(min_length=1,max_length=120)
    work_ids:list[Reference]=Field(min_length=1,max_length=6)
    headcount:int|None=Field(default=None,ge=1,le=1000)
    basis:str=Field(min_length=1,max_length=300)
    capabilities:list[Note]=Field(default_factory=list,max_length=5)
    responsibilities:list[Note]=Field(default_factory=list,max_length=5)
    coordination:list[Note]=Field(default_factory=list,max_length=4)
    resource_responsibilities:list[Note]=Field(default_factory=list,max_length=4)
    safety:list[Note]=Field(default_factory=list,max_length=4)
class SelectedActorAdvice(StrictModel):
    roles:list[StageActor]=Field(min_length=1,max_length=6)
    message:str=Field(min_length=1,max_length=800)

def validate_selected(kind,result,base,stage_id,run_id):
    from app.shared.types import digest
    stage=next((s for s in base['stages'] if s['id']==stage_id),None)
    if not stage:raise DomainError('invalid_stage','Select a current confirmed stage.',422)
    if kind=='planning_chat':
        value=ChatAdvice.model_validate(result)
        if value.proposed_stages is not None:raise DomainError('scope_violation','Use explicit Stage Planning recalculation for schedule proposals.',422)
        return {'message':value.message,'advisory_only':True,'changes':[],'violations':[],'stage_id':stage_id}
    candidate=deepcopy(base);prefix=digest({'stage':stage_id,'run':run_id})[:16]
    owned_work={w['id'] for w in base['work'] if w['stage_id']==stage_id}
    if kind=='work':
        value=SelectedWorkAdvice.model_validate(result);items=value.work
        # Replacement must not break work or shared requirements outside this stage.
        if any(owned_work & set(w['dependency_ids']) for w in base['work'] if w['stage_id']!=stage_id):raise DomainError('dependent_work_review','Other-stage work depends on this stage; edit the existing linked work manually.',422)
        if any(stage_id in r['stage_ids'] and set(r['stage_ids'])!={stage_id} for r in base['roles']):raise DomainError('shared_requirement_review','Review shared cross-stage requirements before replacing work.',422)
        new=[];needs=[];resource_reviews=[];group_id='g_'+prefix
        ids=['w_'+prefix+'_'+str(i+1) for i in range(len(items))]
        for i,item in enumerate(items):
            if any(x<1 or x>len(items) or x==i+1 for x in item.dependency_indexes) or len(set(item.dependency_indexes))!=len(item.dependency_indexes):raise DomainError('invalid_dependency','Invalid local dependency index.',422)
            schedule=item.schedule
            if not stage['relative_start']<=schedule.start_day<=schedule.end_day<=stage['relative_end']:raise DomainError('stale_work','Model work lies outside the selected stage window.',422)
            if schedule.timezone!=base.get('_event_timezone',schedule.timezone):raise DomainError('invalid_schedule','Work timezone must match event timezone.',422)
            resource_ids=[]
            for j,r in enumerate(item.resources):
                rid='q_'+prefix+'_'+str(i+1)+'_'+str(j+1);resource_ids.append(rid)
                # AROUNDYOU RESOURCE QUANTITY FIX: preserve numerical demand and auditable reasoning.
                fields=r.model_dump();basis=fields.pop('estimation_basis');reason=fields.pop('unknown_reason')
                needs.append(Resource(id=rid,work_ids=[ids[i]],**fields).model_dump())
                resource_reviews.append({'resource_id':rid,'work_ids':[ids[i]],'quantity':r.quantity,'estimation_basis':basis,'unknown_reason':reason,'status':'Needs review' if r.quantity is None else 'Estimated - human review required'})
            new.append(Work(id=ids[i],stage_id=stage_id,work_group_id=group_id,title=item.title,scope=item.objective,outcome=item.outcome,schedule=schedule,dependency_ids=[ids[x-1] for x in item.dependency_indexes],skills=item.skills,conditions=item.conditions+['Resource '+r['resource_id']+' Needs review: '+r['unknown_reason'] for r in resource_reviews if r['quantity'] is None and ids[i] in r['work_ids']],evidence_requirements=item.evidence,resource_requirement_ids=resource_ids,effort={'value':item.effort_person_hours,'unit':'person_hours','confidence':'model_estimate'},duration={'value':(schedule.finish-schedule.start)/60,'unit':'hours','confidence':'proposed_schedule'}).model_dump())
        candidate['work']=[w for w in base['work'] if w['stage_id']!=stage_id]+new
        candidate['groups']=[g for g in base['groups'] if g['stage_id']!=stage_id]+[WorkGroup(id=group_id,stage_id=stage_id,title=stage['title']).model_dump()]
        candidate['resources']=[]
        for r in base['resources']:
            if not owned_work.intersection(r['work_ids']):candidate['resources'].append(deepcopy(r));continue
            remaining=[w for w in r['work_ids'] if w not in owned_work]
            if remaining:raise DomainError('shared_resource_review','Review shared resource quantities before replacing work.',422)
        candidate['resources']+=needs
        candidate['roles']=[r for r in base['roles'] if stage_id not in r['stage_ids']]
        changes=[w['title'] for w in new]
    else:
        value=SelectedActorAdvice.model_validate(result);works={w['id']:w for w in base['work'] if w['stage_id']==stage_id}
        if not works:raise DomainError('missing_work','Selected stage needs confirmed work.',422)
        if any(stage_id in r['stage_ids'] and set(r['stage_ids'])!={stage_id} for r in base['roles']):raise DomainError('shared_requirement_review','Review cross-stage requirements explicitly.',422)
        new=[]
        for i,r in enumerate(value.roles):
            if len(set(r.work_ids))!=len(r.work_ids) or not set(r.work_ids)<=set(works):raise DomainError('scope_violation','Actor source work must belong to the selected stage.',422)
            windows=[]
            for wid in r.work_ids:
                if works[wid]['schedule'] not in windows:windows.append(works[wid]['schedule'])
            efforts=[works[wid]['effort']['value'] for wid in r.work_ids]
            new.append(ActorRequirement(id='r_'+prefix+'_'+str(i+1),title=r.title,stage_ids=[stage_id],work_ids=r.work_ids,source_work_ids=r.work_ids,required_capabilities=r.capabilities,proposed_headcount=r.headcount,headcount_basis=r.basis,schedule_intervals=windows,effort_person_hours=sum(efforts) if all(x is not None for x in efforts) else None,responsibilities=r.responsibilities,coordination_needs=r.coordination,resource_responsibilities=r.resource_responsibilities,safety_considerations=r.safety,capacity_assumptions=['Model-estimated demand; availability, concurrency and skills require human review. No assignments created.']).model_dump())
        if {w for r in new for w in r['work_ids']}!=set(works):raise DomainError('missing_coverage','Cover every confirmed work unit in the selected stage.',422)
        candidate['roles']=[r for r in base['roles'] if stage_id not in r['stage_ids']]+new
        for w in candidate['work']:
            if w['stage_id']==stage_id:w['role_requirement_ids']=[r['id'] for r in new if w['id'] in r['work_ids']]
        changes=[r['title'] for r in new]
    candidate.pop('_event_timezone',None);candidate=marked(candidate)
    if owned_work.intersection(candidate['stale_work_ids']) or any(w['stage_id']==stage_id and w['id'] in candidate['stale_work_ids'] for w in candidate['work']):raise DomainError('stale_work','Selected stage work is stale.',422)
    candidate=PlanContent.model_validate(candidate).model_dump()
    return {'plan':candidate,'stage_id':stage_id,'message':value.message,'changes':changes,'violations':[],'advisory_only':False,**({'resource_quantity_reviews':resource_reviews} if kind=='work' else {})}
