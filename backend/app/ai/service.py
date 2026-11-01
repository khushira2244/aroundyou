from datetime import timedelta
from typing import Literal
from app.planning.draft_models import PlanningDraft
from sqlalchemy import select,and_,or_
from pydantic import ValidationError
from app.ai.models import AIRun,AIProposal
from app.ai.planning_port import MuseSparkRequest,WORKFLOW_INSTRUCTIONS
from app.ai.context_builder import MuseSparkContextBuilder
from app.planning.schemas import PlanContent
from app.events.creation_schemas import Interpretation
from app.planning.service import draft_for,versions
from app.events.models import Event,ContextRevision
from app.events.creation_service import manual_interpretation
from app.shared.models import JobTask,ReviewDecision
from app.shared.jobs import owned,Lease
from app.shared.unit_of_work import unit_of_work
from app.shared.types import uid,digest,now
from app.shared.audit import audit
from app.access.authorization import require
from app.api.errors import DomainError,missing
from app.memory.schemas import StrictModel
from pydantic import Field,model_validator

class GovernanceItem(StrictModel):
    id: str=Field(min_length=1,max_length=60)
    title: str=Field(min_length=1,max_length=200)
    status: Literal['advisory_only','needs_input','potentially_relevant','recommended','optional']='advisory_only'
    detail: str=Field(min_length=1,max_length=2000)
    classification: Literal['verified_requirement','conditional_recommendation','ai_advisory_suggestion','unknown_needs_clarification','not_applicable']='ai_advisory_suggestion'
    rationale: str=Field(default='',max_length=2000)
    supporting_event_facts: list[str]=Field(default_factory=list,max_length=20)
    rule_sources: list[str]=Field(default_factory=list,max_length=10)
    uncertainty: list[str]=Field(default_factory=list,max_length=20)
    next_action: str=Field(default='',max_length=2000)
    suggest_ticket: bool=False
    @model_validator(mode='after')
    def no_unverified_legal_claims(self):
        # No verified external legal evidence registry exists in this group.
        if self.classification=='verified_requirement' or self.rule_sources:raise ValueError('Verified external rules require an implemented evidence verifier; unsupported in Group 2')
        return self
class GovernanceAdvice(StrictModel):
    items: list[GovernanceItem]=Field(max_length=30)

def output_schema(kind):
    if kind=='recovery':
        from app.recovery.advisory import RecoveryAdvice
        return RecoveryAdvice.model_json_schema()
    if kind=='execution':
        from app.execution.advisory import EvidenceAdvice
        return EvidenceAdvice.model_json_schema()
    if kind in ('participation','resources','execution','recovery'):
        from app.participation.advisory import ParticipationAdvice
        return ParticipationAdvice.model_json_schema()
    return Interpretation.model_json_schema() if kind=='understanding' else GovernanceAdvice.model_json_schema() if kind=='governance' else PlanContent.model_json_schema()

def request_run(session,actor,event,kind,message,adapter,application_id=None):
    if adapter is None:raise DomainError('provider_unavailable','Muse Spark planning provider is not configured; manual authoring remains available',503)
    if kind not in ('understanding','stages','work','governance','participation','resources','execution','recovery'):raise DomainError('invalid_kind','Unsupported AI workflow',422)
    if not event.active_context_revision_id:raise DomainError('missing_context','Save original context first',422)
    draft=draft_for(session,event) if kind in ('stages','work') else None
    if kind=='work' and not draft.stage_confirmed:raise DomainError('invalid_state','Confirm stages first')
    builder=MuseSparkContextBuilder()
    built=builder.build(session,actor,event.id,purpose='planning',draft=draft,allow_stale_plan=kind in ('understanding','governance','participation','resources','execution','recovery'))
    if kind in ('participation','resources','execution','recovery'):
        if kind=='recovery':
            from app.recovery.advisory import context
            built['authoritative_current']['participation_and_resources']=context(session,actor,event,application_id)
        elif kind=='execution':
            from app.execution.advisory import context
            built['authoritative_current']['execution_evidence']=context(session,actor,event,application_id)
        else:
            from app.participation.advisory import context
            built['authoritative_current']['participation_and_resources']=context(session,actor,event,application_id)
    if len(__import__('json').dumps(built,allow_nan=False))>64000:raise DomainError('context_budget_exceeded','Use a smaller planning scope or manual editing; AI input budget exceeded',422)
    source=versions(event,draft)
    run=AIRun(id=uid(),event_id=event.id,requester_id=actor,kind=kind,source_versions=source,context_manifest=built,request_message=message)
    session.add(run);session.flush();session.add(JobTask(ai_run_id=run.id));audit(session,actor,event.id,'ai.request.'+kind,run.id)
    return {'run_id':run.id,'status':'queued','source_versions':source,'status_url':f'/v1/ai-runs/{run.id}'}

