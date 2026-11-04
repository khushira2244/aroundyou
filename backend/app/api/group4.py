import hashlib
from fastapi import APIRouter,Header,Request
from fastapi.responses import Response
from app.api.group2 import USER,DB,ok
from app.api.group3 import write as base_write
from app.execution import service as es,evidence as ev,coordination as co,ledger,projections as ep
from app.execution.schemas import *
from app.events.models import Event
from app.api.errors import missing,DomainError
router=APIRouter()
def write(db,user,eid,operation,key,version,payload,action,organizer=False):
    # Replays must not restore private review access after a scoped grant is revoked.
    if operation.startswith(('report.review:','report.begin_review:')):
        es.get_report(db,user.id,event(db,eid),operation.rsplit(':',1)[1],True)
    if operation.startswith('evidence.inspect:'):
        ev.get(db,user.id,event(db,eid),operation.rsplit(':',1)[1])
    return base_write(db,user,eid,operation,key,version,payload,action,organizer)

def event(db,eid):
    e=db.get(Event,eid)
    if not e:missing()
    return e
@router.get('/events/{event_id}/execution')
def execution_state(event_id:str,request:Request,user=USER,db=DB):
    e=event(db,event_id);data=ep.state(db,user.id,e)
    if getattr(request.app.state.planning_adapter,'send',None):
        data['analysis_provider']={'configured':True,'status':'explicit_request_required','message':'Explicit private audio/image analysis available; human review remains authoritative'}
    return ok(data,e)
