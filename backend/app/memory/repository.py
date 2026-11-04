from sqlalchemy import select
from app.memory.models import MemoryEntry, MemorySource
from app.access.authorization import require, allowed
from app.shared.source_resolver import resolve
from app.memory.schemas import SourceRef
from app.api.errors import missing, DomainError

def source_rows(session, entry):
    return list(session.scalars(select(MemorySource).where(MemorySource.memory_entry_id==entry.id)))

def entry_access(session, actor_id, event_id, memory_id, lock=False):
    require(session,actor_id,event_id,"memory:read")
    query=select(MemoryEntry).where(MemoryEntry.id==memory_id,MemoryEntry.event_id==event_id)
    if lock: query=query.with_for_update()
    entry=session.scalar(query)
    if not entry: missing()
    sources=source_rows(session,entry)
    if not sources: missing()
    if any(s.access_class=="private" for s in sources) and not allowed(session,actor_id,event_id,"source:private"): missing()
    return entry

def current_sources(session,actor_id,entry):
    rows=source_rows(session,entry)
    if not rows: raise DomainError("invalid_provenance","Missing source lineage")
    return [resolve(session,actor_id,entry.event_id,SourceRef(source_kind=r.source_kind,source_id=r.source_id,source_revision=r.source_revision,source_digest=r.source_digest)) for r in rows]

def eligible(session,actor_id,entry):
    if entry.lifecycle!="published": return False
    if entry.kind=='lesson':
        from app.events.models import Event
        event=session.get(Event,entry.event_id)
        if not event or event.memory_data_class!='real':return False
    try: current_sources(session,actor_id,entry)
    except DomainError: return False
    return True
