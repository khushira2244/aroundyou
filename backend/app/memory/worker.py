from sqlalchemy import select
from pydantic import ValidationError
from app.shared.unit_of_work import unit_of_work
from app.shared.jobs import claim, owned, fail
from app.shared.models import JobTask
from app.memory.models import MemoryRun
from app.events.models import Event
from app.memory.schemas import SourceRef
from app.memory.service import resolved_inputs, validate_candidates, store_candidate
from app.memory.projections import project
from app.memory.ports import ExtractionInput
from app.access.authorization import require
from app.api.errors import DomainError

def process_lease(factory, lease, extractor=None):
    try:
        # Only immutable minimized input crosses the provider boundary. No open transaction.
        with factory() as session:
            if not owned(session.get(JobTask,lease.job_id),lease): return False
            run=session.get(MemoryRun,lease.run_id)
            require(session,run.requester_id,run.event_id,"memory:extract")
            sources=resolved_inputs(session,run.requester_id,run.event_id,[SourceRef.model_validate(r) for r in run.source_manifest])
            event_id,actor,mode=run.event_id,run.requester_id,run.extractor
            source_request=ExtractionInput(event_id,tuple(sources))
        if mode=="open_weight":
            if extractor is None: raise DomainError("extractor_unavailable","Open-weight provider not enabled",503)
            candidates=extractor.extract(source_request)
            model_profile=extractor.model_profile
            if not isinstance(model_profile,str) or not 1<=len(model_profile)<=120: raise ValueError("Invalid model profile")
        else:
            candidates=project(sources);model_profile=None
        candidates=validate_candidates(candidates,sources)
        with unit_of_work(factory) as session:
            # Serialize with source corrections before checking and persisting the result.
            session.scalar(select(Event).where(Event.id==event_id).with_for_update())
            task=session.scalar(select(JobTask).where(JobTask.id==lease.job_id).with_for_update())
            if not owned(task,lease): return False
            run=session.get(MemoryRun,lease.run_id)
            require(session,actor,event_id,"memory:extract")
            fresh=resolved_inputs(session,actor,event_id,[SourceRef.model_validate(r) for r in run.source_manifest])
            validate_candidates(candidates,fresh)
            entries=[store_candidate(session,actor,event_id,c,"model" if mode=="open_weight" else "deterministic",run=run,model_profile=model_profile) for c in candidates]
            run.output_entry_ids=[e.id for e in entries];run.status="succeeded";run.failure_code=None
            task.status="succeeded";task.lease_until=None;task.last_error=None
        return True
    except DomainError as exc:
        fail(factory,lease,exc.code,terminal=exc.status!=503)
    except (ValidationError,ValueError,TypeError):
        fail(factory,lease,"invalid_model_output",terminal=True)
    except Exception:
        # No raw provider/DB exceptions or secrets in durable/user-facing failure fields.
        fail(factory,lease,"extractor_failed")
    return False

def work_once(factory, extractor=None, owner="memory-worker"):
    lease=claim(factory,owner)
    return process_lease(factory,lease,extractor) if lease else None
