from copy import deepcopy
from typing import Literal
from fastapi import APIRouter,Depends,Header,Body,Request,Query
from pydantic import Field,ConfigDict
from sqlalchemy import select
from app.api.dependencies import identity,session,bearer
from app.access.authentication import authenticate
from app.access.authorization import require,allowed
from app.shared.commands import command
from app.shared.types import uid
from app.shared.audit import audit
from app.events.models import Event,ContextRevision
from app.events.creation_schemas import CreationForm,Interpretation
from app.events import creation_service as creation
from app.events.dto import creation_dto,event_dto
from app.planning import service as planning
from app.planning.dto import planning_dto,proposal_dto
from app.planning.schemas import PlanContent,ActorRequirement
from app.publication import service as publication
from app.publication.schemas import ParticipantConfiguration,Invite,Partner,PublishPreferences
from app.governance import service as governance
from app.ai import service as ai
from app.ai.models import AIProposal,AIRun
from app.memory.schemas import StrictModel
from app.api.errors import DomainError,missing
from app.publication.models import Publication

router=APIRouter()
DB=Depends(session,scope='function')
USER=Depends(identity)

def ok(data,event=None):return {'data':data,'meta':{'version':event.version} if event else {}}
def write(db,user,event_id,op,key,version,payload,action,permission='plan:write'):
    require(db,user.id,event_id,'source:private')
    result=command(db,user.id,event_id,permission,op,key,payload,version,action)
    return ok(result,db.get(Event,event_id))

def optional_identity(request:Request,credentials=Depends(bearer),db=DB):
    return authenticate(db,request.app.state.settings,credentials.credentials) if credentials else None

class NewDraft(StrictModel):
    format: Literal['in_person','hybrid','online']='in_person'
class SaveDraft(StrictModel):
    step: int=Field(ge=1,le=4)
    form: CreationForm
class Intent(StrictModel):
    model_config=ConfigDict(extra="forbid",str_strip_whitespace=False)
    text: str=Field(min_length=1,max_length=12000)
    source: Literal['written','reviewed_transcript']='written'
class Empty(StrictModel):pass
class ManualInterpretation(StrictModel):
    interpretation: Interpretation
    context_version: int=Field(ge=1)
class ClarificationAnswer(StrictModel):
    question: str=Field(min_length=1,max_length=1000)
    answer: str=Field(min_length=1,max_length=2000)
class Clarify(StrictModel):
    context_version: int=Field(ge=1)
    proposal_id: str|None=None
    answers: list[ClarificationAnswer]=Field(min_length=1,max_length=20)
class TicketEdit(StrictModel):
    status: Literal['open','in_review','waiting_for_documents','closed']
    note: str=Field(min_length=1,max_length=2000)
class ConfirmCreation(StrictModel):
    expected_draft_version: int
    acknowledgements: dict=Field(default_factory=dict)
class AIRequest(StrictModel):
    message: str=Field(default='',max_length=2000)
class AdviceReview(StrictModel):
    decision: Literal['accept','reject']
    reviewed_digest: str=Field(pattern=r'^[a-f0-9]{64}$')
    source_version: int|None=None
    corrected_interpretation: Interpretation|None=None
class PlanReview(StrictModel):
    reviewed_digest: str=Field(pattern=r'^[a-f0-9]{64}$')
    expected_source_versions: dict|None=None
    reason: str=Field(default='',max_length=2000)
class Confirm(StrictModel):
    expected_draft_version: int=Field(ge=1)
    proposal_id: str|None=None
    expected_derived_from: dict|None=None
class StageTiming(StrictModel):
    stage_id: str
    start_day: int=Field(ge=1,le=3660)
    duration_days: int=Field(ge=1,le=3660)
class WorkEdit(StrictModel):
    work_id: str
    patch: dict
class RoleReview(StrictModel):
    headcount: int|None=Field(default=None,ge=0,le=10000)
    capabilities: list[str]=Field(default_factory=list,max_length=30)
class RoleAdd(StrictModel):
    stage_id: str
    title: str=Field(min_length=1,max_length=200)
class Section(StrictModel):
    data: dict
class Finalize(StrictModel):
    confirm_review: bool
    expected_setup_version: int
    expected_plan_id: str
class Publish(StrictModel):
    finalization_id: str
    expected_versions: dict|None=None