def validate_output(kind,result,base):
    if len(__import__('json').dumps(result,allow_nan=False))>24000:raise DomainError('invalid_model_output','Model output budget exceeded',422)
    if kind in ('participation','resources','execution','recovery'):
        if kind=='recovery':
            from app.recovery.advisory import RecoveryAdvice
            return RecoveryAdvice.model_validate(result).model_dump()
        if kind=='execution':
            from app.execution.advisory import EvidenceAdvice
            return EvidenceAdvice.model_validate(result).model_dump()
        from app.participation.advisory import ParticipationAdvice
        return ParticipationAdvice.model_validate(result).model_dump()
    if kind=='understanding':return Interpretation.model_validate(result).model_dump()
    if kind=='governance':return GovernanceAdvice.model_validate(result).model_dump()
    proposed=PlanContent.model_validate(result).model_dump()
    if kind=='stages' and base and any(proposed[k]!=base[k] for k in ('work','resources','groups','roles','zones','dependencies')):raise DomainError('scope_violation','Stage proposal cannot redesign work/resources',422)
    if kind=='work' and base and proposed['stages']!=base['stages']:raise DomainError('scope_violation','Work proposal cannot change confirmed stages',422)
    return {'plan':proposed,'message':'Structured model proposal requiring human review'}

def call_provider(adapter,request,timeout_seconds):
    # A daemon holds no session or mutation tools. A late result is discarded.
    from queue import Queue,Empty
    from threading import Thread
    result=Queue(maxsize=1)
    def invoke():
        try:result.put((True,adapter.propose(request)))
        except Exception as exc:result.put((False,exc))
    Thread(target=invoke,daemon=True,name='aroundyou-provider-call').start()
    try:success,value=result.get(timeout=timeout_seconds)
    except Empty:raise DomainError('provider_timeout','Provider exceeded the bounded deadline',503) from None
    if not success:
        if isinstance(value,TimeoutError):raise DomainError('provider_timeout','Provider timed out',503) from None
        raise value
    return value

