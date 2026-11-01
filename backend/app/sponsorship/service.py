from copy import deepcopy
from decimal import Decimal
from sqlalchemy import select,text
from app.sponsorship.models import Organization,OrganizationMembership,SupportOffer,SupportFulfillment,SupportOfferRevision
from app.sponsorship.schemas import OrganizationProfile
from app.participation.service import published,require_state,source
from app.resources.service import find_resource,totals,D
from app.events.models import Event
from app.shared.types import uid
from app.shared.audit import audit
from app.api.errors import DomainError,missing

def member(session,actor,organization_id):
    membership=session.scalar(select(OrganizationMembership).where(OrganizationMembership.organization_id==organization_id,OrganizationMembership.account_id==actor))
    if not membership:missing()
    return session.get(Organization,organization_id)

def save_organization(session,actor,body):
    if body.organization_id:session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':'organization:'+body.organization_id})
    org=member(session,actor,body.organization_id) if body.organization_id else None
    if org and org.version!=body.expected_version:raise DomainError('stale_version','Reload organization profile version')
    if not org:
        org=Organization(id=uid(),profile={});session.add(org);session.flush();session.add(OrganizationMembership(organization_id=org.id,account_id=actor));session.flush()
    org.profile=body.profile.model_dump();org.version+=1
    audit(session,actor,None,'organization.profile',org.id,version=org.version)
    return {'organization_id':org.id,'version':org.version}

def complete_organization(session,actor,organization_id):
    org=member(session,actor,organization_id);p=org.profile
    require_state(all(p.get(k) for k in ('name','type','description','contact_name','email','city','country','focus','capabilities','coverage')),'Complete organization request first')
    org.status='registered_unverified';org.version+=1
    audit(session,actor,None,'organization.registration_request',org.id,version=org.version)
    return {'organization_id':org.id,'status':org.status,'verified':False}

def own_offer(session,actor,event,offer_id):
    row=session.get(SupportOffer,offer_id)
    if not row or row.event_id!=event.id or row.account_id!=actor:missing()
    if row.organization_id:member(session,actor,row.organization_id)
    return row

def save_offer(session,actor,event,body):
    release=published(session,event,actor,True);r=find_resource(session,event,body.resource_id,actor)
    if body.organization_id:require_state(member(session,actor,body.organization_id).status=='registered_unverified','Complete organization onboarding first')
    require_state(body.support_type in {'consumable':['materials'],'equipment':['equipment'],'service':['services','expertise','volunteer_support'],'facility':['services'],'funding':['funding']}[r['kind']],'Support type must match requirement kind')
    require_state(body.unit==r['unit'],'Offers require exact requirement units; no implicit conversion')
    if body.delivery_date:__import__('datetime').date.fromisoformat(body.delivery_date)
    row=own_offer(session,actor,event,body.offer_id) if body.offer_id else None
    if row:require_state(row.status in ('draft','pledged'),'Accepted support must be withdrawn/reviewed before revised terms')
    else:
        row=SupportOffer(id=uid(),event_id=event.id,account_id=actor,organization_id=body.organization_id,plan_id=release.plan_id,content={});session.add(row);session.flush()
    row.content=body.model_dump(mode='json',exclude={'offer_id','submit'});row.organization_id=body.organization_id;row.plan_id=release.plan_id;row.status='pledged' if body.submit else 'draft';row.version+=1;event.version+=1
    session.add(SupportOfferRevision(event_id=event.id,offer_id=row.id,version=row.version,content={'terms':row.content,'status':row.status,'plan_id':row.plan_id},created_by=actor))
    if row.status!='draft':source(session,actor,event,row.id,'support.offer',{'offer_id':row.id,'resource_id':r['id'],'version':row.version,'quantity':str(body.quantity),'status':row.status,'notice':'Promise is not inventory, payment or completed work'})
    return {'offer':offer_dto(session,row)}

def transition(session,actor,event,row,action):
    if action=='submit':require_state(row.status=='draft','Only drafts can be submitted');row.status='pledged'
    elif action in ('accept','reject'):
        require_state(row.status=='pledged' and row.plan_id==published(session,event,actor,True).plan_id,'Review current pledged support');row.status='accepted' if action=='accept' else 'rejected'
    elif action=='withdraw':
        require_state(row.status in ('draft','pledged'),'Only unaccepted offers may be withdrawn; accepted commitments require organizer change review');row.status='withdrawn'
    row.version+=1;event.version+=1
    session.add(SupportOfferRevision(event_id=event.id,offer_id=row.id,version=row.version,content={'terms':row.content,'status':row.status,'plan_id':row.plan_id},created_by=actor))
    source(session,actor,event,row.id,'support.'+action,{'offer_id':row.id,'version':row.version,'status':row.status,'notice':'No stock or payment effect'})
    return {'offer':offer_dto(session,row)}

def report(session,actor,event,row,body):
    require_state(row.status=='accepted','Only accepted support can be reported')
    reported=sum((D(x.quantity) for x in session.scalars(select(SupportFulfillment).where(SupportFulfillment.offer_id==row.id))),D(0))
    require_state(reported+body.quantity<=D(row.content['quantity']),'Report exceeds accepted amount')
    f=SupportFulfillment(id=uid(),event_id=event.id,offer_id=row.id,quantity=body.quantity,reference=body.reference,evidence_reference=body.evidence_reference,created_by=actor);session.add(f);session.flush();event.version+=1
    source(session,actor,event,f.id,'support.report',{'fulfillment_id':f.id,'offer_id':row.id,'quantity':str(body.quantity),'state':'reported_unverified','outcome':'unknown'})
    return {'fulfillment_id':f.id,'verified':False}

def offer_dto(session,row):
    from app.resources.models import ResourceTransaction
    reports=list(session.scalars(select(SupportFulfillment).where(SupportFulfillment.offer_id==row.id)))
    credited=sum((D(x.quantity) if x.kind=='receipt' else -D(x.quantity) for x in session.scalars(select(ResourceTransaction).where(ResourceTransaction.offer_id==row.id))),D(0));reported=sum((D(x.quantity) for x in reports),D(0))
    org=session.get(Organization,row.organization_id) if row.organization_id else None;event=session.get(Event,row.event_id)
    resource=find_resource(session,event,row.content['resource_id'],row.account_id)
    status='completed' if credited>=D(row.content['quantity']) else 'partially_fulfilled' if credited else 'delivered_unverified' if reported else 'submitted' if row.status=='pledged' else row.status
    return {'id':row.id,'event_id':row.event_id,'organization_id':row.organization_id or '',**row.content,'resource_requirement_id':row.content['resource_id'],'representative_account_id':row.account_id,'quantity':float(row.content['quantity']),'estimated_value':float(row.content['estimated_value']) if row.content.get('estimated_value') is not None else None,'organization_label':org.profile.get('name','') if org else 'Individual supporter','event_title':event.title,'requirement_title':resource['title'],'status':row.status,'version':row.version,'verified':float(credited),'reported':float(reported),'fulfillment_status':status}
