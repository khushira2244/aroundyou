from sqlalchemy import select, text
from app.shared.models import IdempotencyRecord
from app.shared.types import digest
from app.api.errors import DomainError

def execute_once(session, actor_id, scope, operation, key, payload, action):
    if not key or len(key)>128:
        raise DomainError("idempotency_required","Idempotency-Key of 1..128 characters required",422)
    # Transaction-scoped lock handles simultaneous inserts (not just existing rows).
    lock_key=f"{actor_id}:{scope}:{operation}:{key}"
    session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),{"key":lock_key})
    row=session.scalar(select(IdempotencyRecord).where(IdempotencyRecord.actor_id==actor_id,IdempotencyRecord.scope==scope,IdempotencyRecord.operation==operation,IdempotencyRecord.key==key))
    hashed=digest(payload)
    if row:
        if row.payload_hash!=hashed: raise DomainError("idempotency_conflict","Key used for a different request")
        return row.response
    result=action()
    session.add(IdempotencyRecord(actor_id=actor_id,scope=scope,operation=operation,key=key,payload_hash=hashed,response=result))
    session.flush()
    return result
