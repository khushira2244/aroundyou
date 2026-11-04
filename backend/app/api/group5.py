from typing import Literal
from fastapi import APIRouter
from pydantic import Field
from app.api.group2 import USER,DB,ok
from app.access.authorization import require
from app.memory.schemas import StrictModel
from app.recovery.service import impact
router=APIRouter()
class ImpactRequest(StrictModel):
    issue_ids:list[str]=Field(min_length=1,max_length=30)
    expected_plan_id:str
@router.post('/events/{event_id}/recovery/impact')
def recovery_impact(event_id:str,body:ImpactRequest,user=USER,db=DB):
    e=require(db,user.id,event_id,'plan:write');require(db,user.id,event_id,'source:private')
    return ok(impact(db,user.id,e,body.issue_ids,body.expected_plan_id),e)

from fastapi import Header
from app.api.group3 import write
from app.participation import dynamic_insights as di
from app.participation.service import published
from app.events.models import Event
from app.api.errors import missing
@router.get('/events/{event_id}/insight-configuration')
def insight_configuration(event_id:str,user=USER,db=DB):
    e=db.get(Event,event_id)
    if not e:missing()
    from app.access.authorization import allowed
    if not allowed(db,user.id,e.id,'plan:write'):published(db,e,user.id,True)
    return ok(di.configuration(db,e),e)
@router.put('/events/{event_id}/insight-configuration')
def insight_configure(event_id:str,body:di.Configuration,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'insight.configure',idempotency_key,if_match,body.model_dump(),lambda e:di.configure(db,user.id,e,body),True)
@router.put('/events/{event_id}/insight-responses/me')
def insight_respond(event_id:str,body:di.Response,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'insight.respond',idempotency_key,if_match,body.model_dump(),lambda e:di.respond(db,user.id,e,body))
@router.delete('/events/{event_id}/insight-responses/me/consent')
def insight_revoke(event_id:str,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'insight.revoke',idempotency_key,if_match,{},lambda e:di.revoke(db,user.id,e))
@router.get('/events/{event_id}/dynamic-insights')
def dynamic_insights(event_id:str,filters:str|None=None,user=USER,db=DB):
    e=db.get(Event,event_id)
    if not e:missing()
    return ok(di.aggregate(db,user.id,e,filters),e)

class ConfirmCondition(StrictModel):
    expected_revision:int=Field(ge=1)
    reason:str=Field(min_length=1,max_length=2000)
