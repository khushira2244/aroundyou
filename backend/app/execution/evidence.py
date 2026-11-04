from sqlalchemy import select
from app.execution.models import EvidenceAsset,WorkReport
from app.execution.service import *
from app.execution.storage import inspect_bytes
ALLOWED={'image':{'image/jpeg','image/png','image/webp'},'audio':{'audio/mpeg','audio/wav','audio/webm','audio/ogg'},'video':{'video/mp4','video/webm'},'document':{'application/pdf','text/plain'},'text':{'text/plain'}}
def create(db,actor,e,b):
    r=get_report(db,actor,e,b.report_id);a,t=assignment(db,actor,e,r.work_id)
    require_state(r.account_id==actor and r.terms_id==t.id and r.version==b.report_revision and r.content['review_status']=='draft','Attach to exact own current draft')
    require_state(b.mime in ALLOWED[b.kind] and len(r.content['evidence_ids'])<20,'Unsupported media type or attachment limit')
    require_state(b.size<= (52428800 if b.kind=='video' else 10485760),'Media exceeds type size limit')
    data={'kind':b.kind,'name':b.name,'mime':b.mime,'size':b.size,'status':'awaiting_upload','sha256':None,'storage_key':None,'analysis_status':'provider_unavailable','verification':'Not verified','transcript':None}
    if b.kind=='text':
        require_state(bool(b.text),'Original text statement required');data.update(text=b.text,size=len(b.text.encode()),status='accepted_for_review',sha256=__import__('hashlib').sha256(b.text.encode()).hexdigest())
    asset=EvidenceAsset(id=uid(),event_id=e.id,report_id=r.id,account_id=actor,content={});db.add(asset);db.flush();record(db,actor,e,asset,'evidence.create',data)
    record(db,actor,e,r,'report.attach',{**r.content,'evidence_ids':r.content['evidence_ids']+[asset.id]})
    return {'asset':dto(asset),'report_revision':r.version}
def get(db,actor,e,aid):
    a=db.get(EvidenceAsset,aid)
    if not a or a.event_id!=e.id:missing()
    try:get_report(db,actor,e,a.report_id)
    except DomainError:
        # Explicit issue attachment authorizes the organizer to read that exact original,
        # not the participant's unsubmitted report or its other draft attachments.
        from app.execution.models import WorkIssue
        if not owner(db,actor,e) or not db.scalar(select(WorkIssue.id).where(WorkIssue.event_id==e.id,WorkIssue.content['evidence_ids'].contains([aid]))):raise
    return a
def dto(a):return {'id':a.id,'report_id':a.report_id,'revision':a.version,**{k:v for k,v in a.content.items() if k!='storage_key'},'last_modified':0,'storage':'private_backend','media_reference':'/v1/events/'+a.event_id+'/evidence/'+a.id+'/content'}
def upload(db,actor,e,aid,data,storage):
    a=get(db,actor,e,aid);r=get_report(db,actor,e,a.report_id);_,t=assignment(db,actor,e,r.work_id)
    require_state(a.account_id==actor and r.terms_id==t.id and r.content['review_status']=='draft' and a.content['status']=='awaiting_upload','Upload only once to own authorized draft')
    if storage is None:raise DomainError('storage_unavailable','Private evidence object storage is not configured',503)
    require_state(len(data)==a.content['size'],'Uploaded byte count differs from authorized size')
    sha=inspect_bytes(a.content['kind'],a.content['mime'],data);key=uid().replace('-','')
    try:storage.put(key,data)
    except OSError:raise DomainError('storage_unavailable','Private object could not be durably stored',503) from None
    record(db,actor,e,a,'evidence.upload',{**a.content,'storage_key':key,'sha256':sha,'status':'pending_inspection','uploaded_at':now().isoformat()})
    return {'asset':dto(a)}
def inspect(db,actor,e,aid,b):
    a=get(db,actor,e,aid);r=get_report(db,actor,e,a.report_id);w=work(db,e,actor,r.work_id)
    require_state(a.version==b.expected_revision,'Inspect exact evidence revision')
    if b.decision=='retract':
        if a.account_id!=actor and not reviewer(db,actor,e,w):missing()
    elif not reviewer(db,actor,e,w) or r.account_id==actor:missing()
    data={**a.content,'inspection_note':b.note}
    if b.decision=='review_transcript':
        require_state(a.content['kind']=='audio' and a.content['status']=='accepted_for_review' and b.transcript is not None,'Manual reviewed transcript requires accepted original audio')
        data.update(transcript=b.transcript,transcript_reviewed_by=actor,transcript_source='human_supplied_reviewed_not_machine_transcription')
    else:
        require_state(b.decision=='retract' or a.content['status'] in ('pending_inspection','accepted_for_review','quarantined'),'Original upload required before inspection')
        data['status']={'accept_for_review':'accepted_for_review','quarantine':'quarantined','retract':'retracted'}[b.decision]
    record(db,actor,e,a,'evidence.inspect',data)
    if b.decision in ('retract','quarantine') or r.content['review_status']=='accepted':
        row=execution(db,e,r.work_id)
        if row and row.content.get('verified_report_id')==r.id:
            record(db,actor,e,row,'work.evidence_invalidated',{**row.content,'status':'reopened','verified_percent':0,'verified_at':None},'attempted','inconclusive',b.note)
        if r.content['review_status']=='accepted':record(db,actor,e,r,'report.evidence_invalidated',{**r.content,'review_status':'needs_correction','review_notes':r.content['review_notes']+[b.note]})
    if b.decision=='retract':
        record(db,actor,e,r,'report.detach_retracted',{**r.content,'evidence_ids':[x for x in r.content['evidence_ids'] if x!=a.id],'review_status':'draft' if r.content['review_status']=='draft' else 'needs_correction','review_notes':r.content['review_notes']+[b.note]})
    return {'asset':dto(a)}
