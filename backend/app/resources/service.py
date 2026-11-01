from decimal import Decimal
from sqlalchemy import select
from app.resources.models import ResourceTransaction,ResourceReservation
from app.sponsorship.models import SupportOffer,SupportFulfillment
from app.participation.service import published,require_state,source
from app.shared.types import uid
from app.api.errors import DomainError,missing
D=lambda x:Decimal(str(x))
def requirements(session,event,actor=None):return published(session,event,actor).snapshot['plan']['resources']
def find_resource(session,event,resource_id,actor=None):
    r=next((x for x in requirements(session,event,actor) if x['id']==resource_id),None)
    if not r:missing()
    return r

def totals(session,event,resource_id):
    receipts=list(session.scalars(select(ResourceTransaction).where(ResourceTransaction.event_id==event.id,ResourceTransaction.resource_id==resource_id)))
    received=sum((D(x.quantity) if x.kind=='receipt' else -D(x.quantity) for x in receipts),D(0))
    reserved=sum((D(x.quantity) for x in session.scalars(select(ResourceReservation).where(ResourceReservation.event_id==event.id,ResourceReservation.resource_id==resource_id,ResourceReservation.status=='reserved'))),D(0))
    from app.execution.ledger import amounts
    consumed,issued,returned=amounts(session,event,resource_id=resource_id)
    adjusted_reserved=D(0)
    for res in session.scalars(select(ResourceReservation).where(ResourceReservation.event_id==event.id,ResourceReservation.resource_id==resource_id,ResourceReservation.status=='reserved')):
        c,i,r=amounts(session,event,reservation_id=res.id);adjusted_reserved+=D(res.quantity)-c-i+r
    return received-consumed-issued+returned,adjusted_reserved,receipts

def receipt(session,actor,event,body):
    r=find_resource(session,event,body.resource_id,actor)
    require_state(r['kind']!='funding','Funding references do not create inventory or payment settlement')
    require_state(body.unit==r['unit'],'Unsupported unit conversion')
    offer=session.get(SupportOffer,body.offer_id) if body.offer_id else None
    fulfillment=session.get(SupportFulfillment,body.fulfillment_id) if body.fulfillment_id else None
    if body.offer_id:
        if not offer or offer.event_id!=event.id:missing()
        require_state(offer.status=='accepted' and offer.content['resource_id']==body.resource_id and offer.content['unit']==body.unit,'Receipt requires the accepted matching offer')
        require_state(offer.content['support_type'] in ('materials','equipment','services','expertise'),'Funding/volunteers do not create resource stock')
        if not fulfillment and session.scalar(select(SupportFulfillment.id).where(SupportFulfillment.offer_id==offer.id)):raise DomainError('fulfillment_required','Link the exact reported delivery before receipt verification')
        credited=sum((D(x.quantity) if x.kind=='receipt' else -D(x.quantity) for x in session.scalars(select(ResourceTransaction).where(ResourceTransaction.offer_id==offer.id))),D(0))
        require_state(credited+body.quantity<=D(offer.content['quantity']),'Receipt exceeds accepted pledge')
    if fulfillment:
        if not offer or fulfillment.offer_id!=offer.id or fulfillment.event_id!=event.id:missing()
        require_state(D(fulfillment.quantity)==body.quantity,'Verify the exact reported quantity')
    elif body.fulfillment_id:missing()
    if session.scalar(select(ResourceTransaction.id).where(ResourceTransaction.event_id==event.id,ResourceTransaction.reference==body.reference)):raise DomainError('duplicate_receipt','Receipt reference already credited')
    row=ResourceTransaction(id=uid(),event_id=event.id,resource_id=r['id'],offer_id=offer.id if offer else None,fulfillment_id=fulfillment.id if fulfillment else None,quantity=body.quantity,unit=body.unit,reference=body.reference,evidence_reference=body.evidence_reference,kind='receipt',created_by=actor)
    session.add(row);session.flush();event.version+=1
    source(session,actor,event,row.id,'resource.receipt',{'resource_id':r['id'],'quantity':str(body.quantity),'unit':body.unit,'receipt_id':row.id,'evidence_reference':body.evidence_reference,'notice':'Human-recorded receipt, not verified work completion'})
    return {'receipt_id':row.id,'verified_received':float(totals(session,event,r['id'])[0]),'payment_settled':False}

