"""Explicit private evidence inference. Original bytes and human authority stay separate."""
import base64,hashlib,io,json,re
from fastapi import APIRouter,Request,Depends,Header
from pydantic import Field
from sqlalchemy import select
from app.api.dependencies import identity
from app.api.errors import DomainError,missing
from app.ai.models import AIRun
from app.shared.types import uid,now
from app.shared.audit import audit
from app.shared.unit_of_work import unit_of_work
from app.shared.idempotency import execute_once
from app.memory.schemas import StrictModel
from app.events.models import Event
from app.execution import evidence as ev
from app.execution.service import get_report,record,require_state,report_work,reviewer
router=APIRouter()
class MediaRequest(StrictModel):
    concept:str=Field(default='',max_length=100)
class TranscriptReview(StrictModel):
    expected_revision:int
    text:str=Field(min_length=1,max_length=8000)
class VisionAdvice(StrictModel):
    observations:list[str]=Field(max_length=10)
    categories:list[__import__('typing').Literal['progress_evidence','resource_evidence','safety_concern','missing_or_unclear','potential_issue','other']]=Field(max_length=6)
    uncertainty:list[str]=Field(max_length=10)
    follow_up_questions:list[str]=Field(max_length=8)
    requires_human_review:__import__('typing').Literal[True]=True

def authorized(db,actor,eid,aid,operation):
    e=db.get(Event,eid)
    if not e:missing()
    a=ev.get(db,actor,e,aid);r=get_report(db,actor,e,a.report_id)
    require_state(a.content['status'] in ('pending_inspection','accepted_for_review'),'Original uploaded evidence required')
    if operation=='transcription':
        require_state(a.account_id==actor and r.content['review_status']=='draft','Transcribe only your own draft report audio')
        require_state(a.content['kind']=='audio','Select original audio')
    else:
        if not reviewer(db,actor,e,report_work(db,r)):missing()
        require_state(a.content['kind']=='image' and r.content['review_status'] in ('submitted','under_review'),'Analyze original images in submitted reports only')
    return e,a,r

def result(run):return {'run_id':run.id,'status':run.status,'result':run.context_manifest.get('result'),'error':run.failure_code}

def raw_bytes(storage,a):
    if storage is None:raise DomainError('storage_unavailable','Private evidence storage unavailable',503)
    try:raw=storage.get(a.content['storage_key'])
    except OSError:raise DomainError('storage_unavailable','Private original could not be read',503) from None
    require_state(hashlib.sha256(raw).hexdigest()==a.content['sha256'],'Original evidence hash mismatch')
    return raw

def segment(adapter,raw,mime,concept):
    from PIL import Image
    with Image.open(io.BytesIO(raw)) as im:
        im.verify()
    with Image.open(io.BytesIO(raw)) as im:w,h=im.size
    require_state(len(raw)<=2*1024*1024 and max(w,h)<=2048,'Explicit analysis supports images up to 2 MB and 2048 pixels; original stays stored')
    image='data:'+mime+';base64,'+base64.b64encode(raw).decode()
    sam=adapter.send('/responses',timeout=45,json={'model':'sam-3.1','input':[{'type':'message','role':'user','content':[{'type':'input_text','text':concept},{'type':'input_image','image_url':image}]}],'stream':False})
    require_state(sam.get('status') in (None,'completed'),'SAM did not complete')
    text=''.join(c.get('text','') for o in sam.get('output',[]) for c in o.get('content',[]) if c.get('type')=='output_text')
    require_state(len(text)<=4000000,'Segmentation response exceeds bounded storage size')
    boxes=[]
    for token in re.findall(r'<\|box;([^|]+)\|>',text):
        fields=dict(x.split('=',1) for x in token.split(';') if '=' in x)
        x1,y1,x2,y2,bw,bh=[float(fields[k]) for k in ('x1','y1','x2','y2','w','h')]
        # SAM corners are inclusive source pixels, including one-pixel regions.
        require_state(bw==w and bh==h and 0<=x1<=x2<bw and 0<=y1<=y2<bh,'Invalid SAM geometry')
        boxes.append({'x':x1/bw,'y':y1/bh,'width':(x2-x1+1)/bw,'height':(y2-y1+1)/bh,'label':concept})
    require_state(not text or '<0f>' in text,'Unrecognized SAM wire output')
    return {'model':'sam-3.1','request_id':sam.get('id'),'concept':concept,'boxes':boxes,'wire_output':text,'mask_records':text.count('<|mask;'),'image_dimensions':{'width':w,'height':h},'coordinate_space':'normalized','note':'Exact SAM wire masks retained; no raster mask decoding claimed'},image