class Document(StrictModel):
    name: str=Field(min_length=1,max_length=300)
    document_type: str=Field(min_length=1,max_length=80)
    document_reference: str=Field(default='',max_length=1000)
    size: int=Field(default=0,ge=0,le=10485760)
    mime: str=Field(default='',max_length=100)
class Reminders(StrictModel):
    email_updates: bool=False
    remind_documents: bool=False

@router.post('/events/drafts',status_code=201)
def create_draft(body:NewDraft,user=USER,db=DB,idempotency_key:str=Header()):
    value=creation.new_draft(db,user.id,body.format,idempotency_key)
    return {'data':value,'meta':{'version':value['runtime']['revision']}}

@router.get('/events/{event_id}/creation')
def get_creation(event_id:str,user=USER,db=DB):
    require(db,user.id,event_id,'source:private')
    return ok(creation_dto(db,require(db,user.id,event_id,'context:write')),db.get(Event,event_id))

@router.patch('/events/{event_id}/draft')
def save_creation(event_id:str,body:SaveDraft,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'event.draft.save',idempotency_key,if_match,body.model_dump(),lambda e:creation.save_draft(db,user.id,e,body.step,body.form.model_dump()),'context:write')

@router.post('/events/{event_id}/context-revisions')
def save_intent(event_id:str,body:Intent,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):creation.save_intent(db,user.id,e,body.text,body.source);return creation_dto(db,e)
    return write(db,user,event_id,'context.save',idempotency_key,if_match,body.model_dump(),apply,'context:write')

@router.post('/events/{event_id}/context-interpretations')
def interpret_manually(event_id:str,body:ManualInterpretation,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'context.manual_review',idempotency_key,if_match,body.model_dump(),lambda e:creation.manual_interpretation(db,user.id,e,body.interpretation.model_dump(),body.context_version),'context:write')

@router.patch('/events/{event_id}/context-details')
def revise_context_details(event_id:str,body:CreationForm,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'context.details.revise',idempotency_key,if_match,body.model_dump(),lambda e:creation.revise_details(db,user.id,e,body.model_dump()),'context:write')

@router.post('/events/{event_id}/context-clarifications')
def clarify_context(event_id:str,body:Clarify,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'context.clarify',idempotency_key,if_match,body.model_dump(),lambda e:creation.clarify(db,user.id,e,body.context_version,[x.model_dump() for x in body.answers],body.proposal_id),'context:write')