def work_ai_once(factory,adapter,owner='planning-worker',timeout_seconds=30):
    with unit_of_work(factory) as session:
        expired=list(session.scalars(select(JobTask).where(JobTask.ai_run_id.is_not(None),JobTask.status=='running',JobTask.lease_until<=now(),JobTask.attempt_count>=JobTask.max_attempts).with_for_update(skip_locked=True)))
        for task in expired:
            task.status='failed';session.get(AIRun,task.ai_run_id).status='failed';session.get(AIRun,task.ai_run_id).failure_code='lease_exhausted'
        task=session.scalar(select(JobTask).where(JobTask.ai_run_id.is_not(None),JobTask.attempt_count<JobTask.max_attempts,or_(and_(JobTask.status.in_(['queued','retry']),JobTask.available_at<=now()),and_(JobTask.status=='running',JobTask.lease_until<=now()))).order_by(JobTask.id).with_for_update(skip_locked=True).limit(1))
        if not task:return None
        task.status='running';task.attempt_count+=1;task.fencing_token+=1;task.lease_owner=owner;task.lease_until=now()+timedelta(seconds=60)
        lease=Lease(task.id,task.ai_run_id,task.fencing_token,owner);run=session.get(AIRun,task.ai_run_id);run.status='running';event_id=run.event_id
    try:
        with factory() as session:
            run=session.get(AIRun,lease.run_id);event=require(session,run.requester_id,event_id,'plan:write');draft=session.scalar(select(PlanningDraft).where(PlanningDraft.event_id==event_id)) if run.kind in ('stages','work') else None
            if run.source_versions!=versions(event,draft):raise DomainError('stale_proposal','Input changed before inference')
            MuseSparkContextBuilder().validate(session,run.requester_id,event_id,run.context_manifest,draft=draft)
            if run.kind in ('participation','resources','execution','recovery'):
                if run.kind=='recovery':
                    from app.recovery.advisory import validate_context
                elif run.kind=='execution':
                    from app.execution.advisory import validate_context
                else:
                    from app.participation.advisory import validate_context
                validate_context(session,run.requester_id,event,run.context_manifest['authoritative_current']['execution_evidence' if run.kind=='execution' else 'participation_and_resources'])
            base=draft.content if draft else None;kind=run.kind;actor=run.requester_id
            request=MuseSparkRequest(kind,run.context_manifest['authoritative_current'],run.context_manifest['derived_historical'],run.source_versions,WORKFLOW_INSTRUCTIONS[kind]+"\nOrganizer request: "+run.request_message,output_schema(kind))
        if adapter is None:raise DomainError('provider_unavailable','No configured model adapter',503)
        result=call_provider(adapter,request,min(30,max(.001,timeout_seconds)));validated=validate_output(kind,result,base)
        if kind in ('participation','resources','execution','recovery'):
            if kind=='recovery':
                from app.recovery.advisory import validate_output as validate_participation
            elif kind=='execution':
                from app.execution.advisory import validate_output as validate_participation
            else:
                from app.participation.advisory import validate_output as validate_participation
            validated=validate_participation(result,request.authoritative_current)
        if kind=='governance':
            fact_text=__import__('json').dumps(request.authoritative_current,ensure_ascii=False)
            if any(fact not in fact_text for item in validated['items'] for fact in item['supporting_event_facts']):raise DomainError('invalid_model_output','Supporting facts must cite supplied event information',422)
        with unit_of_work(factory) as session:
            event=session.scalar(select(Event).where(Event.id==event_id).with_for_update());task=session.scalar(select(JobTask).where(JobTask.id==lease.job_id).with_for_update())
            if not owned(task,lease):return False
            run=session.get(AIRun,lease.run_id);require(session,actor,event_id,'plan:write');draft=draft_for(session,event) if kind in ('stages','work') else None
            if run.source_versions!=versions(event,draft):raise DomainError('stale_proposal','Input changed during inference')
            MuseSparkContextBuilder().validate(session,actor,event_id,run.context_manifest,draft=draft)
            if kind in ('participation','resources','execution','recovery'):
                if kind=='recovery':
                    from app.recovery.advisory import validate_context
                elif kind=='execution':
                    from app.execution.advisory import validate_context
                else:
                    from app.participation.advisory import validate_context
                validate_context(session,actor,event,run.context_manifest['authoritative_current']['execution_evidence' if kind=='execution' else 'participation_and_resources'])
            profile=adapter.model_profile
            if not isinstance(profile,str) or not 1<=len(profile)<=120:raise DomainError('invalid_model_output','Model profile required',422)
            proposal=AIProposal(id=uid(),event_id=event_id,run_id=run.id,kind=kind,source_versions=run.source_versions,payload=validated,digest=digest(validated),provenance={'source':profile,'model_execution':bool(getattr(adapter,'live_provider',False)),'requires_human_confirmation':True})
            session.add(proposal);session.flush();run.proposal_id=proposal.id;run.status='succeeded';run.model_profile=profile;run.failure_code=None;task.status='succeeded';task.lease_until=None
            audit(session,actor,event_id,'ai.proposal.pending',proposal.id)
        return True
    except Exception as exc:
        code=exc.code if isinstance(exc,DomainError) else 'invalid_model_output' if isinstance(exc,(ValueError,ValidationError,TypeError)) else 'provider_failed'
        retry=code in ('provider_failed','provider_unavailable','provider_timeout')
        with unit_of_work(factory) as session:
            task=session.scalar(select(JobTask).where(JobTask.id==lease.job_id).with_for_update())
            if not owned(task,lease):return False
            terminal=not retry or task.attempt_count>=task.max_attempts;task.status='failed' if terminal else 'retry';task.last_error=code;task.available_at=now()+timedelta(seconds=2**task.attempt_count);task.lease_until=None
            run=session.get(AIRun,lease.run_id);run.status='stale' if code in ('stale_proposal','stale_memory','stale_context') else 'failed' if terminal else 'queued';run.failure_code=code
        return False

def review_advice(session,actor,event,proposal_id,decision,reviewed_digest,corrected=None):
    p=session.get(AIProposal,proposal_id)
    if not p or p.event_id!=event.id or p.kind not in ('understanding','governance','participation','resources','execution','recovery'):missing()
    if p.status!='pending' or p.digest!=reviewed_digest or p.source_versions!=versions(event):raise DomainError('stale_proposal','Review exact current pending proposal')
    if decision=='accept' and p.run_id:
        run=session.get(AIRun,p.run_id);MuseSparkContextBuilder().validate(session,actor,event.id,run.context_manifest)
    if decision=='accept' and p.kind in ('participation','resources','execution','recovery'):
        if p.kind=='recovery':
            from app.recovery.advisory import validate_context
        elif p.kind=='execution':
            from app.execution.advisory import validate_context
        else:
            from app.participation.advisory import validate_context
        validate_context(session,actor,event,session.get(AIRun,p.run_id).context_manifest['authoritative_current']['execution_evidence' if p.kind=='execution' else 'participation_and_resources'])
    if decision=='accept' and p.kind=='understanding':
        source=session.get(ContextRevision,event.active_context_revision_id);manual_interpretation(session,actor,event,corrected or p.payload,source.sequence)
    if decision=='accept' and p.kind=='governance':event.version+=1
    review=ReviewDecision(id=uid(),event_id=event.id,actor_id=actor,subject_kind='proposal',subject_id=p.id,subject_digest=p.digest,decision=decision)
    session.add(review);session.flush();p.status='approved' if decision=='accept' else 'rejected';p.review_decision_id=review.id
    audit(session,actor,event.id,'ai.advice.review',p.id)
    return {'status':p.status}
