from sqlalchemy import select
from app.resources.models import ResourceTransaction,ResourceReservation
from app.sponsorship.models import SupportOffer
from app.publication.models import Publication
from app.api.errors import DomainError

def guard_plan(session,event,content):
    release=session.get(Publication,event.current_publication_id) if event.current_publication_id else None
    if not release:return
    old={r['id']:r for r in release.snapshot['plan']['resources']};new={r['id']:r for r in content['resources']}
    protected={x.resource_id for x in session.scalars(select(ResourceTransaction).where(ResourceTransaction.event_id==event.id))}|{x.resource_id for x in session.scalars(select(ResourceReservation).where(ResourceReservation.event_id==event.id))}
    protected|={x.content['resource_id'] for x in session.scalars(select(SupportOffer).where(SupportOffer.event_id==event.id,SupportOffer.status.in_(['pledged','accepted'])))}
    for rid in protected:
        if rid not in old:continue
        if rid not in new or (new[rid]['unit'],new[rid]['kind'])!=(old[rid]['unit'],old[rid]['kind']):raise DomainError('resource_identity_conflict','A resource with promises/receipts/reservations keeps its identity and exact unit; create a different resource ID')
