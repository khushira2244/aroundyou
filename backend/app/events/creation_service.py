from sqlalchemy import select
from app.events.models import Event,ContextRevision
from app.events.creation_schemas import CreationForm,Interpretation
from app.events.dto import creation_dto
from app.events.source_revisions import append_context
from app.access.models import EventGrant
from app.access.authorization import require
from app.access.permissions import PERMISSIONS
from app.shared.types import uid,digest
from app.shared.models import ReviewDecision
from app.shared.idempotency import execute_once
from app.shared.audit import audit
from app.planning.draft_models import PlanningDraft
from app.api.errors import DomainError

def new_draft(session,actor,format,key):
    def apply():
        form=CreationForm(format=format).model_dump()
        event=Event(id=uid(),creator_id=actor,title='',category='',lifecycle='draft',draft_form=form)
        session.add(event);session.flush()
        for permission in PERMISSIONS:session.add(EventGrant(event_id=event.id,user_id=actor,permission=permission,scope={}))
        session.flush();audit(session,actor,event.id,'event.draft.create',event.id)
        return creation_dto(session,event)
    return execute_once(session,actor,'event-drafts','event.draft.create',key,{'format':format},apply)

def invalidate(session,event):
    event.interpretation=None;event.current_finalization_id=None
    draft=session.scalar(select(PlanningDraft).where(PlanningDraft.event_id==event.id))
    if draft:
        draft.stage_confirmed=False;draft.work_confirmed=False;draft.actors_confirmed=False;draft.derived_from=None;draft.version+=1
    if event.lifecycle!='draft':event.lifecycle='created_unpublished'

def save_intent(session,actor,event,text,source='written',form=None):
    if source=='reviewed_demo_transcript':raise DomainError('invalid_source','Demo transcript provenance cannot be sent to the backend',422)
    if source not in ('written','reviewed_transcript'):raise DomainError('invalid_source','Unsupported source',422)
    if not text.strip():raise DomainError('invalid_context','Original context is required',422)
    current=session.get(ContextRevision,event.active_context_revision_id) if event.active_context_revision_id else None
    details={**(form or event.draft_form),'executionIntent':text,'intentSource':source}
    details={k:v for k,v in details.items() if k not in ('confirmAccuracy','confirmPlanning','confirmContinue')}
    snapshot={'creation_form':details,'clarification_rounds':current.snapshot.get('clarification_rounds',[]) if current else []}
    if current and current.original_text==text and current.source_kind==source and current.snapshot.get('creation_form')==snapshot['creation_form']:return
    # Group 1 supports human written/observation; reviewed transcript is stored as original written context plus provenance.
    row=append_context(session,actor,event.id,text,event.version,source_kind=source,snapshot=snapshot)
    invalidate(session,event)
    event.draft_form={**event.draft_form,"executionIntent":text,"intentSource":source}
    return row

def save_draft(session,actor,event,step,raw):
    if event.lifecycle!='draft':raise DomainError('invalid_state','Creation draft is already confirmed')
    form=CreationForm.model_validate(raw)
    event.title=form.title;event.category=form.category
    if form.executionIntent:save_intent(session,actor,event,form.executionIntent,form.intentSource,form.model_dump())
    event.title=form.title;event.category=form.category;event.draft_form=form.model_dump();event.draft_step=max(event.draft_step,step);event.version+=1
    audit(session,actor,event.id,'event.draft.save',event.id,step=step)
    return creation_dto(session,event)

def confirm_creation(session,actor,event):
    if event.lifecycle!='draft':raise DomainError('invalid_state','Only drafts can be created')
    form=CreationForm.model_validate(event.draft_form)
    try:form.complete()
    except ValueError as exc:raise DomainError('incomplete_brief',str(exc),422) from None
    if not event.active_context_revision_id:raise DomainError('missing_context','Save the original context before creating',422)
    event.lifecycle='created_unpublished';event.draft_step=4;event.version+=1
    audit(session,actor,event.id,'event.confirm_creation',event.id)
    return creation_dto(session,event)

def manual_interpretation(session,actor,event,interpretation,context_version):
    source=session.get(ContextRevision,event.active_context_revision_id)
    if not source or source.sequence!=context_version:raise DomainError('stale_context','Exact source context required')
    value=Interpretation.model_validate(interpretation).model_dump()
    snapshot={**source.snapshot,'confirmed_interpretation':value}
    source=append_context(session,actor,event.id,source.original_text,event.version,source_kind=source.source_kind,snapshot=snapshot)
    context_version=source.sequence
    invalidate(session,event)
    event.interpretation={**value,'context_version':context_version,'source':'human_reviewed','independently_verified':False}
    session.add(ReviewDecision(event_id=event.id,actor_id=actor,subject_kind='context',subject_id=source.id,subject_digest=source.content_hash,decision='interpretation_review',note='Human reviewed interpretation; original retained'))
    event.version+=1;audit(session,actor,event.id,'context.interpretation.review',source.id)
    return creation_dto(session,event)


def clarify(session,actor,event,context_version,answers,proposal_id=None):
    source=session.get(ContextRevision,event.active_context_revision_id)
    if not source or source.sequence!=context_version:raise DomainError('stale_context','Answer the current context revision')
    questions=[]
    if proposal_id:
        from app.ai.models import AIProposal
        from app.planning.service import versions
        p=session.get(AIProposal,proposal_id)
        if not p or p.event_id!=event.id or p.kind!='understanding':raise DomainError('not_found','Proposal not found',404)
        if p.status!='pending' or p.source_versions!=versions(event):raise DomainError('stale_proposal','Clarify the current pending interpretation')
        questions=p.payload.get('clarifications',[])
        if any(x['question'] not in questions for x in answers):raise DomainError('invalid_question','Answer a question from the reviewed proposal',422)
    rounds=source.snapshot.get('clarification_rounds',[])
    if len(rounds)>=20:raise DomainError('limit_exceeded','Clarification round limit reached',422)
    snapshot={**source.snapshot,'clarification_rounds':[*rounds,{'round':len(rounds)+1,'source_context_id':source.id,'proposal_id':proposal_id,'answers':answers}]}
    snapshot.pop('confirmed_interpretation',None)
    append_context(session,actor,event.id,source.original_text,event.version,source_kind=source.source_kind,snapshot=snapshot)
    invalidate(session,event);audit(session,actor,event.id,'context.clarify',source.id)
    return creation_dto(session,event)


def revise_details(session,actor,event,raw):
    if event.lifecycle=='draft':return save_draft(session,actor,event,event.draft_step,raw)
    form=CreationForm.model_validate(raw)
    try:form.complete()
    except ValueError as exc:raise DomainError('incomplete_brief',str(exc),422) from None
    if form.model_dump()==event.draft_form:return creation_dto(session,event)
    event.title=form.title;event.category=form.category
    save_intent(session,actor,event,form.executionIntent,form.intentSource,form.model_dump())
    event.draft_form=form.model_dump();event.version+=1
    audit(session,actor,event.id,'context.details.revise',event.id)
    return creation_dto(session,event)
