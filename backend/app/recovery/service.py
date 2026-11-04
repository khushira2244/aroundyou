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
    direct={wid for i in issues for wid in i.content.get('work_ids',[i.work_id])}
    resource_ids={rid for i in issues for rid in i.content.get('resource_ids',[])}|{i.content['resource_count']['resource_id'] for i in issues if i.content.get('resource_count')}
    shared={w['id'] for w in current['work'] if set(w['resource_requirement_ids'])&resource_ids}
    scope=affected_scope(current,sorted(direct),completed)
    potential=shared-set(scope['affected_work_ids'])
    for item in scope['work']:
        if item['work_id'] in potential and item['classification']=='unaffected':item['classification']='potentially_impacted'
    scope['potential_work_ids']=sorted(potential)
    scope['affected_stage_ids']=sorted({w['stage_id'] for w in current['work'] if w['id'] in set(scope['affected_work_ids'])|potential})
    scope['affected_resource_ids']=sorted({r for w in current['work'] if w['id'] in scope['affected_work_ids'] for r in w['resource_requirement_ids']})
    scope['affected_role_ids']=sorted({r['id'] for r in current['roles'] if set(r['work_ids'])&set(scope['affected_work_ids'])})
    scope['digest']=digest({k:v for k,v in scope.items() if k!='digest'})
    sources=[{'issue_id':i.id,'revision':i.version,'digest':digest(i.content)} for i in issues]
    return {'plan_id':expected_plan_id,'scope':scope,'sources':sources,'digest':digest({'plan':expected_plan_id,'scope':scope,'sources':sources}),
        'activation_available':False,'model_status':'unavailable'}
