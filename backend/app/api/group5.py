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
        record(db,user.id,e,row,'issue.confirm',{**row.content,'confirmed_blocking_condition':{'reason':body.reason,'actor_id':user.id}},'verified','inconclusive',body.reason)
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

from fastapi import Request
class RecoveryAI(StrictModel):
    issue_id:str
    message:str=Field(default='',max_length=2000)
@router.post('/events/{event_id}/recovery/ai-runs')
def recovery_ai(event_id:str,body:RecoveryAI,request:Request,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    from app.ai.service import request_run
    return write(db,user,event_id,'recovery.ai',idempotency_key,if_match,body.model_dump(),lambda e:request_run(db,user.id,e,'recovery',body.message,request.app.state.planning_adapter,body.issue_id),True)
