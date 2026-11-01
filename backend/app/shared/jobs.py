from dataclasses import dataclass
from datetime import timedelta
from sqlalchemy import select, or_, and_
from app.shared.models import JobTask
from app.memory.models import MemoryRun
from app.shared.types import now
from app.shared.unit_of_work import unit_of_work
from app.shared.audit import audit

@dataclass(frozen=True)
class Lease:
    job_id: str
    run_id: str
    token: int
    owner: str

def claim(factory, owner, seconds=60):
    if not 1<=seconds<=300 or not owner or len(owner)>80: raise ValueError("Invalid lease")
    with unit_of_work(factory) as session:
        current=now()
        # Expired final attempts are terminal; they cannot remain stuck running.
        exhausted=session.scalars(select(JobTask).where(JobTask.run_id.is_not(None),JobTask.status=="running",JobTask.lease_until<=current,JobTask.attempt_count>=JobTask.max_attempts).with_for_update(skip_locked=True))
        for task in exhausted:
            task.status="failed";task.last_error="lease_exhausted"
            run=session.get(MemoryRun,task.run_id);run.status="failed";run.failure_code="lease_exhausted"
        task=session.scalar(select(JobTask).where(JobTask.run_id.is_not(None),JobTask.attempt_count<JobTask.max_attempts,or_(and_(JobTask.status.in_(["queued","retry"]),JobTask.available_at<=current),and_(JobTask.run_id.is_not(None),JobTask.status=="running",JobTask.lease_until<=current))).order_by(JobTask.available_at,JobTask.id).with_for_update(skip_locked=True).limit(1))
        if not task: return None
        task.status="running";task.attempt_count+=1;task.fencing_token+=1;task.lease_owner=owner;task.lease_until=current+timedelta(seconds=seconds)
        run=session.get(MemoryRun,task.run_id);run.status="running"
        audit(session,run.requester_id,run.event_id,"memory.job.claim",task.id,attempt=task.attempt_count,fence=task.fencing_token)
        return Lease(task.id,task.run_id,task.fencing_token,owner)

def owned(task, lease):
    return task and task.status=="running" and task.fencing_token==lease.token and task.lease_owner==lease.owner and task.lease_until>now()

def fail(factory, lease, code="extractor_failed", terminal=False):
    with unit_of_work(factory) as session:
        task=session.scalar(select(JobTask).where(JobTask.id==lease.job_id).with_for_update())
        if not owned(task,lease): return False
        task.last_error=code
        task.status="failed" if terminal or task.attempt_count>=task.max_attempts else "retry"
        task.available_at=now()+timedelta(seconds=min(60,2**task.attempt_count))
        task.lease_until=None
        run=session.get(MemoryRun,task.run_id);run.status="stale" if code=="stale_source" else ("failed" if task.status=="failed" else "queued");run.failure_code=code
        audit(session,run.requester_id,run.event_id,"memory.job.failure",task.id,attempt=task.attempt_count,code=code,terminal=task.status=="failed")
        return True