@router.post('/events/{event_id}/recovery/issues/{issue_id}/confirm')
def confirm_blocking_condition(event_id:str,issue_id:str,body:ConfirmCondition,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        from app.execution.models import WorkIssue
        from app.execution.service import record
        from app.api.errors import DomainError
        row=db.get(WorkIssue,issue_id)
        if not row or row.event_id!=e.id:missing()
        if row.version!=body.expected_revision or row.plan_id!=e.active_plan_id:raise DomainError('stale_source','Review current issue and plan')
        if row.content.get('condition_cleared'):raise DomainError('cleared_condition','Cannot confirm a cleared blocker')
        record(db,user.id,e,row,'issue.confirm',{**row.content,'blocking':True,'confirmed_blocking_condition':{'reason':body.reason,'actor_id':user.id}},'verified','inconclusive',body.reason)
        return {'issue_id':row.id,'revision':row.version,'condition_confirmed':True}
    return write(db,user,event_id,'recovery.confirm:'+issue_id,idempotency_key,if_match,body.model_dump(),apply,True)

@router.get('/events/{event_id}/insight-responses/me')
def insight_own_response(event_id:str,user=USER,db=DB):
    e=db.get(Event,event_id)
    if not e:missing()
    published(db,e,user.id,True)
    row=di.latest(db,e.id,'insight.response',user.id)
    return ok({'response':{'revision':row.sequence,**row.content} if row else None},e)

from app.recovery import lifecycle as rl
@router.post('/events/{event_id}/recovery/alternatives')
def recovery_create(event_id:str,body:rl.Alternative,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'recovery.create',idempotency_key,if_match,body.model_dump(mode='json'),lambda e:rl.create(db,user.id,e,body),True)
@router.get('/events/{event_id}/recovery/alternatives')
def recovery_list(event_id:str,user=USER,db=DB):
    from sqlalchemy import select
    from app.execution.models import CoordinationRecord
    e=require(db,user.id,event_id,'plan:write');require(db,user.id,event_id,'source:private')
    return ok({'items':[rl.view(db,user.id,e,r) for r in db.scalars(select(CoordinationRecord).where(CoordinationRecord.event_id==e.id,CoordinationRecord.kind=='recovery'))]},e)
@router.post('/events/{event_id}/recovery/alternatives/{recovery_id}/review')
def recovery_review(event_id:str,recovery_id:str,body:rl.Decision,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'recovery.review:'+recovery_id,idempotency_key,if_match,body.model_dump(),lambda e:rl.review(db,user.id,e,recovery_id,body),True)
@router.post('/events/{event_id}/recovery/alternatives/{recovery_id}/activate')
def recovery_activate(event_id:str,recovery_id:str,body:rl.Activate,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'recovery.activate:'+recovery_id,idempotency_key,if_match,body.model_dump(),lambda e:rl.activate(db,user.id,e,recovery_id,body),True)
@router.get('/events/{event_id}/recovery/offers/me')
def recovery_offers(event_id:str,user=USER,db=DB):
    from sqlalchemy import select
    from app.execution.models import CoordinationRecord
    from app.participation.models import AssignmentTerms,AssignmentConsent
    e=db.get(Event,event_id)
    if not e:missing()
    published(db,e,user.id,True);items=[]
    for r in db.scalars(select(CoordinationRecord).where(CoordinationRecord.event_id==e.id,CoordinationRecord.kind=='recovery')):
        if r.content['status'] not in ('approved','conditionally_approved'):continue
        for aid,v in r.content['reconfirmations'].items():
            if v['account_id']!=user.id:continue
            t=db.get(AssignmentTerms,v['terms_id']);c=db.scalar(select(AssignmentConsent).where(AssignmentConsent.terms_id==t.id))
            items.append({'recovery_id':r.id,'assignment_id':aid,'terms':t.content,'terms_key':t.digest,'expires_at':t.expires_at.isoformat(),'decision':c.decision if c else None})
    return ok({'items':items},e)
@router.post('/events/{event_id}/recovery/alternatives/{recovery_id}/assignments/{assignment_id}/consent')
def recovery_consent(event_id:str,recovery_id:str,assignment_id:str,body:rl.Consent,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'recovery.consent:'+assignment_id,idempotency_key,if_match,body.model_dump(),lambda e:rl.consent(db,user.id,e,recovery_id,assignment_id,body))

from fastapi import Request,BackgroundTasks
class RecoveryAI(StrictModel):
    issue_id:str
    message:str=Field(default='',max_length=2000)
@router.post('/events/{event_id}/recovery/ai-runs')
def recovery_ai(event_id:str,body:RecoveryAI,request:Request,background_tasks:BackgroundTasks,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    from app.ai.service import request_run
    result=write(db,user,event_id,'recovery.ai',idempotency_key,if_match,body.model_dump(),lambda e:request_run(db,user.id,e,'recovery',body.message,request.app.state.planning_adapter,body.issue_id),True)
    if getattr(request.app.state.planning_adapter,'live_provider',False):
        from app.ai.service import work_ai_once
        background_tasks.add_task(work_ai_once,request.app.state.session_factory,request.app.state.planning_adapter,run_id=result['data']['run_id'])
    return result

# Prompt 7: existing recovery workspace extensions, all mutation through event-locked write.
from app.recovery import workspace as rw
@router.post('/events/{event_id}/recovery/workspaces')
def recovery_workspace_open(event_id:str,body:rw.Open,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'recovery.workspace_open',idempotency_key,if_match,body.model_dump(),lambda e:rw.open_workspace(db,user.id,e,body),True)
@router.get('/events/{event_id}/recovery/workspaces/{workspace_id}')
def recovery_workspace_read(event_id:str,workspace_id:str,user=USER,db=DB):
    e=require(db,user.id,event_id,'plan:write');require(db,user.id,event_id,'source:private');return ok(rw.view(db,user.id,e,rw.get(db,e,workspace_id)),e)
@router.post('/events/{event_id}/recovery/workspaces/{workspace_id}/local-review')
def recovery_local_review(event_id:str,workspace_id:str,body:rw.LocalReview,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'recovery.local:'+workspace_id,idempotency_key,if_match,body.model_dump(),lambda e:rw.local_review(db,user.id,e,workspace_id,body),True)
@router.post('/events/{event_id}/recovery/workspaces/{workspace_id}/submit')
def recovery_workspace_submit(event_id:str,workspace_id:str,body:rw.Finalize,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'recovery.submit:'+workspace_id,idempotency_key,if_match,body.model_dump(),lambda e:rw.finalize(db,user.id,e,workspace_id,body),True)
@router.post('/events/{event_id}/recovery/workspaces/{workspace_id}/communication')
def recovery_communication(event_id:str,workspace_id:str,body:rw.Communication,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'recovery.communication:'+workspace_id,idempotency_key,if_match,body.model_dump(),lambda e:rw.communicate(db,user.id,e,workspace_id,body),True)
@router.post('/events/{event_id}/recovery/alternatives/{recovery_id}/outcome')
def recovery_outcome(event_id:str,recovery_id:str,body:rw.Outcome,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'recovery.outcome:'+recovery_id,idempotency_key,if_match,body.model_dump(),lambda e:rw.outcome(db,user.id,e,recovery_id,body),True)
@router.get('/notifications')
def notifications(user=USER,db=DB):
    from sqlalchemy import select
    from app.execution.models import CoordinationRecord
    rows=db.scalars(select(CoordinationRecord).where(CoordinationRecord.kind=='recovery_notice',CoordinationRecord.content['recipient_id'].astext==user.id))
    items=[]
    for row in rows:
        e=db.get(Event,row.event_id)
        try:published(db,e,user.id,True)
        except Exception:continue
        items.append({'id':row.id,'event_id':e.id,**row.content})
    return {'data':{'items':items},'meta':{}}

class DataClass(StrictModel):
    data_class:Literal['real','synthetic']
    reason:str=Field(min_length=8,max_length=2000)
@router.post('/events/{event_id}/memory/data-class')
def memory_data_class(event_id:str,body:DataClass,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        import json
        from app.api.errors import DomainError
        from app.shared.audit import audit
        text=json.dumps(e.draft_form).lower()
        if body.data_class=='real' and (e.memory_data_class=='synthetic' or any(x in text for x in ('synthetic','integration verification','integration-test','fictional'))):raise DomainError('synthetic_memory','Known synthetic event cannot become a trusted real-world source',422)
        e.memory_data_class=body.data_class;e.version+=1;audit(db,user.id,e.id,'memory.data_class',e.id,data_class=body.data_class,reason=body.reason);return {'data_class':body.data_class}
    return write(db,user,event_id,'memory.data_class',idempotency_key,if_match,body.model_dump(),apply,True)
