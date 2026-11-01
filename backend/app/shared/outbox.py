from sqlalchemy import select
from app.shared.models import OutboxEvent
from app.shared.types import now
from app.shared.unit_of_work import unit_of_work
from app.memory.schemas import ExtractionRequest
from app.memory.service import enqueue
from app.api.errors import DomainError

def dispatch_one(factory):
    with unit_of_work(factory) as session:
        event=session.scalar(select(OutboxEvent).where(OutboxEvent.delivered_at.is_(None)).order_by(OutboxEvent.created_at,OutboxEvent.id).with_for_update(skip_locked=True).limit(1))
        if not event: return False
        try:
            # Savepoint prevents a failed projection from partially enqueuing a job.
            with session.begin_nested():
                enqueue(session,event.actor_id,event.event_id,ExtractionRequest.model_validate(event.payload))
        except DomainError as exc:
            if exc.code not in ("stale_source","not_found"): raise
            # Old/revoked capture is intentionally not retried with broader authority.
        event.delivered_at=now()
        return True
