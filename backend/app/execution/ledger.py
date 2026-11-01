from app.execution.service import *
from app.execution.models import ResourceOperation
from app.resources.models import ResourceReservation
from app.resources.service import D

def operations(db,e,resource_id=None,reservation_id=None):
    query=select(ResourceOperation).where(ResourceOperation.event_id==e.id)
    if resource_id:query=query.where(ResourceOperation.resource_id==resource_id)
    if reservation_id:query=query.where(ResourceOperation.reservation_id==reservation_id)
    rows=list(db.scalars(query));reversed_ids={x.reverses_id for x in rows if x.kind=='reversal'}
    return [x for x in rows if x.kind!='reversal' and x.id not in reversed_ids]
def amounts(db,e,resource_id=None,reservation_id=None):
    rows=operations(db,e,resource_id,reservation_id);consumed=sum((D(x.quantity) for x in rows if x.kind=='consume'),D(0));issued=sum((D(x.quantity) for x in rows if x.kind=='checkout'),D(0));returned=sum((D(x.quantity) for x in rows if x.kind=='return'),D(0))
    return consumed,issued,returned

def reconcile(db,actor,e,b,kind):
    if not owner(db,actor,e):missing()
    require_state(b.confirm,'Explicit human verification of actual quantity required')
    r=db.get(WorkReport,b.report_id) if kind=='return' else get_report(db,actor,e,b.report_id)
    if not r or r.event_id!=e.id:missing()
    if kind!='return':require_state(r.content['review_status'] in ('submitted','under_review','accepted'),'Reconcile actual submitted report usage')
    u=next((x for x in r.content['resource_usage'] if x['id']==b.usage_id),None);res=db.get(ResourceReservation,b.reservation_id)
    require_state(u and res and res.event_id==e.id and res.resource_id==u['resource_id'] and res.work_id==r.work_id and res.plan_id==r.plan_id,'Match exact work, resource, plan and reservation')
    require_state(res.unit==u['unit'],'Exact units required')
    existing=db.scalar(select(ResourceOperation).where(ResourceOperation.event_id==e.id,ResourceOperation.reference==b.reference))
    if existing:
        require_state(existing.kind==kind and existing.reservation_id==res.id and existing.report_id==r.id and existing.usage_id==u['id'] and D(existing.quantity)==b.quantity,'Reference already used for different operation');return {'operation_id':existing.id,'replayed':True}
    consumed,issued,returned=amounts(db,e,reservation_id=res.id);resource=next(x for x in plan(db,e,actor)['resources'] if x['id']==res.resource_id)
    previous=operations(db,e);used=sum((D(x.quantity) for x in previous if x.report_id==r.id and x.usage_id==u['id'] and x.kind==kind),D(0))
    require_state(used+b.quantity<=D(u['quantity']),'Cannot reconcile more than original declared quantity')
    if kind=='return':require_state(resource['kind']=='equipment' and b.quantity<=issued-returned,'Only outstanding equipment may be returned')
    else:
        require_state(res.status=='reserved' and b.quantity<=D(res.quantity)-consumed-issued+returned,'Insufficient remaining reservation')
        require_state((kind=='checkout' and resource['kind']=='equipment') or (kind=='consume' and resource['kind']=='consumable'),'Consumables and reusable equipment have different operations')
        from app.resources.service import totals
        onhand,_,_=totals(db,e,res.resource_id);require_state(onhand>=b.quantity,'Verified stock insufficient')
    row=ResourceOperation(id=uid(),event_id=e.id,reservation_id=res.id,report_id=r.id,resource_id=res.resource_id,report_revision=r.version,usage_id=u['id'],kind=kind,quantity=b.quantity,reference=b.reference,created_by=actor);db.add(row);db.flush();e.version+=1
    from app.participation.service import source
    source(db,actor,e,row.id,'resource.'+kind,{'operation_id':row.id,'report_id':r.id,'report_revision':r.version,'reservation_id':res.id,'resource_id':res.resource_id,'quantity':str(b.quantity),'kind':kind,'notice':'Human-recorded operational verification, not event impact'})
    return {'operation_id':row.id,'verified':True}
def reverse(db,actor,e,opid,reason):
    if not owner(db,actor,e):missing()
    row=db.get(ResourceOperation,opid)
    if not row or row.event_id!=e.id:missing()
    require_state(row.kind=='consume' and row.id in {x.id for x in operations(db,e)},'Only unreversed consumption may be reversed; equipment uses explicit returns')
    reversal=ResourceOperation(id=uid(),event_id=e.id,reservation_id=row.reservation_id,report_id=row.report_id,resource_id=row.resource_id,report_revision=row.report_revision,usage_id=row.usage_id,kind='reversal',quantity=row.quantity,reference='reversal:'+row.id,reverses_id=row.id,created_by=actor);db.add(reversal);db.flush();e.version+=1
    from app.participation.service import source
    source(db,actor,e,row.id,'resource.reverse_usage',{'operation_id':row.id,'reversal_id':reversal.id,'reason':reason});return {'reversal_id':reversal.id}
