from sqlalchemy import select
from app.events.models import Event
from app.access.authorization import require
from app.shared.idempotency import execute_once
from app.api.errors import DomainError

def command(session,actor,event_id,permission,operation,key,payload,version,action):
    require(session,actor,event_id,permission)
    def apply():
        event=session.scalar(select(Event).where(Event.id==event_id).with_for_update())
        if version is None or str(event.version)!=str(version).strip('"'):
            raise DomainError('stale_version','If-Match must match the current event version')
        result=action(event)
        session.flush()
        return result
    return execute_once(session,actor,event_id,operation,key,{'payload':payload,'version':version},apply)