@router.post('/events/{event_id}/confirm-creation')
def confirm_creation(event_id:str,body:ConfirmCreation,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        if e.version!=body.expected_draft_version:raise DomainError('stale_version','Review exact draft version')
        return creation.confirm_creation(db,user.id,e)
    return write(db,user,event_id,'event.confirm_creation',idempotency_key,if_match,body.model_dump(),apply,'context:write')

@router.post('/events/{event_id}/planning/draft')
def open_planning(event_id:str,body:Empty,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        d=planning.draft_for(db,e,True)
        if d.context_revision_id!=e.active_context_revision_id:
            d.context_revision_id=e.active_context_revision_id;d.stage_confirmed=False;d.work_confirmed=False;d.actors_confirmed=False;d.version+=1;e.version+=1
        return planning_dto(db,e,d)
    return write(db,user,event_id,'planning.open',idempotency_key,if_match,{},apply)

@router.get('/events/{event_id}/planning')
def read_planning(event_id:str,user=USER,db=DB):
    e=require(db,user.id,event_id,'plan:write');require(db,user.id,event_id,'source:private');return ok(planning_dto(db,e),e)

@router.post('/events/{event_id}/planning/checkpoints')
def checkpoint(event_id:str,body:dict=Body(),user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        d=planning.draft_for(db,e)
        if body.get('expected_draft_version',d.version)!=d.version:raise DomainError('stale_version','Draft version changed')
        audit(db,user.id,e.id,'planning.checkpoint',d.id);return {'saved':True,'draft_version':d.version,'checkpoint_id':uid()}
    return write(db,user,event_id,'planning.checkpoint',idempotency_key,if_match,body,apply)

@router.post('/events/{event_id}/planning/items/{kind}',status_code=201)
def add_plan_item(event_id:str,kind:Literal['stages','work','groups','resources','zones'],body:dict=Body(),user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'planning.add.'+kind,idempotency_key,if_match,body,lambda e:planning.manual_add(db,user.id,e,kind,body))
@router.patch('/events/{event_id}/planning/items/{kind}/{item_id}')
def edit_plan_item(event_id:str,kind:Literal['stages','work','groups','resources','zones'],item_id:str,body:dict=Body(),user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'planning.edit.'+kind+':'+item_id,idempotency_key,if_match,body,lambda e:planning.manual_update(db,user.id,e,kind,item_id,body))
@router.delete('/events/{event_id}/planning/items/{kind}/{item_id}')
def delete_plan_item(event_id:str,kind:Literal['stages','work','groups','resources','zones'],item_id:str,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'planning.remove.'+kind+':'+item_id,idempotency_key,if_match,{},lambda e:planning.manual_delete(db,user.id,e,kind,item_id))
@router.put('/events/{event_id}/planning/stage-order')
def order_stages(event_id:str,stage_ids:list[str]=Body(),user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        d=planning.draft_for(db,e);content=deepcopy(d.content);items={s['id']:s for s in content['stages']}
        if len(stage_ids)!=len(items) or set(stage_ids)!=set(items):raise DomainError('invalid_order','Order must contain every stage exactly once',422)
        content['stages']=[items[x] for x in stage_ids];planning.store_content(db,user.id,e,d,content,'stages');return {'saved':True,'draft_version':d.version}
    return write(db,user,event_id,'planning.order',idempotency_key,if_match,stage_ids,apply)
@router.put('/events/{event_id}/planning/manifest')
def manual_manifest(event_id:str,body:PlanContent,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'planning.manifest',idempotency_key,if_match,body.model_dump(),lambda e:{'proposal':proposal_dto(planning.manual_proposal(db,user.id,e,body.model_dump()),e)})

@router.post('/events/{event_id}/planning/stage-edits')
def stage_edit(event_id:str,body:StageTiming,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        d=planning.draft_for(db,e);content=deepcopy(d.content);stage=next((s for s in content['stages'] if s['id']==body.stage_id),None)
        if not stage:missing()
        delta=body.start_day-stage['relative_start'];stage['relative_start']=body.start_day;stage['relative_end']=body.start_day+body.duration_days-1
        for w in content['work']:
            if w['stage_id']==stage['id']:w['schedule']['start_day']+=delta;w['schedule']['end_day']+=delta
        return {'proposal':proposal_dto(planning.manual_proposal(db,user.id,e,content),e)}
    return write(db,user,event_id,'planning.stage_edit',idempotency_key,if_match,body.model_dump(),apply)

@router.post('/events/{event_id}/planning/arrangements')
def arrange(event_id:str,body:dict=Body(),user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        d=planning.draft_for(db,e);content=deepcopy(d.content);done={};pending=list(content['stages'])
        while pending:
            ready=[s for s in pending if all(p in done for p in s['dependency_ids'])]
            if not ready:raise DomainError('invalid_graph','Cannot arrange cyclic stages',422)
            for s in ready:
                start=max([done[p]+1 for p in s['dependency_ids']] or [1]);span=s['relative_end']-s['relative_start'];delta=start-s['relative_start'];s['relative_start']=start;s['relative_end']=start+span;done[s['id']]=s['relative_end'];pending.remove(s)
                for w in content['work']:
                    if w['stage_id']==s['id']:w['schedule']['start_day']+=delta;w['schedule']['end_day']+=delta
        p=planning.manual_proposal(db,user.id,e,content,'Deterministic precedence arrangement; resource feasibility unverified')
        return {'proposal':proposal_dto(p,e),'feasibility':'resource_and_skill_capacity_unverified','violations':[]}
    return write(db,user,event_id,'planning.arrange',idempotency_key,if_match,body,apply)

@router.post('/events/{event_id}/planning/work-edits')
def work_edit(event_id:str,body:WorkEdit,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        d=planning.draft_for(db,e);content=deepcopy(d.content);w=next((x for x in content['work'] if x['id']==body.work_id),None)
        if not w:missing()
        patch=deepcopy(body.patch)
        if 'start_day' in patch:
            delta=patch.pop('start_day')-w['schedule']['start_day'];w['schedule']['start_day']+=delta;w['schedule']['end_day']+=delta
        if 'duration_hours' in patch:
            hours=patch.pop('duration_hours')
            if hours is not None:
                finish=w['schedule']['start_minute']+round(hours*60);w['schedule']['end_day']=w['schedule']['start_day']+finish//1440;w['schedule']['end_minute']=finish%1440;w['duration']={**w['duration'],'value':hours,'unit':'hours'}
        if 'effort' in patch and not isinstance(patch['effort'],dict):patch['effort']={**w['effort'],'value':patch['effort']}
        quantities=patch.pop('resource_quantities',{})
        for r in content['resources']:
            if r['id'] in quantities:
                if w['id'] not in r['work_ids']:raise DomainError('foreign_resource','Resource not linked to this work',422)
                r['quantity']=quantities.pop(r['id'])
        if quantities:raise DomainError('foreign_resource','Unknown resource',422)
        w.update(patch);p=planning.manual_proposal(db,user.id,e,content,'Human-proposed work revision');return {'proposal':proposal_dto(p,e)}
    return write(db,user,event_id,'planning.work_edit',idempotency_key,if_match,body.model_dump(),apply)

@router.post('/events/{event_id}/planning/proposals/{proposal_id}/apply')
@router.post('/events/{event_id}/planning/work-proposals/{proposal_id}/apply')
def apply_plan(event_id:str,proposal_id:str,body:PlanReview,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'planning.apply:'+proposal_id,idempotency_key,if_match,body.model_dump(),lambda e:planning.apply_proposal(db,user.id,e,proposal_id,body.reviewed_digest,True))
@router.post('/events/{event_id}/planning/proposals/{proposal_id}/reject')
def reject_plan(event_id:str,proposal_id:str,body:PlanReview,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'planning.reject:'+proposal_id,idempotency_key,if_match,body.model_dump(),lambda e:planning.apply_proposal(db,user.id,e,proposal_id,body.reviewed_digest,False))

@router.post('/events/{event_id}/planning/{level}-confirmations')
def confirm_plan(event_id:str,level:Literal['stage','work','actor'],body:Confirm,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        d=planning.draft_for(db,e)
        if d.version!=body.expected_draft_version:raise DomainError('stale_version','Draft version changed')
        if body.proposal_id:
            p=db.get(AIProposal,body.proposal_id)
            if not p or p.event_id!=e.id or p.status!='approved':raise DomainError('unapproved_proposal','Apply the reviewed proposal before confirming')
        if body.expected_derived_from is not None and body.expected_derived_from!=d.derived_from:raise DomainError('stale_derivation','Actor derivation changed')
        return planning.confirm(db,user.id,e,{'stage':'stages','actor':'actors','work':'work'}[level])
    return write(db,user,event_id,'planning.confirm.'+level,idempotency_key,if_match,body.model_dump(),apply)
@router.post('/events/{event_id}/planning/actor-derivations')
def derive(event_id:str,body:dict=Body(),user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        d=planning.draft_for(db,e)
        if body.get('expected_work_revision',d.work_revision)!=d.work_revision:raise DomainError('stale_derivation','Confirmed work revision changed')
        return planning.derive_actors(db,user.id,e)
    return write(db,user,event_id,'planning.derive',idempotency_key,if_match,body,apply)
@router.patch('/events/{event_id}/planning/actor-requirements/{role_id}')
def review_role(event_id:str,role_id:str,body:RoleReview,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'planning.role:'+role_id,idempotency_key,if_match,body.model_dump(),lambda e:planning.update_role(db,user.id,e,role_id,body.headcount,body.capabilities))
@router.post('/events/{event_id}/planning/actor-requirements')
def add_role(event_id:str,body:RoleAdd,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        d=planning.draft_for(db,e)
        if not d.work_confirmed:raise DomainError('invalid_state','Confirm work first')
        works=[w for w in d.content['work'] if w['stage_id']==body.stage_id]
        if not works:raise DomainError('missing_work','Stage requires confirmed work',422)
        role=ActorRequirement(id=uid(),title=body.title,stage_ids=[body.stage_id],work_ids=[w['id'] for w in works],source_work_ids=[w['id'] for w in works])
        c=deepcopy(d.content);c['roles'].append(role.model_dump());d.content=PlanContent.model_validate(c).model_dump();d.version+=1;d.actors_confirmed=False;e.version+=1;e.current_finalization_id=None
        return {'requirement':role.model_dump()}
    return write(db,user,event_id,'planning.role.add',idempotency_key,if_match,body.model_dump(),apply)

@router.post('/events/{event_id}/context-proposals',status_code=202)
@router.post('/events/{event_id}/planning/stage-proposals',status_code=202)
@router.post('/events/{event_id}/planning/stage-proposals/revisions',status_code=202)
@router.post('/events/{event_id}/planning/work-proposals',status_code=202)
@router.post('/events/{event_id}/governance/assessments',status_code=202)
def ai_request(event_id:str,body:AIRequest,request:Request,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    path=request.url.path;kind='governance' if '/governance/' in path else 'understanding' if '/context-proposals' in path else 'work' if '/work-proposals' in path else 'stages'
    return write(db,user,event_id,'ai.'+kind,idempotency_key,if_match,body.model_dump(),lambda e:ai.request_run(db,user.id,e,kind,body.message,request.app.state.planning_adapter))
@router.get('/ai-runs/{run_id}')
def read_ai_run(run_id:str,user=USER,db=DB):
    run=db.get(AIRun,run_id)
    if not run:missing()
    e=require(db,user.id,run.event_id,'plan:write');require(db,user.id,e.id,'source:private')
    p=db.get(AIProposal,run.proposal_id) if run.proposal_id else None
    stale=run.source_versions!=planning.versions(e,planning.draft_for(db,e) if run.kind in ('stages','work') else None)
    return ok({'run_id':run.id,'status':'stale' if stale else run.status,'proposal_id':run.proposal_id,'proposal':None if stale or not p else {**proposal_dto(p,e,db.get(ContextRevision,e.active_context_revision_id).sequence),'advisory':p.payload if p.kind in ('participation','resources','execution','recovery') else None,'interpretation':p.payload if p.kind=='understanding' else None},'error':{'code':run.failure_code,'retryable':run.status=='queued'} if run.failure_code else None},e)
@router.post('/events/{event_id}/context-proposals/{proposal_id}/review')
@router.post('/events/{event_id}/governance/proposals/{proposal_id}/review')
def review_ai_advice(event_id:str,proposal_id:str,body:AdviceReview,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        ai.review_advice(db,user.id,e,proposal_id,body.decision,body.reviewed_digest,body.corrected_interpretation.model_dump() if body.corrected_interpretation else None)
        return creation_dto(db,e)
    return write(db,user,event_id,'ai.review:'+proposal_id,idempotency_key,if_match,body.model_dump(),apply)

@router.get('/events/{event_id}/governance')
def read_governance(event_id:str,user=USER,db=DB):
    e=require(db,user.id,event_id,'plan:write');require(db,user.id,event_id,'source:private');return ok(governance.state(db,e),e)
@router.post('/events/{event_id}/governance/tickets')
def start_ticket(event_id:str,body:Empty,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'governance.start',idempotency_key,if_match,{},lambda e:governance.start(db,user.id,e))
@router.patch('/events/{event_id}/governance/tickets/{ticket_id}')
def edit_ticket(event_id:str,ticket_id:str,body:TicketEdit,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'governance.ticket.edit',idempotency_key,if_match,body.model_dump(),lambda e:governance.edit(db,user.id,e,ticket_id,body.status,body.note))
@router.post('/events/{event_id}/governance/tickets/{ticket_id}/documents')
def document(event_id:str,ticket_id:str,body:Document,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'governance.document',idempotency_key,if_match,body.model_dump(),lambda e:governance.update(db,user.id,e,ticket_id,'document',body))
@router.patch('/events/{event_id}/governance/tickets/{ticket_id}/reminders')
def reminders(event_id:str,ticket_id:str,body:Reminders,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'governance.reminders',idempotency_key,if_match,body.model_dump(),lambda e:governance.update(db,user.id,e,ticket_id,'reminders',body))

@router.post('/events/{event_id}/setup/draft')
def open_setup(event_id:str,body:Empty,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):publication.open_setup(db,user.id,e);return publication.setup_dto(db,e)
    return write(db,user,event_id,'setup.open',idempotency_key,if_match,{},apply)
@router.get('/events/{event_id}/setup')
def read_setup(event_id:str,user=USER,db=DB):
    e=require(db,user.id,event_id,'plan:write');require(db,user.id,event_id,'source:private');return ok(publication.setup_dto(db,e),e)
@router.post('/events/{event_id}/setup/checkpoints')
def setup_checkpoint(event_id:str,body:dict=Body(),user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'setup.checkpoint',idempotency_key,if_match,body,lambda e:{'saved':True,'configuration_revision':publication.setup_for(db,e).sequence})
@router.patch('/events/{event_id}/setup/sections/{section}')
def setup_section(event_id:str,section:str,body:Section,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'setup.section.'+section,idempotency_key,if_match,body.model_dump(),lambda e:publication.save_section(db,user.id,e,section,body.data))
@router.put('/events/{event_id}/setup/participant-configuration')
def participant_config(event_id:str,body:ParticipantConfiguration,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'setup.questions',idempotency_key,if_match,body.model_dump(),lambda e:publication.save_tags(db,user.id,e,body.model_dump()))
@router.post('/events/{event_id}/setup/invitation-drafts')
def invite(event_id:str,body:Invite,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'setup.invite',idempotency_key,if_match,body.model_dump(),lambda e:publication.add_entry(db,user.id,e,'invite',body.model_dump()))
@router.delete('/events/{event_id}/setup/invitation-drafts/{invite_id}')
def remove_invite(event_id:str,invite_id:str,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'setup.remove_invite',idempotency_key,if_match,{'id':invite_id},lambda e:publication.remove_invite(db,user.id,e,invite_id))
@router.post('/events/{event_id}/setup/partner-drafts')
def partner(event_id:str,body:Partner,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'setup.partner',idempotency_key,if_match,body.model_dump(),lambda e:publication.add_entry(db,user.id,e,'partner',body.model_dump()))
@router.patch('/events/{event_id}/setup/publication-preferences')
def publish_preferences(event_id:str,body:PublishPreferences,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'setup.publish_preferences',idempotency_key,if_match,body.model_dump(),lambda e:publication.preferences(db,user.id,e,body.model_dump()))
@router.post('/events/{event_id}/finalizations')
def finalize(event_id:str,body:Finalize,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'event.finalize',idempotency_key,if_match,body.model_dump(),lambda e:publication.finalize(db,user.id,e,body.confirm_review,body.expected_setup_version,body.expected_plan_id))
@router.post('/events/{event_id}/publications')
def publish(event_id:str,body:Publish,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'event.publish',idempotency_key,if_match,body.model_dump(),lambda e:{**publication.publish(db,user.id,e,body.finalization_id),'event_id':e.id})
@router.get('/events/{event_id}/profile')
def public_profile(event_id:str,preview:Literal['organizer']|None=None,user=Depends(optional_identity),db=DB):
    event=db.get(Event,event_id)
    if not event:missing()
    result=publication.profile(db,event,user.id if user else None,preview is not None)
    return ok(result,event if user and allowed(db,user.id,event_id,'plan:write') else None)
@router.get('/events')
def discovery(category:str|None=None,q:str|None=Query(default=None,max_length=200),limit:int=Query(default=20,ge=1,le=100),db=DB):
    items=[]
    for e in db.scalars(select(Event).where(Event.current_publication_id.is_not(None)).order_by(Event.id)):
        release=db.get(Publication,e.current_publication_id)
        if release.visibility!='public':continue
        event=release.snapshot['event']
        if category and event['category']!=category:continue
        if q and q.lower() not in (event['title']+' '+event['location']['label']).lower():continue
        items.append({k:event[k] for k in ['id','title','category','filter_group','label','demo','location']}|{'preview_event_id':e.id})
        if len(items)>=limit:break
    return ok({'items':items,'next_cursor':None})
@router.get('/me/events')
def my_events(user=USER,db=DB):
    from app.participation.projections import my_events as project
    return ok({'items':project(db,user.id),'next_cursor':None})


@router.get('/events/{event_id}/context-proposals/{proposal_id}')
def understanding_proposal(event_id:str,proposal_id:str,user=USER,db=DB):
    event=require(db,user.id,event_id,'context:write');require(db,user.id,event_id,'source:private')
    proposal=db.get(AIProposal,proposal_id)
    if not proposal or proposal.event_id!=event_id or proposal.kind!='understanding':missing()
    if proposal.source_versions!=planning.versions(event):raise DomainError('stale_proposal','Context source changed')
    return ok({'proposal':{**proposal_dto(proposal,event,db.get(ContextRevision,event.active_context_revision_id).sequence),'interpretation':proposal.payload}},event)
