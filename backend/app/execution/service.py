from copy import deepcopy
from decimal import Decimal
from sqlalchemy import select
from app.execution.models import *
from app.participation.models import Assignment,AssignmentTerms
from app.participation.service import published,effective_assignment,require_state
from app.access.authorization import allowed,require
from app.events.models import Event
from app.shared.types import uid,digest,now
from app.shared.audit import audit
from app.api.errors import missing,DomainError

def owner(db,actor,e):return allowed(db,actor,e.id,'plan:write') and allowed(db,actor,e.id,'source:private')
def plan(db,e,actor,current=False):return published(db,e,actor,current).snapshot['plan']
def work(db,e,actor,wid):
    w=next((x for x in plan(db,e,actor)['work'] if x['id']==wid),None)
    if not w:missing()
    return w
def assignment(db,actor,e,wid):
    for a in db.scalars(select(Assignment).where(Assignment.event_id==e.id,Assignment.account_id==actor)):
        t=db.get(AssignmentTerms,a.current_terms_id)
        if effective_assignment(db,a)=='assignment_accepted' and wid in t.content['work_ids']:return a,t
    missing()
def reviewer(db,actor,e,w):
    if owner(db,actor,e):return True
    grant=db.scalar(select(ExecutionReviewGrant).where(ExecutionReviewGrant.event_id==e.id,ExecutionReviewGrant.account_id==actor,ExecutionReviewGrant.stage_id==w['stage_id'],ExecutionReviewGrant.plan_id==e.active_plan_id,ExecutionReviewGrant.active.is_(True)))
    if not grant:return False
    try:assignment(db,actor,e,w['id']);return True
    except DomainError:
        # A stage lead may review other work in their explicitly granted stage.
        for x in plan(db,e,actor)['work']:
            if x['stage_id']==w['stage_id']:
                try:assignment(db,actor,e,x['id']);return True
                except DomainError:pass
        return False

def record(db,actor,e,row,kind,data,stage='attempted',outcome='unknown',criteria=None):
    row.version+=1;row.content=deepcopy(data);db.flush()
    snapshot={'record':{**{k:v for k,v in data.items() if k!='storage_key'},**{k:getattr(row,k) for k in ('plan_id','assignment_id','terms_id') if hasattr(row,k)},**({'report_id':row.report_id} if hasattr(row,'report_id') else {}),**({'work_id':row.work_id} if hasattr(row,'work_id') else {})},'evidence_stage':stage,'outcome':outcome,'criteria':criteria,'actor_id':actor}
    rev=ExecutionRevision(id=uid(),event_id=e.id,aggregate_id=row.id,sequence=row.version,kind=kind,content=snapshot,digest=digest(snapshot),actor_id=actor)
    db.add(rev);db.flush();e.version+=1
    from app.events.source_revisions import capture
    from app.memory.schemas import SourceRef
    if not (isinstance(row,WorkReport) and data.get('review_status')=='draft') and not (isinstance(row,EvidenceAsset) and db.get(WorkReport,row.report_id).content.get('review_status')=='draft'):
        capture(db,e.creator_id,e.id,SourceRef(source_kind='execution',source_id=rev.id,source_revision=rev.sequence,source_digest=rev.digest))
    audit(db,actor,e.id,'execution.'+kind,row.id,revision=row.version,source_id=rev.id)
    return row

def execution(db,e,wid,create=False):
    row=db.scalar(select(WorkExecution).where(WorkExecution.event_id==e.id,WorkExecution.plan_id==e.active_plan_id,WorkExecution.work_id==wid))
    if not row and create:
        row=WorkExecution(id=uid(),event_id=e.id,plan_id=e.active_plan_id,work_id=wid,content={'status':'not_started','verified_percent':0,'reported_percent':None,'started_at':None,'verified_at':None});db.add(row);db.flush()
    return row

