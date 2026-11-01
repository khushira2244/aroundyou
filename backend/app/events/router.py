from fastapi import APIRouter, Depends
from app.api.dependencies import identity, session
from app.access.authorization import require, allowed
from app.events.models import ContextRevision
from app.planning.models import PlanVersion
router=APIRouter()
@router.get("/events/{event_id}")
def event_read(event_id: str, user=Depends(identity), db=Depends(session, scope="function")):
    event=require(db,user.id,event_id,"event:read")
    return {"data":{"event_id":event.id,"title":event.title,"category":event.category,"version":event.version,"active_context_revision_id":event.active_context_revision_id if allowed(db,user.id,event_id,"source:private") else None,"active_plan_id":event.active_plan_id},"meta":{"version":event.version}}

@router.get("/events/{event_id}/sources/current")
def current_sources(event_id: str, user=Depends(identity), db=Depends(session, scope="function")):
    event=require(db,user.id,event_id,"source:private")
    context=db.get(ContextRevision,event.active_context_revision_id) if event.active_context_revision_id else None
    plan=db.get(PlanVersion,event.active_plan_id) if event.active_plan_id else None
    refs=[]
    for kind,row in [("context",context),("plan",plan)]:
        if row: refs.append({"source_kind":kind,"source_id":row.id,"source_revision":row.sequence,"source_digest":row.content_hash if kind=="context" else row.digest})
    return {"data":{"source_refs":refs,"event_version":event.version},"meta":{}}
