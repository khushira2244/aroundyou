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
    assumptions:list[str]=Field(max_length=30)
    risks:list[str]=Field(max_length=30)
    unknowns:list[str]=Field(max_length=30)
    conditions:list[str]=Field(max_length=30)
    cited_issue_ids:list[str]=Field(min_length=1,max_length=30)
class RecoveryAdvice(StrictModel):
    alternatives:list[RecoveryOption]=Field(min_length=1,max_length=5)
    questions:list[str]=Field(max_length=30)

def context(db,actor,event,issue_id):
    scope=impact(db,actor,event,[issue_id],event.active_plan_id)
    from app.resources.service import projection
    from app.participation.models import Assignment,AssignmentTerms
    from sqlalchemy import select
    commitments=[{'assignment_id':a.id,'status':a.status,'terms':db.get(AssignmentTerms,a.current_terms_id).content} for a in db.scalars(select(Assignment).where(Assignment.event_id==event.id))]
    return {'resources':projection(db,event,actor),'commitments':commitments,'issue_ids':[issue_id],'impact':scope,'fingerprint':fingerprint(db,event,[issue_id]),'notice':'Existing resources and commitments are constraints, not model-created capacity.'}

def validate_context(db,actor,event,c):
    if c['fingerprint']!=fingerprint(db,event,c['issue_ids']):raise DomainError('stale_proposal','Recovery inputs changed')

def validate_output(payload,authoritative):
    payload=RecoveryAdvice.model_validate(payload).model_dump(mode='json');c=authoritative['participation_and_resources']
    allowed=set(c['impact']['scope']['affected_work_ids'])-set(c['impact']['scope']['preserved_complete_ids'])
    for option in payload['alternatives']:
        if not set(option['schedules'])<=allowed or not set(option['cited_issue_ids'])<=set(c['issue_ids']):raise DomainError('invalid_model_output','Recovery option cites unpermitted work or issues',422)

    return payload
