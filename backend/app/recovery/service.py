from sqlalchemy import select
from app.execution.models import WorkIssue,WorkExecution
from app.execution.service import plan
from app.api.errors import DomainError
from app.recovery.impact import affected_scope
from app.shared.types import digest


def impact(db,actor,event,issue_ids,expected_plan_id):
    if event.active_plan_id!=expected_plan_id:raise DomainError('stale_plan','Reload current authoritative plan')
    current=plan(db,event,actor,True);issues=[]
    for iid in issue_ids:
        row=db.get(WorkIssue,iid)
        if not row or row.event_id!=event.id:raise DomainError('not_found','Issue inaccessible',404)
        if row.plan_id!=expected_plan_id:raise DomainError('stale_plan','Issue belongs to an earlier plan')
        # Human investigation is not proof that the underlying condition cleared.
        if row.content.get('condition_cleared') or not row.content.get('confirmed_blocking_condition'):
            raise DomainError('unconfirmed_blocker','Requires a human-reviewed uncleared condition')
        issues.append(row)
    completed=[r.work_id for r in db.scalars(select(WorkExecution).where(WorkExecution.event_id==event.id,WorkExecution.plan_id==expected_plan_id)) if r.content.get('status')=='completed']
    scope=affected_scope(current,[i.work_id for i in issues],completed)
    sources=[{'issue_id':i.id,'revision':i.version,'digest':digest(i.content)} for i in issues]
    return {'plan_id':expected_plan_id,'scope':scope,'sources':sources,'digest':digest({'plan':expected_plan_id,'scope':scope,'sources':sources}),
        'activation_available':False,'model_status':'unavailable'}