def readiness(db,e,actor,w):
    p=plan(db,e,actor);pred=set(w['dependency_ids'])|{x['predecessor'] for x in p['dependencies'] if x['successor']==w['id']}
    stage=next(x for x in p['stages'] if x['id']==w['stage_id'])
    pred|={x['id'] for x in p['work'] if x['stage_id'] in stage['dependency_ids']}
    unresolved=[wid for wid in pred if not (execution(db,e,wid) and execution(db,e,wid).content['status']=='completed')]
    issues=[i.id for i in db.scalars(select(WorkIssue).where(WorkIssue.event_id==e.id,WorkIssue.plan_id==e.active_plan_id)) if w['id'] in i.content.get('work_ids',[i.work_id]) and (i.content.get('confirmed_blocking_condition') or i.content.get('protective_hold') or i.content.get('blocking')) and not i.content.get('condition_cleared')]
    return {'ready':not unresolved and not issues,'unverified_dependencies':sorted(unresolved),'blocking_issue_ids':issues,'preconditions':w['conditions']+w['exclusion_constraints']}

def start(db,actor,e,wid,body):
    published(db,e,actor,True);assignment(db,actor,e,wid);w=work(db,e,actor,wid);r=readiness(db,e,actor,w)
    require_state(r['ready'],'Unverified dependencies or uncleared blocking condition')
    require_state(not r['preconditions'] or body.preconditions_confirmed,'Explicit acknowledgement of current work preconditions required')
    row=execution(db,e,wid,True);require_state(row.content['status']!='completed','Reopen verified work before another attempt')
    data=deepcopy(row.content);data.update(status='in_progress',started_at=data.get('started_at') or now().isoformat(),preconditions_confirmed=body.preconditions_confirmed)
    record(db,actor,e,row,'work.start',data);return {'work_id':wid,'status':'in_progress'}

def report_work(db,r):
    from app.planning.models import PlanVersion
    p=db.get(PlanVersion,r.plan_id)
    w=next((w for w in p.content['work'] if w['id']==r.work_id),None)
    if not w:missing()
    return w

def get_report(db,actor,e,rid,review=False):
    r=db.get(WorkReport,rid)
    if not r or r.event_id!=e.id:missing()
    w=report_work(db,r)
    if r.account_id!=actor and (r.content.get('review_status')=='draft' or not reviewer(db,actor,e,w)):missing()
    if review and (r.account_id==actor or not reviewer(db,actor,e,w)):missing()
    return r

def report_dto(db,actor,e,r):
    w=report_work(db,r);editable=False
    try:
        a,t=assignment(db,actor,e,r.work_id);editable=r.account_id==actor and t.id==r.terms_id and r.content['review_status'] in ('draft','needs_correction','clarification_requested')
    except DomainError:pass
    return {'id':r.id,'account_id':r.account_id,'stage_id':w['stage_id'],'work_ids':[r.work_id],'plan_id':r.plan_id,'revision':r.version,'assignment_id':r.assignment_id,'terms_id':r.terms_id,'completion_approved_by':(execution(db,e,r.work_id).content.get('completed_by') if execution(db,e,r.work_id) and execution(db,e,r.work_id).content.get('verified_report_id')==r.id and execution(db,e,r.work_id).content['status']=='completed' else None),**r.content,'resource_usage':[{**u,'quantity':float(u['quantity'])} for u in r.content.get('resource_usage',[])],'review_status':'verified' if r.content['review_status']=='accepted' else r.content['review_status'],'can_edit':editable,'can_review':r.account_id!=actor and reviewer(db,actor,e,w)}

