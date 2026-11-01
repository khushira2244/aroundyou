from app.events.models import ContextRevision
from app.events.creation_schemas import CreationForm

def event_dto(event,form=None):
    form=form or event.draft_form or {}
    f=CreationForm.model_validate(form)
    dates=(__import__('datetime').date.fromisoformat(f.endDate)-__import__('datetime').date.fromisoformat(f.startDate)).days+1 if f.startDate and f.endDate else 1
    return {'id':event.id,'title':f.title or event.title,'category':f.category or event.category,'filter_group':f.category or event.category,'label':'Event','demo':False,'lifecycle':event.lifecycle,'purpose':f.purpose,'goal':f.goal,'format':f.format,'location':{'label':'Online event' if f.format=='online' else ', '.join(x for x in [f.venue,f.area,f.city,f.state,f.country] if x),'confidence':'organizer_entered_unverified','coordinates':f.coordinates.model_dump() if f.coordinates else None,'source_id':f.locationSource,'precise_meeting_point':None},'context_id':event.active_context_revision_id,'schedule':{'anchor_date':f.startDate or None,'end_date':f.endDate or None,'start_time':f.startTime,'end_time':f.endTime,'timezone':f.timezone,'relative_days':list(range(1,min(dates,3660)+1)),'status':'organizer_selected' if f.startDate else 'unanchored'}}

def context_dto(session,event):
    source=session.get(ContextRevision,event.active_context_revision_id) if event.active_context_revision_id else None
    from sqlalchemy import select
    history=[{'text':x.original_text,'source':x.source_kind,'version':x.sequence,'snapshot':x.snapshot} for x in session.scalars(select(ContextRevision).where(ContextRevision.event_id==event.id).order_by(ContextRevision.sequence))]
    from app.ai.models import AIProposal,AIRun
    from app.planning.dto import proposal_dto
    pending=list(session.scalars(select(AIProposal).join(AIRun,AIProposal.run_id==AIRun.id).where(AIProposal.event_id==event.id,AIProposal.kind=='understanding',AIProposal.status=='pending').order_by(AIRun.created_at.desc()).limit(10)))
    proposals=[{**proposal_dto(p,event,source.sequence if source else 0),'interpretation':p.payload,'source_explanation':'Source-linked proposal; organizer review required'} for p in pending]
    return {'pending_interpretations':proposals,'clarification_rounds' :source.snapshot.get('clarification_rounds',[]) if source else [],'input_history':history,'id':source.id if source else '', 'original_text':source.original_text if source else '', 'version':source.sequence if source else 0,'execution_intent':{'text':source.original_text if source else '', 'source':source.source_kind if source else 'written','version':source.sequence if source else 0,'independently_verified':False},'approved_interpretation':event.interpretation}

def creation_dto(session,event):
    context=context_dto(session,event)
    return {'event':event_dto(event),'context':context,'runtime':{'revision':event.version,'lifecycle':event.lifecycle,'publication':'published' if event.current_publication_id else 'unpublished','wizard_step':event.draft_step,'draft':{'creation_details':event.draft_form},'context_version':context['version']},'sample_intent':''}
