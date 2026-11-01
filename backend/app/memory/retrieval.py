from sqlalchemy import select, func, cast, Text
from app.memory.models import MemoryEntry, MemoryRun
from app.memory.repository import entry_access, eligible, source_rows, current_sources
from app.access.authorization import require
from app.shared.types import uid, digest
from app.api.errors import missing, DomainError

def serialize(session,entry):
    rows=source_rows(session,entry)
    assertions=[]
    for raw in entry.assertions:
        assertion={k:v for k,v in raw.items() if k!="source_refs"}
        assertion["citations"]=[{"memory_source_id":r.id,"permitted_source_reference":{"kind":r.source_kind,"id":r.source_id},"revision":r.source_revision,"digest":r.source_digest,"relation":r.relation} for r in rows if r.assertion_id==raw["assertion_id"]]
        assertions.append(assertion)
    return {"memory_id":entry.id,"logical_memory_id":entry.logical_memory_id,"revision":entry.revision,"version":entry.version,"event_id":entry.event_id,"kind":entry.kind,"title":entry.title,"lifecycle":entry.lifecycle,"visibility":entry.visibility,"assertions":assertions,"applicability":entry.applicability,"provenance":{"origin":entry.origin,"schema_version":entry.schema_version,"extractor_version":entry.extractor_version,"model_profile":entry.model_profile,"run_id":entry.run_id,"review_decision_id":entry.review_decision_id},"digest":entry.digest,"supersedes_id":entry.supersedes_id}

def get_memory(session,actor_id,event_id,memory_id):
    entry=entry_access(session,actor_id,event_id,memory_id)
    if not eligible(session,actor_id,entry): missing()
    return serialize(session,entry)

def retrieve(session,actor_id,event_id,q=None,purpose="planning",kind=None,evidence_stage=None,outcome=None,category=None,work_pattern=None,tags=None,conditions=None,limit=20,cursor=None,include_reusable=False):
    require(session,actor_id,event_id,"memory:read")
    filters={"q":q,"purpose":purpose,"kind":kind,"evidence_stage":evidence_stage,"outcome":outcome,"category":category,"work_pattern":work_pattern,"tags":tags or [],"conditions":conditions or [],"include_reusable":include_reusable}
    query_digest=digest(filters)
    offset=0
    if cursor:
        # Cursor binds pagination to actor/event/query; it never grants access.
        import base64,json
        try:
            data=json.loads(base64.urlsafe_b64decode(cursor))
            expected=digest({"actor":actor_id,"event":event_id,"query":query_digest})
            if data["binding"]!=expected or not isinstance(data["offset"],int) or not 0<=data["offset"]<=10000: raise ValueError()
            offset=data["offset"]
        except Exception: raise DomainError("invalid_cursor","Invalid retrieval cursor",422) from None
    if not 1<=limit<=20: raise DomainError("invalid_limit","Limit must be 1..20",422)
    query=select(MemoryEntry).where(MemoryEntry.event_id==event_id,MemoryEntry.lifecycle=="published")
    if kind: query=query.where(MemoryEntry.kind==kind)
    for key,value in [("category",category),("work_pattern",work_pattern)]:
        if value: query=query.where(MemoryEntry.applicability[key].astext==value)
    for key,value in [("tags",tags),("conditions",conditions)]:
        if value: query=query.where(MemoryEntry.applicability[key].contains(value))
    rank=func.ts_rank(func.to_tsvector('simple',MemoryEntry.title+" "+cast(MemoryEntry.assertions,Text)),func.plainto_tsquery('simple',q or ""))
    if q:
        query=query.where(func.to_tsvector('simple',MemoryEntry.title+" "+cast(MemoryEntry.assertions,Text)).op('@@')(func.plainto_tsquery('simple',q)))
    query=query.order_by(rank.desc(),MemoryEntry.id) if q else query.order_by(MemoryEntry.id)
    # Batch scan after indexed coarse filters. Only eligible rows count towards pagination.
    selected=[];eligible_position=0;has_more=False
    for entry in session.scalars(query.execution_options(yield_per=100)):
        if not eligible(session,actor_id,entry): continue
        if evidence_stage and not any(a["evidence_stage"]==evidence_stage for a in entry.assertions): continue
        if outcome and not any(a["outcome"]==outcome for a in entry.assertions): continue
        if eligible_position<offset: eligible_position+=1;continue
        if len(selected)==limit: has_more=True;break
        selected.append(entry);eligible_position+=1
    import base64,json
    next_cursor=base64.urlsafe_b64encode(json.dumps({"binding":digest({"actor":actor_id,"event":event_id,"query":query_digest}),"offset":offset+len(selected)}).encode()).decode() if has_more else None
    retrieval_id=uid()
    manifest=[{"memory_id":e.id,"revision":e.revision,"digest":e.digest} for e in selected]
    refs={}
    for entry in selected:
        for row in source_rows(session,entry):
            ref={"source_kind":row.source_kind,"source_id":row.source_id,"source_revision":row.source_revision,"source_digest":row.source_digest}
            refs[digest(ref)]=ref
    sources=list(refs.values())
    session.add(MemoryRun(id=retrieval_id,event_id=event_id,requester_id=actor_id,kind="retrieval",purpose=purpose,extractor="postgres-lexical",schema_version="memory-v1",dedup_key=retrieval_id,source_manifest=sources,source_manifest_digest=digest(sources),query_digest=query_digest,selection_manifest=manifest,status="succeeded",output_entry_ids=[e.id for e in selected]))
    session.flush()
    return {"items":[serialize(session,e) for e in selected],"retrieval_id":retrieval_id,"query_digest":query_digest,"policy_version":"event-only-v1","selected_revision_manifest":[{"memory_id":e.id,"revision":e.revision,"digest":e.digest} for e in selected],"applicability_reasons":["Exact supplied structured conditions matched; other conditions remain unverified"],"limitations":["Event-scoped only; cross-event reuse is disabled in Group 1","Relevance is not verification"],"next_cursor":next_cursor}

class PostgresMemoryRetrieval:
    def retrieve(self, session, actor_id, event_id, **filters):
        return retrieve(session,actor_id,event_id,**filters)