def save_report(db,actor,e,b):
    published(db,e,actor,True);a,t=assignment(db,actor,e,b.work_id);w=work(db,e,actor,b.work_id)
    current=execution(db,e,b.work_id);require_state(not current or current.content['status']!='completed','A human must reopen completed work before another execution report')
    r=get_report(db,actor,e,b.report_id) if b.report_id else None
    if r:require_state(r.account_id==actor and r.work_id==b.work_id and r.terms_id==t.id and r.version==b.report_revision and r.content['review_status'] in ('draft','needs_correction','clarification_requested'),'Edit exact own draft/correction with current assignment terms')
    else:
        r=WorkReport(id=uid(),event_id=e.id,plan_id=e.active_plan_id,assignment_id=a.id,terms_id=t.id,account_id=actor,work_id=w['id'],content={});db.add(r);db.flush()
    resources={x['id']:x for x in plan(db,e,actor)['resources']};usage=[]
    reconciled=bool(db.scalar(select(ResourceOperation.id).where(ResourceOperation.report_id==r.id)))
    old={x['id']:x for x in r.content.get('resource_usage',[])}
    for u in b.resource_usage:
        resource=resources.get(u.resource_id);require_state(resource and resource['id'] in w['resource_requirement_ids'] and resource['unit']==u.unit,'Usage must match work-linked resource and exact unit')
        require_state(u.kind==resource['kind'] or u.kind=='reusable' and resource['kind']=='equipment','Resource kind mismatch')
        if u.id:require_state(u.id in old,'Usage identifier must come from this report')
        usage.append({**u.model_dump(mode='json'),'id':u.id or uid()})
    if reconciled:require_state(usage==r.content.get('resource_usage',[]),'Reconciled usage history cannot be silently edited; append a new report or record a ledger correction')
    require_state(len({u['id'] for u in usage})==len(usage),'Duplicate usage')
    data={**r.content,'original_text':b.body,'source_type':'participant_entry','claim':b.claim,'remaining_work':b.remaining_work,'reported_percent':b.progress_percent,'resource_usage':usage,'measurements':[m.model_dump() for m in b.measurements],'evidence_ids':r.content.get('evidence_ids',[]),'review_notes':r.content.get('review_notes',[]),'review_status':'draft','saved_at':now().isoformat(),'submitted_at':None}
    record(db,actor,e,r,'report.draft',data)
    return {'report':report_dto(db,actor,e,r)}

def submit(db,actor,e,rid,b):
    r=get_report(db,actor,e,rid);a,t=assignment(db,actor,e,r.work_id)
    require_state(r.account_id==actor and r.version==b.report_revision and r.terms_id==t.id and r.plan_id==e.active_plan_id and r.content['review_status']=='draft','Submit exact current draft')
    require_state(bool(r.content['original_text'].strip() or r.content['evidence_ids']),'Provide original statement or evidence')
    for eid in r.content['evidence_ids']:
        asset=db.get(EvidenceAsset,eid);require_state(asset and asset.content['status'] in ('pending_inspection','accepted_for_review'),'Every attached original must be uploaded; missing, quarantined or retracted evidence blocks submission')
    data={**r.content,'review_status':'submitted','submitted_at':now().isoformat()};record(db,actor,e,r,'report.submit',data)
    row=execution(db,e,r.work_id,True);record(db,actor,e,row,'work.submit',{**row.content,'status':'submitted_for_review','reported_percent':r.content['reported_percent']})
    return {'report':report_dto(db,actor,e,r)}

