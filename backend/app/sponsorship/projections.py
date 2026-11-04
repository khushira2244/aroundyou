from sqlalchemy import select
from app.sponsorship.models import Organization,OrganizationMembership,SupportOffer,SupportFulfillment
from app.sponsorship.schemas import OrganizationProfile
from app.sponsorship.service import member,offer_dto,fulfillment_credit
from app.events.models import Event
from app.access.models import User
from app.publication.models import Publication
from app.resources.service import projection
from app.participation.service import published
from app.shared.types import uid

def opportunities(session,actor):
    items=[]
    for event in session.scalars(select(Event).where(Event.current_publication_id.is_not(None),Event.lifecycle!='deleted')):
        release=session.get(Publication,event.current_publication_id)
        if release.visibility!='public':continue
        resources=projection(session,event,actor);needs=[]
        for r in resources:
            support={'consumable':'materials','equipment':'equipment','service':'services','facility':'services','funding':'funding'}[r['kind']]
            needs.append({'id':r['id'],'title':r['title'],'kind':r['kind'],'quantity':r['quantity'],'unit':r['unit'],'support_type':support,'available':r['on_hand'],'outstanding':r['gap'],'accepted':r['accepted']})
        if not needs:continue
        creator=session.get(User,event.creator_id)
        e=release.snapshot['event'];items.append({'id':event.id,'title':e['title'],'category':e['category'],'purpose':e['purpose'],'goal':e['goal'],'location':e['location'],'schedule':e['schedule'],'needs':needs,'fit':{'source':'declared_requirements','label':'Review published support needs; no model match score','verified':False},'organizer_label':creator.display_name if creator else 'Event organizer'})
    return items

def portal(session,actor,organization_id=None):
    membership=session.scalar(select(OrganizationMembership).where(OrganizationMembership.account_id==actor,OrganizationMembership.organization_id==organization_id)) if organization_id else session.scalar(select(OrganizationMembership).where(OrganizationMembership.account_id==actor).order_by(OrganizationMembership.id))
    org=member(session,actor,membership.organization_id) if membership else None
    profile=org.profile if org else OrganizationProfile().model_dump();offers=list(session.scalars(select(SupportOffer).where(SupportOffer.account_id==actor,SupportOffer.organization_id==org.id))) if org else []
    offers=[o for o in offers if (event:=session.get(Event,o.event_id)) and event.lifecycle!='deleted']
    dtos=[offer_dto(session,o) for o in offers];supported=[]
    for eid in sorted({o.event_id for o in offers if o.status=='accepted'}):
        e=session.get(Event,eid)
        if not e or e.lifecycle=='deleted':continue
        release=published(session,e,actor);ed=release.snapshot['event'];supported.append({**{k:ed[k] for k in ('id','title','category','location')},'has_verified_support':any(d['event_id']==eid and d['verified']>0 for d in dtos)})
    return {'organization':{'id':org.id if org else '', 'profile':profile,'registration_status':org.status if org else 'not_started','verified':False,'version':org.version if org else 0},'membership':{'organization_id':org.id if org else '', 'account_id':actor,'permission':membership.permission if membership else 'none'},'registration':{'step':1,'status':org.status if org else 'not_started','draft':profile},'offers':dtos,'opportunities':opportunities(session,actor),'supported_events':supported,'stats':{'submitted':sum(o.status=='pledged' for o in offers),'active_offers':sum(o.status in ('pledged','accepted') for o in offers),'accepted':sum(o.status=='accepted' for o in offers),'verified_contributions':sum(d['verified']>0 for d in dtos),'completed':sum(d['fulfillment_status']=='completed' for d in dtos),'supported_events':len(supported)},'fulfillments':[{'id':f.id,'offer_id':f.offer_id,'quantity':float(f.quantity),'reference':f.reference,'status':'verified' if fulfillment_credit(session,f) else 'reported_unverified'} for o in offers for f in session.scalars(select(SupportFulfillment).where(SupportFulfillment.offer_id==o.id))],'impact':{'verified_outputs':[],'beneficiaries':None,'waste_collected_kg':None}}