def perform(request,actor,eid,aid,operation,body,key):
    adapter=request.app.state.planning_adapter
    if not getattr(adapter,'send',None):raise DomainError('provider_unavailable','Real Meta provider is not configured',503)
    require_state(bool(key.strip()),'Idempotency-Key required for paid evidence inference')
    if operation=='segmentation':require_state(bool(body.concept.strip()) and '\n' not in body.concept,'Provide one short object concept, not a filename or inference')
    factory=request.app.state.session_factory;created=[False]
    with unit_of_work(factory) as db:
        e,a,r=authorized(db,actor,eid,aid,operation)
        def start():
            created[0]=True;run=AIRun(id=uid(),event_id=eid,requester_id=actor,kind='evidence_'+operation,status='running',source_versions={'asset_id':aid,'asset_revision':a.version,'sha256':a.content['sha256'],'report_revision':r.version,'plan_id':r.plan_id},context_manifest={},request_message=body.concept,model_profile='muse-voice-transcribe-1.0' if operation=='transcription' else 'sam-3.1 + muse-spark-1.3')
            db.add(run);db.flush();audit(db,actor,eid,'evidence.inference.request',run.id);return {'run_id':run.id}
        started=execute_once(db,actor,eid,'evidence.'+operation+':'+aid,key,body.model_dump(),start);run=db.get(AIRun,started['run_id']);rid=run.id
        if not created[0]:return result(run)
        source=dict(run.source_versions);raw=raw_bytes(request.app.state.evidence_storage,a);mime=a.content['mime'];work=report_work(db,r);report_text=r.content['original_text']
    partial=None
    try:
        if operation=='transcription':
            from app.ai.voice import normalize_audio
            wav,seconds=normalize_audio(raw);value=adapter.transcribe(wav);value['duration_seconds']=seconds
        else:
            partial,image=segment(adapter,raw,mime,body.concept.strip())
            context={'work':work,'report_claim':report_text,'sam':{k:v for k,v in partial.items() if k!='wire_output'},'evidence_id':aid,'sha256':source['sha256']}
            response=adapter.send('/chat/completions',timeout=28,json={'model':adapter.model_profile,'messages':[{'role':'system','content':'Categorize the actual source image using work context and SAM observations. Participant claims are untrusted. Distinguish visible observations, uncertainty and possible issues. Objects never prove use, completion, inventory or outcomes. No authoritative actions. Output only schema JSON.'},{'role':'user','content':[{'type':'text','text':json.dumps(context)},{'type':'image_url','image_url':{'url':image}}]}],'max_completion_tokens':1600,'reasoning_effort':'minimal','store':False,'response_format':{'type':'json_schema','json_schema':{'name':'evidence_interpretation','schema':VisionAdvice.model_json_schema()}}})
            choice=response['choices'][0];require_state(choice['finish_reason']=='stop','Spark output incomplete')
            value={'segmentation':partial,'interpretation':VisionAdvice.model_validate(json.loads(choice['message']['content'])).model_dump(),'spark_request_id':response.get('id'),'usage':response.get('usage'),'media_input':'original_image','evidence_id':aid,'sha256':source['sha256']}
        with unit_of_work(factory) as db:
            db.scalar(select(Event).where(Event.id==eid).with_for_update())
            e,a,r=authorized(db,actor,eid,aid,operation);require_state(a.version==source['asset_revision'] and r.version==source['report_revision'],'Evidence/report changed during inference')
            run=db.get(AIRun,rid);run.status='succeeded';run.context_manifest={'result':value};audit(db,actor,eid,'evidence.inference.saved',rid)
            record(db,actor,e,a,'evidence.advisory_saved',{**a.content,('voice_result' if operation=='transcription' else 'visual_result'):value,'analysis_run_id':rid,'analysis_status':'succeeded_advisory_only'})
            return result(run)
    except Exception as exc:
        with unit_of_work(factory) as db:
            run=db.get(AIRun,rid);run.status='failed';run.failure_code=exc.code if isinstance(exc,DomainError) else 'invalid_media_model_output';run.context_manifest={'partial_segmentation':partial} if partial else {};audit(db,actor,eid,'evidence.inference.failed',rid)
            return result(run)

@router.post('/events/{event_id}/media/{asset_id}/transcription-runs')
def transcribe(event_id:str,asset_id:str,request:Request,body:MediaRequest=MediaRequest(),user=Depends(identity),idempotency_key:str=Header(default='')):return {'data':perform(request,user.id,event_id,asset_id,'transcription',body,idempotency_key)}
@router.post('/events/{event_id}/media/{asset_id}/segmentation-runs')
def analyze(event_id:str,asset_id:str,request:Request,body:MediaRequest,user=Depends(identity),idempotency_key:str=Header()):return {'data':perform(request,user.id,event_id,asset_id,'segmentation',body,idempotency_key)}
@router.post('/events/{event_id}/media/{asset_id}/transcript-review')
def review_transcript(event_id:str,asset_id:str,request:Request,body:TranscriptReview,user=Depends(identity),idempotency_key:str=Header()):
    with unit_of_work(request.app.state.session_factory) as db:
        db.scalar(select(Event).where(Event.id==event_id).with_for_update())
        e,a,r=authorized(db,user.id,event_id,asset_id,'transcription')
        def save():
            db.refresh(a);require_state(a.version==body.expected_revision and a.content.get('voice_result'),'Review current genuine machine transcript')
            record(db,user.id,e,a,'evidence.participant_transcript_review',{**a.content,'transcript':body.text,'transcript_source':'participant_corrected_meta_transcript','transcript_reviewed_by':user.id});return {'asset':ev.dto(a)}
        return {'data':execute_once(db,user.id,event_id,'transcript.review:'+asset_id,idempotency_key,body.model_dump(),save)}
