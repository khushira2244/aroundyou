from app.shared.models import AuditEvent

def audit(session, actor_id, event_id, operation, target_id, **details):
    session.add(AuditEvent(actor_id=actor_id,event_id=event_id,operation=operation,target_id=target_id,details=details))
