from sqlalchemy import select
from app.access.models import EventGrant
from app.events.models import Event
from app.api.errors import missing

def allowed(session, user_id, event_id, permission):
    # Partial stage/work grants do not confer whole-event memory/source access.
    return session.scalar(select(EventGrant.id).where(EventGrant.user_id==user_id,EventGrant.event_id==event_id,EventGrant.permission==permission,EventGrant.active.is_(True),EventGrant.scope=={})) is not None

def require(session, user_id, event_id, permission):
    if not allowed(session,user_id,event_id,"event:read") or not allowed(session,user_id,event_id,permission):
        missing()
    event=session.get(Event,event_id)
    if not event: missing()
    return event
