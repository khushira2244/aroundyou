from sqlalchemy import select,func
from app.events.models import Event, ContextRevision
from app.planning.models import PlanVersion
from app.shared.models import OutboxEvent, ReviewDecision
from app.shared.types import uid, digest
from app.shared.source_resolver import decision_digest
from app.shared.audit import audit
from app.access.authorization import require, allowed
from app.api.errors import DomainError
from app.memory.schemas import Applicability, SourceRef
from app.planning.schemas import PlanContent

def lock_event(session, actor_id, event_id, permission):
    require(session,actor_id,event_id,permission)
    return session.scalar(select(Event).where(Event.id==event_id).with_for_update())

def capture(session, actor_id, event_id, ref):
    session.add(OutboxEvent(event_id=event_id,actor_id=actor_id,dedup_key=f"source:{ref.source_kind}:{ref.source_id}:{ref.source_digest}",payload={"source_refs":[ref.model_dump()],"extractor":"deterministic","schema_version":"memory-v1","purpose":"event_review"}))

def append_context(session, actor_id, event_id, text, expected_version, applicability=None, source_kind="written", access_class="private", snapshot=None):
    event=lock_event(session,actor_id,event_id,"context:write")
    if event.version!=expected_version: raise DomainError("stale_version","Event version changed")
    if not text.strip() or len(text)>12000 or source_kind not in ("written","observation","reviewed_transcript") or access_class not in ("event","private"):
        raise DomainError("invalid_context","Invalid original context",422)
    snapshot=snapshot or {}
    if len(__import__('json').dumps(snapshot,allow_nan=False))>64000:raise DomainError('context_budget_exceeded','Context history budget exceeded; start a corrected explanation',422)
    app=Applicability.model_validate(applicability or {"category":event.category}).model_dump()
    previous=session.get(ContextRevision,event.active_context_revision_id) if event.active_context_revision_id else None
    row=ContextRevision(id=uid(),event_id=event_id,sequence=(previous.sequence+1 if previous else 1),original_text=text,source_kind=source_kind,access_class=access_class,content_hash=digest({"text":text,"source_kind":source_kind,"access_class":access_class,"applicability":app,**({"snapshot":snapshot} if snapshot else {})}),applicability=app,snapshot=snapshot,supersedes_id=previous.id if previous else None,created_by=actor_id)
    session.add(row);session.flush()
    event.active_context_revision_id=row.id;event.version+=1
    ref=SourceRef(source_kind="context",source_id=row.id,source_revision=row.sequence,source_digest=row.content_hash)
    capture(session,actor_id,event_id,ref);audit(session,actor_id,event_id,"context.append",row.id)
    return row

def append_plan(session, actor_id, event_id, content, expected_version):
    event=lock_event(session,actor_id,event_id,"plan:write")
    if event.version!=expected_version or not event.active_context_revision_id: raise DomainError("stale_version","Current context/event version required")
    content=PlanContent.model_validate(content).model_dump()
    from app.resources.invariants import guard_plan
    guard_plan(session,event,content)
    previous=session.get(PlanVersion,event.active_plan_id) if event.active_plan_id else None
    row=PlanVersion(id=uid(),event_id=event_id,sequence=(session.scalar(select(func.max(PlanVersion.sequence)).where(PlanVersion.event_id==event.id)) or 0)+1,parent_id=previous.id if previous else None,context_revision_id=event.active_context_revision_id,content=content,digest=digest(content),created_by=actor_id)
    session.add(row);session.flush();event.active_plan_id=row.id;event.version+=1
    capture(session,actor_id,event_id,SourceRef(source_kind="plan",source_id=row.id,source_revision=row.sequence,source_digest=row.digest))
    audit(session,actor_id,event_id,"plan.append",row.id)
    return row

def record_observation_decision(session, actor_id, event_id, context_id, evidence_stage, outcome, criteria, note):
    event=lock_event(session,actor_id,event_id,"source:verify")
    row=session.get(ContextRevision,context_id)
    if not row or row.event_id!=event_id or row.id!=event.active_context_revision_id or row.source_kind!="observation":
        raise DomainError("invalid_provenance","Current original observation required",422)
    if row.access_class=="private" and not allowed(session,actor_id,event_id,"source:private"):
        raise DomainError("not_found","Record not found or inaccessible",404)
    if evidence_stage not in ("attempted","verified") or outcome not in ("unknown","successful","failed","mixed","inconclusive") or len(note)>4000 or len(criteria)>2000:
        raise DomainError("invalid_decision","Invalid observation decision",422)
    if outcome in ("successful","failed","mixed") and (evidence_stage!="verified" or not criteria.strip()):
        raise DomainError("unsupported_outcome","Reviewed criteria required",422)
    previous=session.scalar(select(ReviewDecision).where(ReviewDecision.event_id==event_id,ReviewDecision.subject_id==row.id,ReviewDecision.decision=="observation_review").order_by(ReviewDecision.created_at.desc()).limit(1))
    decision=ReviewDecision(id=uid(),event_id=event_id,actor_id=actor_id,supersedes_id=previous.id if previous else None,subject_kind="context",subject_id=row.id,subject_digest=row.content_hash,decision="observation_review",evidence_stage=evidence_stage,outcome=outcome,criteria=criteria,note=note)
    session.add(decision);session.flush()
    capture(session,actor_id,event_id,SourceRef(source_kind="decision",source_id=decision.id,source_revision=1,source_digest=decision_digest(decision)))
    audit(session,actor_id,event_id,"observation.review",decision.id)
    return decision
