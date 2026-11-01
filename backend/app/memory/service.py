from sqlalchemy import select
from app.memory.models import MemoryEntry, MemorySource, MemoryRun
from app.memory.schemas import SourceRef, Candidate, ExtractionRequest
from app.memory.repository import entry_access, current_sources
from app.memory.projections import project
from app.shared.source_resolver import resolve
from app.shared.models import JobTask, ReviewDecision
from app.shared.types import digest, uid
from app.shared.audit import audit
from app.shared.idempotency import execute_once
from app.access.authorization import require
from app.api.errors import DomainError
from app.events.models import Event

def resolved_inputs(session, actor_id, event_id, refs):
    sources=[resolve(session,actor_id,event_id,r) for r in refs]
    if sum(len(s.text) for s in sources)>12000:
        raise DomainError("input_budget_exceeded","Extraction input exceeds character budget",422)
    return sources

def enqueue(session, actor_id, event_id, request):
    require(session,actor_id,event_id,"memory:extract")
    resolved_inputs(session,actor_id,event_id,request.source_refs)
    body=request.model_dump()
    key=digest({"actor":actor_id,"event":event_id,"request":body})
    # Serializes deduplication across different HTTP idempotency keys and outbox delivery.
    from sqlalchemy import text
    session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"),{"k":key})
    run=session.scalar(select(MemoryRun).where(MemoryRun.event_id==event_id,MemoryRun.dedup_key==key))
    if not run:
        manifest=[r.model_dump() for r in request.source_refs]
        run=MemoryRun(id=uid(),event_id=event_id,requester_id=actor_id,purpose=request.purpose,extractor=request.extractor,schema_version=request.schema_version,dedup_key=key,source_manifest=manifest,source_manifest_digest=digest(manifest))
        session.add(run);session.flush();session.add(JobTask(run_id=run.id))
        audit(session,actor_id,event_id,"memory.extraction.request",run.id)
    return {"run_id":run.id,"status":run.status,"source_manifest_digest":run.source_manifest_digest,"candidate_ids":run.output_entry_ids,"status_url":f"/v1/events/{event_id}/memory/extractions/{run.id}"}

def validate_candidates(candidates, sources):
    if not 1<=len(candidates)<=20: raise DomainError("invalid_model_output","Candidate count outside budget",422)
    permitted={digest(s.ref.model_dump()):s for s in sources}
    validated=[]
    total=0
    for raw in candidates:
        candidate=Candidate.model_validate(raw.model_dump() if isinstance(raw,Candidate) else raw)
        for assertion in candidate.assertions:
            total+=len(assertion.text)
            bases=[]
            for ref in assertion.source_refs:
                source=permitted.get(digest(ref.model_dump()))
                if not source: raise DomainError("invalid_provenance","Candidate cites an unpermitted source",422)
                bases.append(source)
            # A copied source may retain an existing human classification, never infer one.
            if assertion.evidence_stage!="proposed" or assertion.outcome!="unknown":
                if not any(s.evidence_stage==assertion.evidence_stage and s.outcome==assertion.outcome and s.criteria==assertion.evaluation_criteria for s in bases):
                    raise DomainError("unsupported_outcome","Candidate promotes an unsupported outcome",422)
        validated.append(candidate)
    if total>16000: raise DomainError("invalid_model_output","Output character budget exceeded",422)
    return validated

def store_candidate(session,actor_id,event_id,candidate,origin,run=None,previous=None,reason=None,model_profile=None):
    body=candidate.model_dump()
    entry=MemoryEntry(id=uid(),logical_memory_id=previous.logical_memory_id if previous else uid(),revision=previous.revision+1 if previous else 1,event_id=event_id,kind=candidate.kind,title=candidate.title,assertions=body["assertions"],applicability=body["applicability"],origin=origin,schema_version="memory-v1",extractor_version="projection-v1" if origin=="deterministic" else "port-v1",model_profile=model_profile,run_id=run.id if run else None,lifecycle="published" if origin=="deterministic" and not previous else "candidate",supersedes_id=previous.id if previous else None,correction_reason=reason,digest=digest({"body":body,"source_manifest":run.source_manifest_digest if run else None,"supersedes":previous.id if previous else None}),created_by=actor_id)
    session.add(entry);session.flush()
    for assertion in candidate.assertions:
        for ref in assertion.source_refs:
            source=resolve(session,actor_id,event_id,ref)
            session.add(MemorySource(event_id=event_id,memory_entry_id=entry.id,assertion_id=assertion.assertion_id,source_kind=ref.source_kind,source_id=ref.source_id,source_revision=ref.source_revision,source_digest=ref.source_digest,source_state_at_capture=source.evidence_stage,access_class=source.access_class))
    audit(session,actor_id,event_id,"memory.project" if origin=="deterministic" else "memory.candidate",entry.id,digest=entry.digest)
    return entry

