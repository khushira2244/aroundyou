from typing import Protocol
from app.access.authorization import require
from app.events.models import ContextRevision
from app.planning.models import PlanVersion
from app.memory.retrieval import retrieve
from app.shared.types import digest
from app.api.errors import DomainError

def reported_operating_context(session,event):
    from app.planning.draft_models import PlanningDraft
    from app.publication.models import SetupRevision
    from sqlalchemy import select
    draft=session.scalar(select(PlanningDraft).where(PlanningDraft.event_id==event.id))
    setup=session.get(SetupRevision,event.current_setup_id) if event.current_setup_id else None
    configuration=setup.configuration if setup and setup.source_plan_id==event.active_plan_id else {}
    location=configuration.get('location',{})
    return {'unconfirmed_planning_draft':draft.content if draft and draft.context_revision_id==event.active_context_revision_id else None,'organizer_reported_setup':{'location':{k:v for k,v in location.items() if k!='emergency_contact'},'availability_claims_unverified':configuration.get('availability_claims',{}),'participation':configuration.get('participation',{})}}

def assessment_fingerprint(session,event):
    from app.planning.draft_models import PlanningDraft
    from sqlalchemy import select
    draft=session.scalar(select(PlanningDraft).where(PlanningDraft.event_id==event.id))
    return digest({'context':event.active_context_revision_id,'interpretation':event.interpretation,'form':event.draft_form,'category':event.category,'plan_id':event.active_plan_id,'draft':draft.content if draft else None,'operating_context':reported_operating_context(session,event)})

class PlanningContextPort(Protocol):
    def build(self, session, actor_id: str, event_id: str, purpose: str, **filters) -> dict: ...

class MuseSparkContextBuilder:
    """Model-neutral structured input for the future Muse Spark adapter; no model call."""
    def build(self,session,actor_id,event_id,purpose="planning",draft=None,allow_stale_plan=False,**filters):
        event=require(session,actor_id,event_id,"source:private")
        if purpose not in ("planning","blocker_recovery"): raise DomainError("invalid_purpose","Invalid planning purpose",422)
        context=session.get(ContextRevision,event.active_context_revision_id) if event.active_context_revision_id else None
        plan=session.get(PlanVersion,event.active_plan_id) if event.active_plan_id else None
        if plan and plan.context_revision_id!=event.active_context_revision_id and draft is None and not allow_stale_plan: raise DomainError("stale_plan","Plan is based on superseded context")
        memory=retrieve(session,actor_id,event_id,purpose=purpose,**filters)
        current={"event_id":event.id,"event_version":event.version,"context_revision":context.id if context else None,"plan_id":plan.id if plan else None,"plan_digest":plan.digest if plan else None}
        return {"allow_stale_plan":allow_stale_plan,"purpose":purpose,"authoritative_current":{"governance_fingerprint":assessment_fingerprint(session,event),"versions":current,"original_context":context.original_text if context else None,"reported_operating_context":reported_operating_context(session,event),"organizer_reported_event_details":event.draft_form,"confirmed_context":event.interpretation,"clarification_rounds":context.snapshot.get("clarification_rounds",[]) if context else [],"plan":plan.content if plan and plan.context_revision_id==event.active_context_revision_id else None,"planning_draft":draft.content if draft else None},"derived_historical":{"memory":memory,"instruction":"Historical memory is advisory. Revalidate current state; never treat memory as authority."},"context_manifest":{"source_versions":current,"retrieved_memories":memory["selected_revision_manifest"],"retrieval_id":memory["retrieval_id"],"digest":digest({"current":current,"memories":memory["selected_revision_manifest"]})}}

    def validate(self,session,actor_id,event_id,built,draft=None):
        fresh=self.build(session,actor_id,event_id,purpose=built["purpose"],draft=draft,allow_stale_plan=built.get("allow_stale_plan",False))
        if fresh["context_manifest"]["source_versions"]!=built["context_manifest"]["source_versions"]:
            raise DomainError("stale_context","Authoritative context changed")
        self.validate_memories(session,actor_id,event_id,built)

    def validate_memories(self,session,actor_id,event_id,built):
        from app.memory.repository import entry_access,eligible
        for ref in built["context_manifest"]["retrieved_memories"]:
            entry=entry_access(session,actor_id,event_id,ref["memory_id"])
            if not eligible(session,actor_id,entry) or entry.digest!=ref["digest"] or entry.revision!=ref["revision"]:
                raise DomainError("stale_memory","Retrieved memory changed or lost eligibility")