def review_report(db,actor,e,rid,b):
    published(db,e,actor,True)
    r=get_report(db,actor,e,rid,True)
    require_state(r.version==b.report_revision and r.plan_id==e.active_plan_id and r.content['review_status'] in ('submitted','under_review'),'Review exact submitted report revision')
    assets=[db.get(EvidenceAsset,x) for x in r.content['evidence_ids']]
    require_state(b.evidence_versions=={x.id:x.version for x in assets},'Review exact evidence revisions')
    if b.decision=='accept':require_state(all(x.content['status']=='accepted_for_review' for x in assets),'Evidence is unavailable or retracted')
    data={**r.content,'review_notes':r.content['review_notes']+[b.note],'review_status':{'accept':'accepted','reject':'rejected','request_correction':'needs_correction','clarify':'clarification_requested'}[b.decision],'reviewed_at':now().isoformat(),'reviewer_id':actor,'reviewed_evidence_versions':b.evidence_versions}
    if b.decision=='accept':require_state(b.verified_percent is not None,'Human must explicitly specify cumulative verified progress')
    record(db,actor,e,r,'report.review',data,'verified' if b.decision=='accept' else 'attempted',b.outcome,b.note)
    if b.decision=='accept':
        row=execution(db,e,r.work_id,True);require_state(b.verified_percent>=row.content.get('verified_percent',0),'Reopen before reducing verified progress')
        record(db,actor,e,row,'work.verify_progress',{**row.content,'verified_percent':b.verified_percent,'verified_report_id':r.id,'verified_report_revision':r.version,'status':'submitted_for_review','verified_at':now().isoformat()},'verified','inconclusive',b.note)
    return {'report':report_dto(db,actor,e,r)}

def complete(db,actor,e,wid,b,reopen=False):
    if not reopen:published(db,e,actor,True)
    w=work(db,e,actor,wid)
    if not reviewer(db,actor,e,w):missing()
    row=execution(db,e,wid,True);require_state(bool(b.reason),'Record the exact human completion/reopening reason')
    if reopen:
        require_state(row.content['status']=='completed' or row.content['verified_percent']>0,'No verified work to reopen')
        previous=db.get(WorkReport,row.content.get('verified_report_id'))
        if previous and previous.content['review_status']=='accepted':record(db,actor,e,previous,'report.reopen',{**previous.content,'review_status':'needs_correction','review_notes':previous.content['review_notes']+[b.reason]},'attempted','inconclusive',b.reason)
        record(db,actor,e,row,'work.reopen',{**row.content,'status':'reopened','verified_percent':0,'verified_at':None,'reason':b.reason},'attempted','inconclusive',b.reason)
    else:
        require_state(row.content['status']!='completed' and row.content['verified_percent']==100 and readiness(db,e,actor,w)['ready'],'Exact verified progress and cleared dependencies required')
        r=db.get(WorkReport,row.content.get('verified_report_id'));require_state(r and r.account_id!=actor and r.version==row.content.get('verified_report_revision') and r.content['review_status']=='accepted' and r.content['claim']=='completion' and not r.content['remaining_work'],'Current human-reviewed completion claim with no remaining work required')
        require_state(all(db.get(EvidenceAsset,k).content['status']=='accepted_for_review' and db.get(EvidenceAsset,k).version==v for k,v in r.content.get('reviewed_evidence_versions',{}).items()),'Reviewed evidence changed')
        record(db,actor,e,row,'work.complete',{**row.content,'status':'completed','completed_at':now().isoformat(),'completed_by':actor,'reason':b.reason},'verified','inconclusive',b.reason)
    return {'status':row.content['status']}

def grant(db,actor,e,b):
    if not owner(db,actor,e):missing()
    require_state(b.confirm,'Explicit review grant required')
    p=plan(db,e,actor);require_state(b.stage_id in {w['stage_id'] for w in p['work']},'Published stage required')
    if b.active:
        require_state(any(effective_assignment(db,a)=='assignment_accepted' and any(work(db,e,actor,w)['stage_id']==b.stage_id for w in db.get(AssignmentTerms,a.current_terms_id).content['work_ids']) for a in db.scalars(select(Assignment).where(Assignment.event_id==e.id,Assignment.account_id==b.account_id))),'Delegate must have a current accepted assignment in stage')
    row=db.scalar(select(ExecutionReviewGrant).where(ExecutionReviewGrant.event_id==e.id,ExecutionReviewGrant.account_id==b.account_id,ExecutionReviewGrant.stage_id==b.stage_id))
    if not row:row=ExecutionReviewGrant(event_id=e.id,account_id=b.account_id,stage_id=b.stage_id,plan_id=e.active_plan_id);db.add(row)
    row.active=b.active;row.plan_id=e.active_plan_id;e.version+=1;audit(db,actor,e.id,'execution.review_grant',b.account_id,stage_id=b.stage_id,active=b.active);return {'granted':b.active}