def guard(entry, body, if_match):
    if if_match!=str(entry.version) or body.expected_revision!=entry.revision or body.reviewed_digest!=entry.digest:
        raise DomainError("stale_version","Exact memory revision, digest and If-Match version required")

def review(session,actor,event_id,memory_id,body,key,if_match):
    require(session,actor,event_id,"memory:review")
    entry=entry_access(session,actor,event_id,memory_id)
    def apply():
        session.scalar(select(Event).where(Event.id==event_id).with_for_update())
        entry=entry_access(session,actor,event_id,memory_id,True);guard(entry,body,if_match)
        if entry.lifecycle!="candidate": raise DomainError("invalid_state","Only a pending candidate can be reviewed")
        sources=current_sources(session,actor,entry)
        validate_candidates([{"kind":entry.kind,"title":entry.title,"assertions":entry.assertions,"applicability":entry.applicability}],sources)
        decision=ReviewDecision(id=uid(),event_id=event_id,actor_id=actor,subject_kind="memory",subject_id=entry.id,subject_digest=entry.digest,decision=body.decision,note=body.note)
        session.add(decision);session.flush()
        entry.lifecycle="published" if body.decision=="publish" else "retracted";entry.version+=1;entry.review_decision_id=decision.id
        audit(session,actor,event_id,"memory.review",entry.id,decision_id=decision.id)
        return {"memory_id":entry.id,"lifecycle":entry.lifecycle,"version":entry.version,"decision_id":decision.id}
    return execute_once(session,actor,event_id,f"memory.review:{memory_id}",key,{**body.model_dump(),"if_match":if_match},apply)

def correct(session,actor,event_id,memory_id,body,key,if_match):
    require(session,actor,event_id,"memory:review");entry_access(session,actor,event_id,memory_id)
    # Recheck correcting source permission even on an idempotency replay.
    resolved_inputs(session,actor,event_id,body.correcting_source_refs)
    def apply():
        session.scalar(select(Event).where(Event.id==event_id).with_for_update())
        entry=entry_access(session,actor,event_id,memory_id,True);guard(entry,body,if_match)
        if entry.lifecycle not in ("published","candidate"): raise DomainError("invalid_state","Memory already retired")
        sources=resolved_inputs(session,actor,event_id,body.correcting_source_refs)
        if len(sources)!=1: raise DomainError("invalid_correction","Foundation corrections require one exact source",422)
        candidate=validate_candidates(project(sources),sources)[0]
        replacement=store_candidate(session,actor,event_id,candidate,"deterministic",previous=entry,reason=body.reason)
        entry.lifecycle="superseded";entry.version+=1
        audit(session,actor,event_id,"memory.supersede",entry.id,replacement_id=replacement.id)
        return {"replacement_candidate_id":replacement.id,"supersedes_id":entry.id,"old_eligibility":False,"version":replacement.version}
    return execute_once(session,actor,event_id,f"memory.correct:{memory_id}",key,{**body.model_dump(),"if_match":if_match},apply)

def retract(session,actor,event_id,memory_id,body,key,if_match):
    require(session,actor,event_id,"memory:review");entry_access(session,actor,event_id,memory_id)
    def apply():
        session.scalar(select(Event).where(Event.id==event_id).with_for_update())
        entry=entry_access(session,actor,event_id,memory_id,True);guard(entry,body,if_match)
        if entry.lifecycle not in ("published","candidate"): raise DomainError("invalid_state","Memory already retired")
        decision=ReviewDecision(id=uid(),event_id=event_id,actor_id=actor,subject_kind="memory",subject_id=entry.id,subject_digest=entry.digest,decision="retract",note=body.reason)
        session.add(decision);session.flush();entry.lifecycle="retracted";entry.version+=1;entry.review_decision_id=decision.id
        audit(session,actor,event_id,"memory.retract",entry.id,decision_id=decision.id)
        return {"memory_id":entry.id,"lifecycle":entry.lifecycle,"version":entry.version,"decision_id":decision.id}
    return execute_once(session,actor,event_id,f"memory.retract:{memory_id}",key,{**body.model_dump(),"if_match":if_match},apply)
