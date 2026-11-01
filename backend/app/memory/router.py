from typing import Literal
from fastapi import APIRouter, Depends, Header, Query, Request
from app.api.dependencies import identity, session
from app.api.errors import missing
from app.access.authorization import require, allowed
from app.memory.models import MemoryRun
from app.memory.schemas import ExtractionRequest, ReviewRequest, CorrectionRequest, RetractionRequest, SourceRef
from app.memory.service import enqueue, resolved_inputs, review, correct, retract
from app.memory.retrieval import retrieve, get_memory
from app.shared.idempotency import execute_once

router=APIRouter(prefix="/events/{event_id}/memory")

def response(data): return {"data":data,"meta":{}}

@router.post("/extractions",status_code=202)
def extract(event_id: str, body: ExtractionRequest, request: Request, idempotency_key: str = Header(min_length=1,max_length=128), user=Depends(identity), db=Depends(session, scope="function")):
    require(db,user.id,event_id,"memory:extract")
    resolved_inputs(db,user.id,event_id,body.source_refs)
    if body.extractor=="open_weight" and request.app.state.extractor is None:
        from app.api.errors import DomainError
        raise DomainError("extractor_unavailable","No live open-weight extractor configured",503)
    return response({"run":execute_once(db,user.id,event_id,"memory.extract",idempotency_key,body.model_dump(),lambda:enqueue(db,user.id,event_id,body))})

@router.get("/extractions/{run_id}")
def read_run(event_id: str, run_id: str, user=Depends(identity), db=Depends(session, scope="function")):
    require(db,user.id,event_id,"memory:read")
    run=db.get(MemoryRun,run_id)
    if not run or run.event_id!=event_id or run.kind!="extraction" or (run.requester_id!=user.id and not allowed(db,user.id,event_id,"memory:review")): missing()
    from app.shared.source_resolver import resolve
    from app.api.errors import DomainError
    for ref in run.source_manifest:
        try: resolve(db,user.id,event_id,SourceRef.model_validate(ref))
        except DomainError as exc:
            if exc.code!="stale_source": raise
    return response({"run":{"run_id":run.id,"kind":"extraction","status":run.status,"source_manifest_digest":run.source_manifest_digest,"candidate_ids":run.output_entry_ids,"error":{"code":run.failure_code,"retryable":run.status=="queued"} if run.failure_code else None,"status_url":f"/v1/events/{event_id}/memory/extractions/{run.id}"}})

@router.get("")
def list_memory(event_id: str, q: str | None=Query(default=None,max_length=500), purpose: Literal["planning","blocker_recovery","event_review"]="planning", kind: Literal["context","plan","decision","lesson"] | None=None, evidence_stage: Literal["proposed","attempted","verified"] | None=None, outcome: Literal["unknown","successful","failed","mixed","inconclusive"] | None=None, category: str | None=Query(default=None,max_length=80),work_pattern: str | None=Query(default=None,max_length=200),tags: list[str]=Query(default=[],max_length=20),conditions: list[str]=Query(default=[],max_length=20),limit: int=Query(default=20,ge=1,le=20),cursor: str | None=Query(default=None,max_length=1000),include_reusable: bool=False,user=Depends(identity),db=Depends(session, scope="function")):
    if any(len(x)>300 for x in tags+conditions):
        from app.api.errors import DomainError
        raise DomainError("invalid_filter","Filter item too long",422)
    return response(retrieve(db,user.id,event_id,q=q,purpose=purpose,kind=kind,evidence_stage=evidence_stage,outcome=outcome,category=category,work_pattern=work_pattern,tags=tags,conditions=conditions,limit=limit,cursor=cursor,include_reusable=include_reusable))

@router.get("/{memory_id}")
def read_memory(event_id: str, memory_id: str, user=Depends(identity), db=Depends(session, scope="function")):
    return response({"memory":get_memory(db,user.id,event_id,memory_id)})

@router.post("/{memory_id}/review")
def review_memory(event_id: str,memory_id: str,body: ReviewRequest,if_match: str=Header(),idempotency_key: str=Header(min_length=1,max_length=128),user=Depends(identity),db=Depends(session, scope="function")):
    return response(review(db,user.id,event_id,memory_id,body,idempotency_key,if_match.strip('"')))

@router.post("/{memory_id}/corrections")
def correct_memory(event_id: str,memory_id: str,body: CorrectionRequest,if_match: str=Header(),idempotency_key: str=Header(min_length=1,max_length=128),user=Depends(identity),db=Depends(session, scope="function")):
    return response(correct(db,user.id,event_id,memory_id,body,idempotency_key,if_match.strip('"')))

@router.post("/{memory_id}/retract")
def retract_memory(event_id: str,memory_id: str,body: RetractionRequest,if_match: str=Header(),idempotency_key: str=Header(min_length=1,max_length=128),user=Depends(identity),db=Depends(session, scope="function")):
    return response(retract(db,user.id,event_id,memory_id,body,idempotency_key,if_match.strip('"')))