def reserve(session,actor,event,body):
    release=published(session,event,actor,True);require_state(body.expected_plan_id==release.plan_id,'Reserve against current plan')
    r=find_resource(session,event,body.resource_id,actor)
    works={x['id']:x for x in release.snapshot['plan']['work']}
    require_state(body.work_id in works and body.resource_id in works[body.work_id]['resource_requirement_ids'],'Resource must be linked to this work')
    require_state(r['kind']!='funding','Funding references do not create inventory or payment settlement')
    require_state(body.unit==r['unit'],'Unsupported unit conversion')
    received,reserved,_=totals(session,event,r['id']);require_state(received-reserved>=body.quantity,'Insufficient verified unreserved stock')
    row=ResourceReservation(id=uid(),event_id=event.id,resource_id=r['id'],work_id=body.work_id,plan_id=release.plan_id,quantity=body.quantity,unit=body.unit);session.add(row);session.flush();event.version+=1
    source(session,actor,event,row.id,'resource.reserve',{'resource_id':r['id'],'reservation_id':row.id,'quantity':str(body.quantity),'work_id':body.work_id,'notice':'Reservation is not consumption'})
    return {'reservation_id':row.id,'available':float(received-reserved-body.quantity)}

def release(session,actor,event,reservation_id):
    row=session.get(ResourceReservation,reservation_id)
    if not row or row.event_id!=event.id:missing()
    from app.execution.ledger import amounts
    _,issued,returned=amounts(session,event,reservation_id=row.id);require_state(issued==returned,'Return checked-out equipment before releasing reservation')
    require_state(row.status=='reserved','Reservation already released');row.status='released';row.version+=1;event.version+=1
    source(session,actor,event,row.id,'resource.release',{'reservation_id':row.id,'status':'released'})
    return {'released':True}

def correct_receipt(session,actor,event,receipt_id,reason):
    row=session.get(ResourceTransaction,receipt_id)
    if not row or row.event_id!=event.id:missing()
    require_state(row.kind=='receipt','Only receipts can be reversed')
    require_state(not session.scalar(select(ResourceTransaction.id).where(ResourceTransaction.reverses_id==row.id)),'Receipt already corrected')
    received,reserved,_=totals(session,event,row.resource_id);require_state(received-D(row.quantity)>=reserved,'Release reservations before correcting received stock')
    correction=ResourceTransaction(id=uid(),event_id=event.id,resource_id=row.resource_id,offer_id=row.offer_id,quantity=row.quantity,unit=row.unit,reference='correction:'+row.id,evidence_reference=reason,kind='correction',reverses_id=row.id,created_by=actor);session.add(correction);session.flush();event.version+=1
    source(session,actor,event,row.id,'resource.correct',{'receipt_id':row.id,'correction_id':correction.id,'reason':reason,'state':'reversed'})
    return {'correction_id':correction.id}

def projection(session,event,actor=None):
    result=[]
    for r in requirements(session,event,actor):
        received,reserved,transactions=totals(session,event,r['id'])
        offers=list(session.scalars(select(SupportOffer).where(SupportOffer.event_id==event.id)))
        matching=[o for o in offers if o.content['resource_id']==r['id']]
        pledged=sum((D(o.content['quantity']) for o in matching if o.status=='pledged'),D(0));accepted=sum((D(o.content['quantity']) for o in matching if o.status=='accepted'),D(0));required=r['quantity']
        result.append({**r,'availability':'verified_receipts_only','required':required,'on_hand':float(received),'available':float(received-reserved),'reserved':float(reserved),'pledged':float(pledged),'accepted':float(accepted),'verified':float(sum((D(t.quantity) if t.kind=='receipt' else -D(t.quantity) for t in transactions),D(0))),'reported_delivery':float(sum((D(x.quantity) for o in matching for x in session.scalars(select(SupportFulfillment).where(SupportFulfillment.offer_id==o.id))),D(0))),'consumed':float(__import__('app.execution.ledger',fromlist=['amounts']).amounts(session,event,resource_id=r['id'])[0]),'reported_consumption':0,'equipment_issued':float(__import__('app.execution.ledger',fromlist=['amounts']).amounts(session,event,resource_id=r['id'])[1]),'equipment_returned':float(__import__('app.execution.ledger',fromlist=['amounts']).amounts(session,event,resource_id=r['id'])[2]),'gap':None if required is None else max(0,float(D(required)-received)),'sources':[],'transactions':[{'id':t.id,'kind':t.kind,'delta':float(t.quantity)*(1 if t.kind=='receipt' else -1),'receipt_reference':t.reference} for t in transactions]})
    return result
