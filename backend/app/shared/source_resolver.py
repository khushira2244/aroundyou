from dataclasses import dataclass
from sqlalchemy import select
from app.access.authorization import require, allowed
from app.events.models import ContextRevision
from app.planning.models import PlanVersion
from app.shared.models import ReviewDecision
from app.shared.types import digest
from app.api.errors import DomainError, missing
from app.memory.schemas import SourceRef, Applicability

@dataclass(frozen=True)
class ResolvedSource:
    ref: SourceRef
    text: str
    access_class: str
    evidence_stage: str
    outcome: str
    criteria: str | None
    applicability: dict

def decision_digest(row):
    return digest({k:getattr(row,k) for k in ["event_id","actor_id","supersedes_id","subject_kind","subject_id","subject_digest","decision","evidence_stage","outcome","criteria","note"]})

def resolve(session, actor_id, event_id, ref):
    event=require(session,actor_id,event_id,"memory:read")
    stage,outcome,criteria="proposed","unknown",None
    if ref.source_kind=="context":
        row=session.get(ContextRevision,ref.source_id)
        if not row or row.event_id!=event_id: missing()
        current=event.active_context_revision_id==row.id
        revision,hashed,text,access,app=row.sequence,row.content_hash,row.original_text,row.access_class,row.applicability
        if row.snapshot:
            text=__import__('json').dumps({'original_excerpt':row.original_text[:3000],'organizer_reported_snapshot_excerpt':__import__('json').dumps(row.snapshot,sort_keys=True)[:5000],'notice':'Bounded excerpts; organizer-confirmed meaning is not independently verified; full immutable source retained.'},sort_keys=True)
    elif ref.source_kind=='operational':
        from app.participation.models import OperationalSource
        row=session.get(OperationalSource,ref.source_id)
        if not row or row.event_id!=event_id:missing()
        # Demographic originals are never reusable AI/memory input.
        if row.kind.startswith('insight.'):missing()
        latest=session.scalar(select(OperationalSource.id).where(OperationalSource.event_id==event_id,OperationalSource.aggregate_id==row.aggregate_id).order_by(OperationalSource.sequence.desc()).limit(1))
        current=latest==row.id
        revision,hashed,text,access,app=row.sequence,row.digest,__import__('json').dumps({'recorded_operation':row.kind,'recorded_facts':row.content,'notice':'Historical operation record only; recompute current status. No work success, attendance or external approval inferred.'},ensure_ascii=False),"private",{'category':event.category}
        if row.kind in ('resource.consume','resource.checkout','resource.return'):
            from app.execution.models import ResourceOperation
            operation=session.get(ResourceOperation,row.content.get('operation_id'))
            if not operation or operation.event_id!=event_id or operation.created_by!=row.created_by or not allowed(session,row.created_by,event_id,'plan:write'):raise DomainError('invalid_provenance','Resource verification authority/source invalid')
            stage,outcome,criteria='verified','inconclusive','Human reconciled exact operational quantity; not an event success claim'
    elif ref.source_kind=='execution':
        from app.execution.models import ExecutionRevision
        row=session.get(ExecutionRevision,ref.source_id)
        if not row or row.event_id!=event_id:missing()
        latest=session.scalar(select(ExecutionRevision.id).where(ExecutionRevision.aggregate_id==row.aggregate_id,ExecutionRevision.event_id==event_id).order_by(ExecutionRevision.sequence.desc()).limit(1))
        current=latest==row.id
        if row.kind.startswith('report.') and row.content['record'].get('review_status')=='draft':missing()
        if row.kind.startswith('evidence.'):
            from app.execution.models import WorkReport
            report=session.get(WorkReport,row.content['record'].get('report_id'))
            if report and report.content['review_status']=='draft':missing()
        stage,outcome,criteria=row.content['evidence_stage'],row.content['outcome'],row.content.get('criteria')
        if row.kind=='stage.complete':
            from app.execution.models import WorkExecution
            for wid,version in row.content['record']['work_versions'].items():
                execution=session.scalar(select(WorkExecution).where(WorkExecution.event_id==event_id,WorkExecution.plan_id==row.content['record']['plan_id'],WorkExecution.work_id==wid))
                if not execution or execution.version!=version or execution.content['status']!='completed':current=False
        if row.kind=='measurement.verify':
            from app.execution.models import WorkReport
            report=session.get(WorkReport,row.content['record']['report_id'])
            if not report or report.version!=row.content['record']['report_revision'] or report.content['review_status']!='accepted':current=False
        # Records distinguish exact observed/reviewed operations from reusable success lessons.
        revision,hashed,text,access,app=row.sequence,row.digest,__import__('json').dumps({'kind':row.kind,'source_record':row.content,'notice':'Exact historical execution record; not a general success claim'},ensure_ascii=False),"private",{'category':event.category}
        if stage=='verified' and not allowed(session,row.actor_id,event_id,'plan:write'):
            from app.execution.service import reviewer,work
            wid=row.content['record'].get('work_id')
            if not wid or not reviewer(session,row.actor_id,event,work(session,event,row.actor_id,wid)):raise DomainError('invalid_provenance','Reviewer scope no longer permits this source')
    elif ref.source_kind=="plan":
        row=session.get(PlanVersion,ref.source_id)
        if not row or row.event_id!=event_id: missing()
        current=event.active_plan_id==row.id and event.active_context_revision_id==row.context_revision_id
        content=row.content
        summary={"plan_id":row.id,"source_digest":row.digest,"projection":"bounded factual excerpt; full original retained","stage_count":len(content.get('stages',[])),"work_count":len(content.get('work',[])),"stages_excerpt":[{"id":x['id'],"title_excerpt":x['title'][:80]} for x in content.get('stages',[])[:5]],"work_excerpt":[{"id":x['id'],"stage_id":x['stage_id'],"title_excerpt":x['title'][:80]} for x in content.get('work',[])[:10]]}
        revision,hashed,text,access,app=row.sequence,row.digest,__import__('json').dumps(summary,sort_keys=True),row.access_class,{"category":event.category}
    else:
        row=session.get(ReviewDecision,ref.source_id)
        if not row or row.event_id!=event_id or row.subject_kind not in ("context","plan"): missing()
        target=ContextRevision if row.subject_kind=="context" else PlanVersion
        original=session.get(target,row.subject_id)
        if not original: missing()
        child_ref=SourceRef(source_kind=row.subject_kind,source_id=original.id,source_revision=original.sequence,source_digest=row.subject_digest)
        source=resolve(session,actor_id,event_id,child_ref)
        current=session.scalar(select(ReviewDecision.id).where(ReviewDecision.supersedes_id==row.id)) is None
        revision,hashed,text,access,app=1,decision_digest(row),row.note or row.decision,source.access_class,source.applicability
        stage,outcome,criteria=row.evidence_stage,row.outcome,row.criteria or None
        if stage!="proposed" and (row.subject_kind!="context" or original.source_kind!="observation"):
            raise DomainError("unsupported_outcome","No observed execution source supports decision",422)
        if not allowed(session,row.actor_id,event_id,"source:verify"):
            raise DomainError("invalid_provenance","Decision authority was revoked",409)
    if access=="private" and not allowed(session,actor_id,event_id,"source:private"): missing()
    if not current or revision!=ref.source_revision or hashed!=ref.source_digest:
        raise DomainError("stale_source","Source is superseded or its revision/digest does not match")
    if len(text)>12000: raise DomainError("source_too_large","Source exceeds extraction budget",422)
    return ResolvedSource(ref,text,access,stage,outcome,criteria,Applicability.model_validate(app).model_dump())
