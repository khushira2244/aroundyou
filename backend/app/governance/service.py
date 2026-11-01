from copy import deepcopy
from sqlalchemy import select
from app.governance.models import GovernanceTicket
from app.ai.models import AIProposal
from app.shared.types import uid
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
    pending=[{'id':p.id,'digest':p.digest,'status':'pending' if current(p) and p.source_versions==versions(event) else 'stale','items':p.payload.get('items',[]),'provenance':p.provenance} for p in proposals if p.status=='pending']
    ticket_data=None
    if ticket:
        ticket_data={'id':ticket.id,**ticket.configuration,'status':ticket.configuration.get('status','open'),'version':ticket.version,'external_submission':False,'permission_status':'not_verified'}
    return {'guidance':{'status':'human_reviewed_advice' if proposal else 'stale_reassessment_required' if any(p.status=='approved' for p in proposals) else 'not_assessed','permission_status':'not_verified','mandatory_gate':False},'items':proposal.payload.get('items',[]) if proposal else [],'proposals':pending,'ticket':ticket_data,'revision':event.version}


def start(session,actor,event):
    ticket=session.scalar(select(GovernanceTicket).where(GovernanceTicket.event_id==event.id))
    if not ticket:
        ticket=GovernanceTicket(id=uid(),event_id=event.id,configuration={'documents':[],'email_updates':False,'remind_documents':False,'status':'open','history':[]});session.add(ticket);session.flush();event.version+=1;audit(session,actor,event.id,'governance.ticket.create',ticket.id)
    return {'ticket':state(session,event)['ticket']}

def update(session,actor,event,ticket_id,kind,body):
    ticket=session.get(GovernanceTicket,ticket_id)
    if not ticket or ticket.event_id!=event.id:missing()
    data=deepcopy(ticket.configuration)
    if kind=='document':
        if len(data['documents'])>=100:raise DomainError('limit_exceeded','Document limit reached',422)
        # Reference only: original byte upload/evidence verification belongs to Group 4.
        item={'id':uid(),'name':body.name,'type':body.document_type,'size':body.size,'mime':body.mime,'reference':body.document_reference,'status':'reference_only_not_verified','storage':'reference_only'}
        data['documents'].append(item)
    else:data['email_updates']=body.email_updates;data['remind_documents']=body.remind_documents
    ticket.configuration=data;ticket.version+=1;event.version+=1;audit(session,actor,event.id,'governance.'+kind,ticket.id)
    return {'document':item} if kind=='document' else {'saved':True,'delivery_state':'preferences_only_no_sender'}


def edit(session,actor,event,ticket_id,status,note):
    ticket=session.get(GovernanceTicket,ticket_id)
    if not ticket or ticket.event_id!=event.id:missing()
    from app.shared.types import now
    data=deepcopy(ticket.configuration)
    history=data.get('history',[])
    if len(history)>=100:raise DomainError('limit_exceeded','Ticket history limit reached',422)
    data['history']=[*history,{'from':data.get('status','open'),'to':status,'note':note,'actor_id':actor,'at':now().isoformat(),'external_approval':False}]
    data['status']=status;ticket.configuration=data;ticket.version+=1;event.version+=1
    audit(session,actor,event.id,'governance.ticket.edit',ticket.id,status=status)
    return {'ticket':state(session,event)['ticket']}
