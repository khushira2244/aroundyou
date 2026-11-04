from pydantic import Field
from app.memory.schemas import StrictModel
from app.planning.schemas import Schedule
from app.recovery.lifecycle import fingerprint
from app.recovery.service import impact
from app.api.errors import DomainError
class RecoveryOption(StrictModel):
    title:str=Field(min_length=1,max_length=200)
    rationale:str=Field(min_length=1,max_length=2000)
    schedules:dict[str,Schedule]=Field(default_factory=dict,max_length=50)
    patches:dict[str,dict]=Field(default_factory=dict,max_length=30)
    trade_offs:list[str]=Field(default_factory=list,max_length=10)
    reconfirmation_work_ids:list[str]=Field(default_factory=list,max_length=30)
    assumptions:list[str]=Field(max_length=30)
    risks:list[str]=Field(max_length=30)
    unknowns:list[str]=Field(max_length=30)
    conditions:list[str]=Field(max_length=30)
    cited_issue_ids:list[str]=Field(min_length=1,max_length=30)
class RecoveryAdvice(StrictModel):
    alternatives:list[RecoveryOption]=Field(min_length=0,max_length=3)
    questions:list[str]=Field(max_length=30)

def context(db,actor,event,issue_id):
    scope=impact(db,actor,event,[issue_id],event.active_plan_id)
    from app.resources.service import projection
    from app.participation.models import Assignment,AssignmentTerms
    from sqlalchemy import select
    affected=set(scope['scope']['affected_work_ids']);commitments=[]
    for a in db.scalars(select(Assignment).where(Assignment.event_id==event.id)):
        t=db.get(AssignmentTerms,a.current_terms_id)
        if t and affected.intersection(t.content['work_ids']):commitments.append({'assignment_id':a.id,'status':a.status,'terms':t.content})
    from app.execution.models import WorkIssue
    issue=db.get(WorkIssue,issue_id)
    operational={k:issue.content.get(k) for k in ('category','work_ids','resource_ids','resource_count','occurred_at','can_continue','severity')}
    if not issue.content.get('private_personal'):operational['description']=issue.content['description']
    return {'resources':[r for r in projection(db,event,actor) if r['id'] in scope['scope']['affected_resource_ids']],'commitments':commitments,'issue':operational,'issue_ids':[issue_id],'impact':scope,'fingerprint':fingerprint(db,event,[issue_id]),'notice':'Existing resources and commitments are constraints, not model-created capacity. Personal explanations excluded.'}

def validate_context(db,actor,event,c):
    if c['fingerprint']!=fingerprint(db,event,c['issue_ids']):raise DomainError('stale_proposal','Recovery inputs changed')

def validate_output(payload,authoritative,full_plan=None):
    from copy import deepcopy
    from app.recovery.workspace import apply_patches
    payload=RecoveryAdvice.model_validate(payload).model_dump(mode='json');c=authoritative['participation_and_resources']
    allowed=set(c['impact']['scope']['affected_work_ids'])-set(c['impact']['scope']['preserved_complete_ids'])
    for option in payload['alternatives']:
        if not set(option['schedules'])<=allowed or not set(option['cited_issue_ids'])<=set(c['issue_ids']):raise DomainError('invalid_model_output','Recovery option cites unpermitted work or issues',422)
        if not set(option['reconfirmation_work_ids'])<=allowed:raise DomainError('invalid_model_output','Unknown reconfirmation work',422)
        patches=deepcopy(option['patches'])
        for wid,schedule in option['schedules'].items():
            key='work:'+wid
            if 'schedule' in patches.get(key,{}):raise DomainError('invalid_model_output','Duplicate schedule change',422)
            patches.setdefault(key,{})['schedule']=schedule
        apply_patches(deepcopy(full_plan or authoritative['plan']),patches,c['impact']['scope'])
        # Demand edits never establish staffing, inventory or accepted terms.
        option['conditions']=list(dict.fromkeys(option['conditions']+['Human review and deterministic activation checks required; staffing and resource feasibility are not established by this advice.']))

    return payload