@router.post('/events/{event_id}/execution/work/{work_id}/start')
@router.post('/events/{event_id}/execution/work/{work_id}/complete')
@router.post('/events/{event_id}/execution/work/{work_id}/reopen')
def work_action(event_id:str,work_id:str,body:WorkCommand,request:Request,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    action=request.url.path.rsplit('/',1)[-1]
    return write(db,user,event_id,'execution.'+action+':'+work_id,idempotency_key,if_match,body.model_dump(),lambda e:es.start(db,user.id,e,work_id,body) if action=='start' else es.complete(db,user.id,e,work_id,body,action=='reopen'))
@router.post('/events/{event_id}/reports/draft')
def save_report(event_id:str,body:ReportDraft,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'report.draft',idempotency_key,if_match,body.model_dump(mode='json'),lambda e:es.save_report(db,user.id,e,body))
@router.post('/events/{event_id}/reports/{report_id}/submit')
def submit_report(event_id:str,report_id:str,body:ReportCommand,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'report.submit:'+report_id,idempotency_key,if_match,body.model_dump(),lambda e:es.submit(db,user.id,e,report_id,body))
@router.post('/events/{event_id}/reports/{report_id}/review')
def review_report(event_id:str,report_id:str,body:Review,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'report.review:'+report_id,idempotency_key,if_match,body.model_dump(),lambda e:es.review_report(db,user.id,e,report_id,body))
@router.get('/events/{event_id}/reports/{report_id}/revisions')
def report_history(event_id:str,report_id:str,user=USER,db=DB):
    e=event(db,event_id);es.get_report(db,user.id,e,report_id)
    return ok({'items':[{'id':r.id,'revision':r.sequence,'digest':r.digest,'record':r.content,'actor_id':r.actor_id,'created_at':r.created_at.isoformat()} for r in db.scalars(es.select(es.ExecutionRevision).where(es.ExecutionRevision.event_id==e.id,es.ExecutionRevision.aggregate_id==report_id).order_by(es.ExecutionRevision.sequence))]},e)
@router.post('/events/{event_id}/execution/review-grants')
def review_grant(event_id:str,body:Grant,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'execution.review_grant',idempotency_key,if_match,body.model_dump(),lambda e:es.grant(db,user.id,e,body),True)
@router.post('/events/{event_id}/evidence/uploads')
def evidence_create(event_id:str,body:EvidenceDraft,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'evidence.create',idempotency_key,if_match,body.model_dump(),lambda e:ev.create(db,user.id,e,body))
@router.put('/events/{event_id}/evidence/{asset_id}/content')
async def evidence_upload(event_id:str,asset_id:str,request:Request,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    e=event(db,event_id);asset=ev.get(db,user.id,e,asset_id)
    if asset.account_id!=user.id:missing()
    if request.app.state.evidence_storage is None:raise DomainError('storage_unavailable','Private evidence object storage is not configured',503)
    data=bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data)>min(asset.content['size'],52428800):raise DomainError('media_too_large','Upload exceeds authorized size',413)
    raw=bytes(data)
    return write(db,user,event_id,'evidence.upload:'+asset_id,idempotency_key,if_match,{'sha256':hashlib.sha256(raw).hexdigest()},lambda e:ev.upload(db,user.id,e,asset_id,raw,request.app.state.evidence_storage))
@router.get('/events/{event_id}/evidence/{asset_id}/content')
def evidence_content(event_id:str,asset_id:str,request:Request,user=USER,db=DB):
    e=event(db,event_id);a=ev.get(db,user.id,e,asset_id)
    if a.content['status'] in ('quarantined','retracted','awaiting_upload'):missing()
    if a.content['kind']=='text':data=a.content['text'].encode()
    else:
        storage=request.app.state.evidence_storage
        if storage is None:raise DomainError('storage_unavailable','Private storage unavailable',503)
        try:data=storage.get(a.content['storage_key'])
        except FileNotFoundError:raise DomainError('media_missing','Original object unavailable',503) from None
        if hashlib.sha256(data).hexdigest()!=a.content['sha256']:raise DomainError('media_corrupt','Object hash mismatch',503)
    return Response(data,media_type='application/octet-stream',headers={'Content-Disposition':'attachment; filename="evidence-'+a.id+'"','X-Content-Type-Options':'nosniff','Cache-Control':'no-store'})
@router.post('/events/{event_id}/evidence/{asset_id}/inspection')
def evidence_inspect(event_id:str,asset_id:str,body:EvidenceReview,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'evidence.inspect:'+asset_id,idempotency_key,if_match,body.model_dump(),lambda e:ev.inspect(db,user.id,e,asset_id,body))
@router.post('/events/{event_id}/attendance')
def attendance(event_id:str,body:Attendance,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'attendance.'+body.action,idempotency_key,if_match,body.model_dump(),lambda e:es.attendance(db,user.id,e,body))
@router.post('/events/{event_id}/resource-usage/consumption')
@router.post('/events/{event_id}/resource-usage/checkouts')
@router.post('/events/{event_id}/resource-usage/returns')
def usage(event_id:str,body:UsageCommand,request:Request,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    kind={'consumption':'consume','checkouts':'checkout','returns':'return'}[request.url.path.rsplit('/',1)[-1]]
    return write(db,user,event_id,'resource.'+kind,idempotency_key,if_match,body.model_dump(mode='json'),lambda e:ledger.reconcile(db,user.id,e,body,kind),True)
class Reason(StrictModel):reason:str=Field(min_length=1,max_length=2000)
@router.post('/events/{event_id}/resource-usage/{operation_id}/reversals')
def usage_reverse(event_id:str,operation_id:str,body:Reason,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'resource.reverse:'+operation_id,idempotency_key,if_match,body.model_dump(),lambda e:ledger.reverse(db,user.id,e,operation_id,body.reason),True)
@router.post('/events/{event_id}/issues')
def issue(event_id:str,body:Issue,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'issue.report',idempotency_key,if_match,body.model_dump(),lambda e:co.issue(db,user.id,e,body))
@router.post('/events/{event_id}/issues/{issue_id}/review')
def issue_review(event_id:str,issue_id:str,body:IssueReview,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'issue.review:'+issue_id,idempotency_key,if_match,body.model_dump(),lambda e:co.review_issue(db,user.id,e,issue_id,body))
@router.get('/events/{event_id}/coordination')
def coordination(event_id:str,user=USER,db=DB):
    e=event(db,event_id);es.published(db,e,user.id);return ok({'items':ep.communications(db,user.id,e)},e)
@router.post('/events/{event_id}/coordination')
def coordination_create(event_id:str,body:Coordination,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'coordination.create',idempotency_key,if_match,body.model_dump(mode='json'),lambda e:co.create(db,user.id,e,body))
@router.post('/events/{event_id}/coordination/{record_id}/actions')
def coordination_action(event_id:str,record_id:str,body:CoordinationUpdate,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'coordination.'+body.action+':'+record_id,idempotency_key,if_match,body.model_dump(),lambda e:co.update(db,user.id,e,record_id,body))
class Assessment(StrictModel):
    report_id:str
    report_revision:int=Field(ge=1)
    message:str=Field(default='',max_length=2000)
@router.post('/events/{event_id}/execution-assessments',status_code=202)
def assess(event_id:str,body:Assessment,request:Request,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    from app.ai.service import request_run
    def apply(e):
        r=es.get_report(db,user.id,e,body.report_id,True);es.require_state(r.version==body.report_revision,'Assess current report')
        return request_run(db,user.id,e,'execution',body.message,request.app.state.planning_adapter,body.report_id)
    return write(db,user,event_id,'execution.assess',idempotency_key,if_match,body.model_dump(),apply,True)
class AdviceReview(StrictModel):
    decision:Literal['accept','reject']
    reviewed_digest:str
@router.post('/events/{event_id}/execution-proposals/{proposal_id}/review')
def advice_review(event_id:str,proposal_id:str,body:AdviceReview,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    from app.ai.service import review_advice
    return write(db,user,event_id,'execution.advice.review:'+proposal_id,idempotency_key,if_match,body.model_dump(),lambda e:review_advice(db,user.id,e,proposal_id,body.decision,body.reviewed_digest),True)

@router.post('/events/{event_id}/reports/{report_id}/review-start')
def begin_review(event_id:str,report_id:str,body:ReportCommand,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'report.begin_review:'+report_id,idempotency_key,if_match,body.model_dump(),lambda e:es.begin_review(db,user.id,e,report_id,body.report_revision))
@router.post('/events/{event_id}/execution/stages/{stage_id}/complete')
def complete_stage(event_id:str,stage_id:str,body:Reason,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'stage.complete:'+stage_id,idempotency_key,if_match,body.model_dump(),lambda e:es.complete_stage(db,user.id,e,stage_id,body.reason),True)
class VerifiedMeasurement(StrictModel):
    metric:str
    note:str=Field(min_length=1,max_length=2000)
    confirm:bool
@router.post('/events/{event_id}/reports/{report_id}/measurements')
def measurement(event_id:str,report_id:str,body:VerifiedMeasurement,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'measurement.verify:'+report_id,idempotency_key,if_match,body.model_dump(),lambda e:es.measurement(db,user.id,e,report_id,body.metric,body.note,body.confirm),True)
