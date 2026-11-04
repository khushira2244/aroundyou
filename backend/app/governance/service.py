from copy import deepcopy
from app.execution.storage import inspect_bytes
from sqlalchemy import select
from app.governance.models import GovernanceTicket
from app.ai.models import AIProposal
from app.shared.types import uid, now
from app.shared.audit import audit
from app.api.errors import DomainError,missing

def state(session,event):
    ticket=session.scalar(select(GovernanceTicket).where(GovernanceTicket.event_id==event.id))
    from app.ai.models import AIRun
    from app.ai.context_builder import assessment_fingerprint
    from app.planning.service import versions
    proposals=list(session.scalars(select(AIProposal).join(AIRun,AIProposal.run_id==AIRun.id).where(AIProposal.event_id==event.id,AIProposal.kind=='governance').order_by(AIRun.created_at.desc())))
    fingerprint=assessment_fingerprint(session,event)
    def current(p):
        run=session.get(AIRun,p.run_id)
        if not run or run.context_manifest.get('authoritative_current',{}).get('governance_fingerprint')!=fingerprint:return False
        from app.ai.context_builder import MuseSparkContextBuilder
        try:MuseSparkContextBuilder().validate_memories(session,run.requester_id,event.id,run.context_manifest)
        except DomainError:return False
        return True
    proposal=next((p for p in proposals if p.status=='approved' and current(p)),None)
    reviewed_payload=proposal.payload if proposal else {}
    if proposal and proposal.review_decision_id:
        from app.shared.models import ReviewDecision
        review=session.get(ReviewDecision,proposal.review_decision_id)
        if review and review.subject_digest==proposal.digest and review.reviewed_content:
            reviewed_payload=review.reviewed_content.get('governance',reviewed_payload)
    pending=[{'id':p.id,'digest':p.digest,'status':'pending' if current(p) and p.source_versions==versions(event) else 'stale','items':p.payload.get('items',[]),'provenance':p.provenance} for p in proposals if p.status=='pending']
    ticket_data=None
    if ticket:
        ticket_data={'id':ticket.id,**ticket.configuration,'status':ticket.configuration.get('status','open'),'version':ticket.version,'external_submission':False,'permission_status':'not_verified'}
        ticket_data['documents']=[
            {k:v for k,v in doc.items() if k not in ('storage_key','sha256')}
            for doc in ticket_data['documents']
        ]
    return {'guidance':{'status':'human_reviewed_advice' if proposal else 'stale_reassessment_required' if any(p.status=='approved' for p in proposals) else 'not_assessed','permission_status':'not_verified','mandatory_gate':False},'advisory_id':proposal.id if proposal else None,'items':reviewed_payload.get('items',[]),'proposals':pending,'ticket':ticket_data,'revision':event.version}


def start(session,actor,event,documents=(), originals=(), storage=None):
    ticket=session.scalar(select(GovernanceTicket).where(GovernanceTicket.event_id==event.id))
    if not ticket:
        assessment=state(session,event)
        if assessment['guidance']['status']!='human_reviewed_advice':
            raise DomainError('governance_review_required','Review the current governance advisory before creating a ticket.',422)
        requirements=assessment['items']
        allowed={item['id'] for item in requirements if item.get('classification')!='not_applicable'}
        if any(doc.document_type not in allowed for doc in documents):
            raise DomainError('invalid_document_requirement','Select a current governance requirement.',422)
        references=[document_record(doc) for doc in documents]
        for record, original in zip(references, originals, strict=bool(originals)):
            if storage is None:
                raise DomainError('storage_unavailable','Private document storage is unavailable.',503)
            checksum=inspect_bytes('document' if record['mime']=='application/pdf' else 'image',record['mime'],original)
            key=uid().replace('-','')
            try:
                storage.put(key,original)
            except OSError:
                raise DomainError('storage_unavailable','The original could not be stored.',503) from None
            record.update(storage_key=key,sha256=checksum,storage='private_backend',status='uploaded_not_verified')
        ticket=GovernanceTicket(id=uid(),event_id=event.id,configuration={
            'documents':references,'requirements':requirements,'advisory_id':assessment['advisory_id'],
            'confirmed_by':actor,'confirmed_at':now().isoformat(),'status':'open',
            'email_updates':False,'remind_documents':False,'history':[],
        })
        session.add(ticket)
        session.flush()
        event.version+=1
        audit(session,actor,event.id,'governance.ticket.create',ticket.id)
    return {'ticket':state(session,event)['ticket']}

def document_record(body):
    return {'id':uid(),'name':body.name,'type':body.document_type,'size':body.size,
            'mime':body.mime,'reference':body.document_reference,
            'status':'reference_only_not_verified','storage':'reference_only'}

def update(session,actor,event,ticket_id,kind,body):
    ticket=session.get(GovernanceTicket,ticket_id)
    if not ticket or ticket.event_id!=event.id:missing()
    data=deepcopy(ticket.configuration)
    if kind=='document':
        if len(data['documents'])>=100:raise DomainError('limit_exceeded','Document limit reached',422)
        # Reference only: original byte upload/evidence verification belongs to Group 4.
        item=document_record(body)
        data['documents'].append(item)
    else:data['email_updates']=body.email_updates;data['remind_documents']=body.remind_documents
    ticket.configuration=data;ticket.version+=1;event.version+=1;audit(session,actor,event.id,'governance.'+kind,ticket.id)
    return {'document':item} if kind=='document' else {'saved':True,'delivery_state':'preferences_only_no_sender'}


def edit(session,actor,event,ticket_id,status,note,responsible_party=''):
    ticket=session.get(GovernanceTicket,ticket_id)
    if not ticket or ticket.event_id!=event.id:missing()
    from app.shared.types import now
    data=deepcopy(ticket.configuration)
    history=data.get('history',[])
    if len(history)>=100:raise DomainError('limit_exceeded','Ticket history limit reached',422)
    data['history']=[*history,{'from':data.get('status','open'),'to':status,'note':note,'actor_id':actor,'at':now().isoformat(),'external_approval':False}]
    data['status']=status;data['responsible_party']=responsible_party;data['history'][-1]['responsible_party']=responsible_party;ticket.configuration=data;ticket.version+=1;event.version+=1
    audit(session,actor,event.id,'governance.ticket.edit',ticket.id,status=status)
    return {'ticket':state(session,event)['ticket']}


