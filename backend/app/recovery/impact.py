"""Pure deterministic scope analysis. Scheduling feasibility is deliberately separate."""
from app.api.errors import DomainError
from app.shared.types import digest


def affected_scope(plan, blocked_ids, completed_ids=()):
    work={w['id']:w for w in plan['work']}
    stages={s['id']:s for s in plan['stages']}
    if len(work)!=len(plan['work']) or len(stages)!=len(plan['stages']):
        raise DomainError('invalid_graph','Duplicate work/stage identifiers',422)
    def check(nodes):
        pending={k:set(v.get('dependency_ids',[])) for k,v in nodes.items()}
        if any(not deps<=nodes.keys() for deps in pending.values()):
            raise DomainError('invalid_graph','Unknown dependency',422)
        while pending:
            ready={k for k,v in pending.items() if not v}
            if not ready:raise DomainError('dependency_cycle','Dependency cycle detected',422)
            pending={k:v-ready for k,v in pending.items() if k not in ready}
    check(stages);check(work)
    if any(w['stage_id'] not in stages for w in work.values()) or not set(blocked_ids)<=work.keys() or not set(completed_ids)<=work.keys():
        raise DomainError('invalid_scope','Unknown affected or completed work',422)
    deps={k:set(w.get('dependency_ids',[])) for k,w in work.items()}
    for k,w in work.items():
        for sid in stages[w['stage_id']].get('dependency_ids',[]):
            deps[k].update(i for i,v in work.items() if v['stage_id']==sid)
    check({k:{'dependency_ids':list(v)} for k,v in deps.items()})
    affected=set(blocked_ids);changed=True
    while changed:
        extra={k for k,v in deps.items() if v & affected}-affected
        changed=bool(extra);affected.update(extra)
    result=[]
    for k in sorted(work):
        classification=('verified_complete' if k in completed_ids else 'directly_blocked' if k in blocked_ids else 'downstream_affected' if k in affected else 'unaffected')
        result.append({'work_id':k,'classification':classification,'affected_by':sorted(deps[k]&affected),
            'resource_ids':work[k].get('resource_requirement_ids',[]),'schedule':work[k].get('schedule'),
            'skills':work[k].get('skills',[]),'conditions':work[k].get('conditions',[])})
    manifest={'work':result,'direct_work_ids':sorted(set(blocked_ids)),'affected_work_ids':sorted(affected),'preserved_complete_ids':sorted(set(completed_ids)),
        'limitations':['Dependency impact does not establish resource, staffing or scheduling feasibility','Affected work is not cancelled']}
    return {**manifest,'digest':digest(manifest)}