def attendance(db,actor,e,b):
    a=db.get(Assignment,b.assignment_id)
    if not a or a.event_id!=e.id:missing()
    row=db.scalar(select(AttendanceRecord).where(AttendanceRecord.assignment_id==a.id));require_state((row.version if row else 0)==b.expected_revision,'Review current attendance revision')
    if b.action=='claim':require_state(a.account_id==actor and effective_assignment(db,a)=='assignment_accepted','Only current assignee can self-report attendance')
    elif not owner(db,actor,e):missing()
    if not row:row=AttendanceRecord(id=uid(),event_id=e.id,assignment_id=a.id,account_id=a.account_id);db.add(row);db.flush()
    if b.action=='verify':require_state(row.content.get('claimed_at'),'Review actual self-reported presence before verification')
    data={**row.content,'note':b.note}
    if b.action=='claim':data.update(claimed_at=now().isoformat(),self_reported_present=b.present,verified_at=None,verified_present=None)
    else:data.update(verified_at=now().isoformat() if b.action=='verify' else None,verified_present=b.present if b.action=='verify' else None,reviewer_id=actor)
    record(db,actor,e,row,'attendance.'+b.action,data,'verified' if b.action=='verify' else 'attempted','inconclusive',b.note)
    return {'id':row.id,'revision':row.version,**data}


def begin_review(db,actor,e,rid,revision):
    r=get_report(db,actor,e,rid,True);require_state(r.version==revision and r.content['review_status']=='submitted','Begin exact submitted report review')
    record(db,actor,e,r,'report.begin_review',{**r.content,'review_status':'under_review'});return {'report':report_dto(db,actor,e,r)}
def complete_stage(db,actor,e,sid,reason):
    if not owner(db,actor,e):missing()
    ws=[w for w in plan(db,e,actor)['work'] if w['stage_id']==sid]
    require_state(ws and reason and all(execution(db,e,w['id']) and execution(db,e,w['id']).content['status']=='completed' for w in ws),'Verify every work item before exact stage completion')
    require_state(not any(x.content['stage_id']==sid and x.content['plan_id']==e.active_plan_id and x.content['work_versions']=={w['id']:execution(db,e,w['id']).version for w in ws} for x in db.scalars(select(CoordinationRecord).where(CoordinationRecord.event_id==e.id,CoordinationRecord.kind=='stage_completion'))),'Exact stage completion already recorded')
    row=CoordinationRecord(id=uid(),event_id=e.id,account_id=actor,kind='stage_completion',content={});db.add(row);db.flush()
    record(db,actor,e,row,'stage.complete',{'stage_id':sid,'plan_id':e.active_plan_id,'reason':reason,'work_versions':{w['id']:execution(db,e,w['id']).version for w in ws}},'verified','inconclusive',reason);return {'stage_id':sid,'status':'completed'}
def measurement(db,actor,e,rid,metric,note,confirm):
    if not owner(db,actor,e):missing()
    r=get_report(db,actor,e,rid,True);require_state(confirm and note and r.content['review_status']=='accepted','Human-reviewed report and explicit measurement confirmation required')
    m=next((x for x in r.content['measurements'] if x['metric']==metric),None);require_state(m is not None,'Measurement must be in original reviewed report')
    row=CoordinationRecord(id=uid(),event_id=e.id,account_id=actor,kind='measurement',content={});db.add(row);db.flush();record(db,actor,e,row,'measurement.verify',{'report_id':r.id,'report_revision':r.version,'plan_id':r.plan_id,**m,'note':note,'status':'verified'},'verified','inconclusive',note);return {'measurement_id':row.id}
