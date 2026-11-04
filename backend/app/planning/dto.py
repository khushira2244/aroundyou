from sqlalchemy import select
from app.events.dto import event_dto,context_dto
from app.planning.draft_models import PlanningDraft
from app.ai.models import AIProposal,AIRun

def proposal_dto(p,event,context_version=0):
    from app.planning.service import versions
    status=p.status
    if status=='pending':
        # Callers provide loaded draft versions in the planning projection below.
        if p.source_versions.get('event_version')!=event.version or p.source_versions.get('context_revision')!=event.active_context_revision_id:status='stale'
    return {'stage_id':p.payload.get('stage_id'),'id':p.id,'kind':p.kind,'status':status,'context_version':context_version,'base_stage_revision':p.source_versions.get('stage_revision',0),'base_work_revision':p.source_versions.get('work_revision',0),'message':p.payload.get('message','Review exact source-linked proposal'),'changes':p.payload.get('changes',[]),'violations':p.payload.get('violations',[]),'impact':p.payload.get('impact'),'preview_plan':p.payload.get('plan'),'advisory_only':p.payload.get('advisory_only',False),'digest':p.digest,'source_versions':p.source_versions,'provenance':p.provenance}

def progress(draft):
    body=draft.content
    stages={s['id']:{**s,'capacity':{'confirmed_people':0,'feasibility':'unverified'},'responsible_role_requirement_id':''} for s in body['stages']}
    resources={r['id']:{**r,'availability':'not_verified'} for r in body['resources']}
    roles={r['id']:{**r,'commitment':{'effort_person_hours':r['effort_person_hours'],'schedule_intervals':r['schedule_intervals']},'delegated_permissions':[],'status':'planned_requirement'} for r in body['roles']}
    from app.planning.service import reviewed_stages
    return {'work_confirmed_stage_ids':reviewed_stages(draft,'work'),'actor_confirmed_stage_ids':reviewed_stages(draft,'actors'),'stale_work_ids':body.get('stale_work_ids',[]),'context_version':0,'stages':stages,'work':{w['id']:w for w in body['work']},'resources':resources,'roles':roles,'stage_revision':draft.stage_revision,'work_revision':draft.work_revision,'stage_confirmed':draft.stage_confirmed,'work_confirmed':draft.work_confirmed,'actors_confirmed':draft.actors_confirmed,'derived_from':draft.derived_from,'latest_stage_proposal_id':None,'latest_work_proposal_id':None,'chat_approved':False}

def planning_dto(session,event,draft=None):
    draft=draft or session.scalar(select(PlanningDraft).where(PlanningDraft.event_id==event.id))
    if draft is None:
        from app.api.errors import DomainError
        raise DomainError('not_found','Open a planning draft first',404)
    calendar_warnings=[]
    form=event.draft_form
    if form.get('startDate') and form.get('endDate'):
        from datetime import date
        span=(date.fromisoformat(form['endDate'])-date.fromisoformat(form['startDate'])).days+1
        outside=[s['id'] for s in draft.content['stages'] if s['relative_end']>span]
        if outside:calendar_warnings=['Stage calendar extends beyond the event brief end date: '+', '.join(outside)+'. Review the event dates explicitly; they have not been changed.']
    ctx=context_dto(session,event);p=progress(draft);p['context_version']=ctx['version']
    proposals=list(session.scalars(select(AIProposal).where(AIProposal.event_id==event.id,AIProposal.kind.in_(['stages','work','actors','planning_chat','manual_plan'])).order_by(AIProposal.created_at,AIProposal.id)))
    for x in proposals:
        if x.kind=='stages':p['latest_stage_proposal_id']=x.id
        if x.kind=='work':p['latest_work_proposal_id']=x.id
    return {'event':{**event_dto(event),'creation_details':event.draft_form},'context':ctx,'planning':p,'active_plan_id':event.active_plan_id,'publication':'published' if event.current_publication_id else 'unpublished','proposals':[{**proposal_dto(x,event,ctx['version']),'question':session.get(AIRun,x.run_id).request_message if x.run_id else None} for x in proposals],'work_groups':draft.content['groups'],'lead_requirements':[],'warnings':calendar_warnings+(['Work timing requires review: '+', '.join(draft.content['stale_work_ids'])] if draft.content.get('stale_work_ids') else [])+['Scheduling validates precedence/windows only; skills, participant capacity and physical resource availability remain unverified'],'revision':event.version,'draft_version':draft.version}
