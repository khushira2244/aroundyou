from copy import deepcopy
from sqlalchemy import select
from app.publication.models import SetupRevision,Finalization,Publication,PublishedRole
from app.publication.schemas import Location,Communications,Participation,ParticipantConfiguration,ResourceClaims,SponsorReview,Invite,Partner,PublishPreferences
from app.planning.service import draft_for
from app.planning.dto import progress
from app.planning.models import PlanVersion
from app.events.dto import event_dto
from app.access.authorization import allowed
from app.shared.types import uid,digest
from app.shared.audit import audit
from app.api.errors import DomainError,missing

TABS=['Overview','Stages','Volunteer Roles','Updates','Photos','Sponsors','Discussions','Impact']

def default_configuration(event,plan):
    return {'location':Location().model_dump(),'availability_claims':{},'resource_reviewed':False,'invites':[],'invites_reviewed':False,'partner_drafts':[],'sponsors_reviewed':False,'public_offer_ids':[],'participation':Participation().model_dump(),'participation_configured':False,'tags':ParticipantConfiguration().model_dump(),'tags_reviewed':False,'communications':Communications().model_dump(),'publish_mode':'now','scheduled_intent':None,'scope_exclusions':[],'source_plan_id':plan.id if plan else ''}

def setup_for(session,event):
    row=session.get(SetupRevision,event.current_setup_id) if event.current_setup_id else None
    if not row or row.event_id!=event.id:raise DomainError('not_found','Open event setup first',404)
    if row.source_plan_id!=event.active_plan_id:raise DomainError('stale_setup','Setup references a previous plan; reopen for review')
    return row

def save_revision(session,actor,event,configuration):
    previous=session.get(SetupRevision,event.current_setup_id) if event.current_setup_id else None
    row=SetupRevision(id=uid(),event_id=event.id,sequence=previous.sequence+1 if previous else 1,source_plan_id=event.active_plan_id,configuration=configuration,digest=digest(configuration),created_by=actor)
    session.add(row);session.flush();event.current_setup_id=row.id;event.current_finalization_id=None;event.version+=1
    event.lifecycle='planned';audit(session,actor,event.id,'setup.revise',row.id)
    return row

def open_setup(session,actor,event):
    draft=draft_for(session,event)
    if not draft.actors_confirmed or not event.active_plan_id:raise DomainError('invalid_state','Confirm coherent actor/work/stage plan before setup')
    if event.current_setup_id:
        old=session.get(SetupRevision,event.current_setup_id)
        if old.source_plan_id==event.active_plan_id:return old
    return save_revision(session,actor,event,default_configuration(event,session.get(PlanVersion,event.active_plan_id) if event.active_plan_id else None))

def save_section(session,actor,event,section,data):
    old=setup_for(session,event);c=deepcopy(old.configuration)
    if section=='location':c['location']=Location.model_validate(data).model_dump()
    elif section=='communications':c['communications']=Communications.model_validate(data).model_dump()
    elif section=='participation':c['participation']=Participation.model_validate(data).model_dump();c['participation_configured']=True
    elif section=='resources':
        claims=ResourceClaims.model_validate(data).claims
        draft=draft_for(session,event);ids={r['id'] for r in draft.content['resources']}
        if not set(claims)<=ids:raise DomainError('foreign_resource','Resource report is outside this plan',422)
        c['availability_claims']={k:{'quantity':v,'status':'reported_not_verified'} for k,v in claims.items()};c['resource_reviewed']=True
    elif section=='invites':
        if data:raise DomainError('invalid_fields','Use invitation draft commands',422)
        c['invites_reviewed']=True
    elif section=='sponsors':
        value=SponsorReview.model_validate(data)
        if value.public_offer_ids:raise DomainError('unavailable','Real sponsorship offers arrive in Group 3',503)
        c['public_offer_ids']=[];c['sponsors_reviewed']=True
    else:raise DomainError('invalid_section','Unknown setup section',422)
    row=save_revision(session,actor,event,c)
    return {'saved':True,'setup_revision':row.sequence}

def save_tags(session,actor,event,value):
    c=deepcopy(setup_for(session,event).configuration);c['tags']=ParticipantConfiguration.model_validate(value).model_dump();c['tags_reviewed']=True
    row=save_revision(session,actor,event,c)
    return {'saved':True,'individual_data_public':False,'configuration_version':row.sequence}

def add_entry(session,actor,event,kind,value):
    c=deepcopy(setup_for(session,event).configuration);item=(Invite if kind=='invite' else Partner).model_validate(value).model_dump();item['id']=uid()
    if kind=='invite':
        roles={r['id'] for r in draft_for(session,event).content['roles']}
        if item['role_id'] and item['role_id'] not in roles:raise DomainError('foreign_role','Invitation role not in current plan',422)
        item.update(status='draft',message_sent=False)
    else:item['status']='in_discussion'
    field='invites' if kind=='invite' else 'partner_drafts'
    if len(c[field])>=200:raise DomainError('limit_exceeded','Draft entry limit reached',422)
    c[field].append(item);save_revision(session,actor,event,c)
    return {kind:item}

def remove_invite(session,actor,event,invite_id):
    c=deepcopy(setup_for(session,event).configuration)
    if not any(x['id']==invite_id for x in c['invites']):missing()
    c['invites']=[x for x in c['invites'] if x['id']!=invite_id];row=save_revision(session,actor,event,c)
    return {'removed':True,'setup_revision':row.sequence}

def preferences(session,actor,event,body):
    value=PublishPreferences.model_validate(body);c=deepcopy(setup_for(session,event).configuration)
    c['publish_mode']=value.mode;c['scheduled_intent']={'date':value.date,'time':value.time,'status':'intent_only_no_scheduler'} if value.mode=='scheduled' else None
    save_revision(session,actor,event,c)
    return {'saved':True,'scheduler_connected':False,'scheduled_intent':c['scheduled_intent']}

def setup_dto(session,event):
    draft=draft_for(session,event);setup=setup_for(session,event);c={**setup.configuration,'revision':setup.sequence}
    from app.resources.service import project_requirements
    resources=[{**r,'delivered':r['verified'],'reported_available':c['availability_claims'].get(r['id'],{}).get('quantity'),'status':'verified_receipts_only'} for r in project_requirements(session,event,draft.content['resources'])]
    final=session.get(Finalization,event.current_finalization_id) if event.current_finalization_id else None
    checks=[{'id':'plan','label':'Coherent plan confirmed','done':bool(draft.stage_confirmed and draft.work_confirmed and draft.actors_confirmed),'required':True},{'id':'participation','label':'Participation and visibility reviewed','done':c['participation_configured'],'required':True},{'id':'resources','label':'Resource availability reviewed','done':c['resource_reviewed'],'required':False},{'id':'invites','label':'Invitation drafts reviewed (not sent)','done':c['invites_reviewed'],'required':False},{'id':'sponsors','label':'Sponsor discussions reviewed','done':c['sponsors_reviewed'],'required':False},{'id':'tags','label':'Optional tags reviewed','done':c['tags_reviewed'],'required':False}]
    planning_view=progress(draft)
    from app.events.models import ContextRevision
    context=session.get(ContextRevision,event.active_context_revision_id)
    planning_view['context_version']=context.sequence if context else 0
    return {'event':{**event_dto(event),'creation_details':event.draft_form},'planning':planning_view,'configuration':c,'resources':resources,'sponsors':[],'zones':draft.content['zones'],'checklist':checks,'lifecycle':event.lifecycle,'publication':'published' if event.current_publication_id else 'unpublished','plan_id':event.active_plan_id,'finalization':{'id':final.id,'setup_revision':setup.sequence,'plan_id':final.plan_id,'approved_by':final.approved_by} if final else None,'revision':event.version}

def finalize(session,actor,event,confirm_review,expected_setup_version,expected_plan_id):
    setup=setup_for(session,event);draft=draft_for(session,event)
    if not confirm_review or setup.sequence!=expected_setup_version or event.active_plan_id!=expected_plan_id:raise DomainError('stale_configuration','Review exact setup and plan')
    if not draft.stage_confirmed or not draft.work_confirmed or not draft.actors_confirmed or not setup.configuration['participation_configured']:raise DomainError('incomplete_review','Confirm plan and review participation/visibility',422)
    final=Finalization(id=uid(),event_id=event.id,setup_revision_id=setup.id,plan_id=event.active_plan_id,reviewed_digest=digest({'setup':setup.digest,'plan':event.active_plan_id,'brief':event.draft_form}),approved_by=actor)
    session.add(final);session.flush();event.current_finalization_id=final.id;event.lifecycle='finalized';event.version+=1
    audit(session,actor,event.id,'event.finalize',final.id)
    return {'lifecycle':'finalized','publication':'unpublished','finalization_id':final.id}

def publish(session,actor,event,finalization_id):
    setup=setup_for(session,event)
    if event.lifecycle!='finalized' or not finalization_id or event.current_finalization_id!=finalization_id:raise DomainError('invalid_state','Finalize exact current configuration before publishing')
    final=session.get(Finalization,finalization_id)
    if final.setup_revision_id!=setup.id or final.plan_id!=event.active_plan_id:raise DomainError('stale_configuration','Finalization is stale')
    if setup.configuration['publish_mode']=='scheduled':raise DomainError('scheduler_unavailable','Scheduled intent is saved, but no publishing scheduler is connected',503)
    previous=session.get(Publication,event.current_publication_id) if event.current_publication_id else None
    plan=session.get(PlanVersion,event.active_plan_id)
    snapshot={'event':event_dto(event),'plan':plan.content,'configuration':setup.configuration}
    release=Publication(id=uid(),event_id=event.id,sequence=previous.sequence+1 if previous else 1,finalization_id=final.id,plan_id=plan.id,setup_revision_id=setup.id,snapshot=snapshot,digest=digest(snapshot),visibility=setup.configuration['participation']['visibility'],approved_by=actor)
    session.add(release);session.flush()
    for role in plan.content.get('roles',[]):session.add(PublishedRole(event_id=event.id,publication_id=release.id,plan_id=plan.id,requirement_id=role['id']))
    event.current_publication_id=release.id;event.lifecycle='published';event.version+=1
    audit(session,actor,event.id,'event.publish',release.id)
    return {'publication_id':release.id,'publication':'published','visibility':release.visibility,'plan_id':plan.id}

def profile(session,event,user_id=None,preview=False):
    if event.lifecycle=='deleted':missing()
    owner=bool(user_id and allowed(session,user_id,event.id,'event:read') and allowed(session,user_id,event.id,'plan:write'))
    if preview:
        if not owner:missing()
        from app.planning.draft_models import PlanningDraft
        from app.planning.schemas import PlanContent
        draft=session.scalar(select(PlanningDraft).where(PlanningDraft.event_id==event.id));configuration=setup_for(session,event).configuration if event.current_setup_id else default_configuration(event,session.get(PlanVersion,event.active_plan_id) if event.active_plan_id else None)
        snap={'event':event_dto(event),'plan':draft.content if draft else PlanContent().model_dump(),'configuration':configuration};plan_id=event.active_plan_id;visibility=configuration['participation']['visibility'];publication='preview'
    else:
        release=session.get(Publication,event.current_publication_id) if event.current_publication_id else None
        if not release:missing()
        if release.visibility!='public' and not (user_id and allowed(session,user_id,event.id,'event:read')):missing()
        snap=release.snapshot;plan_id=release.plan_id;visibility=release.visibility;publication='published'
    c=snap['configuration'];body=snap['plan'];communications=deepcopy(c['communications'])
    if not communications.pop('public_contact',False):
        communications['contact_email']='';communications['contact_phone']='';communications['updates_channel']=''
    roles=[]
    if c['participation']['show_open_roles']:
        for r in body['roles']:roles.append({**r,'commitment':{'effort_person_hours':r['effort_person_hours'],'schedule_intervals':r['schedule_intervals']},'delegated_permissions':[],'status':'planned_requirement','positions':r['proposed_headcount'],'accepted_positions':0,'open_positions':r['proposed_headcount'],'published_plan_id':plan_id,'recruitment_status':'planned'})
    from app.access.models import User
    creator=session.get(User,event.creator_id)
    public_event={**snap['event'],'context_id':None,'lifecycle':'published' if not preview else event.lifecycle}
    result={'event':public_event,'tabs':TABS,'publication':publication,'visibility':visibility,'plan_id':plan_id,'viewer':{'is_organizer':owner,'can_edit_content':False,'can_discuss':False,'following':False},'organizer':{'label':creator.display_name if creator else 'Event organizer','verified':False},'scope':{'work_scope':snap['event']['goal'],'zones':[z['label'] for z in body['zones'] if z['in_scope']],'exclusions':c['scope_exclusions']},'stages':[{**s,'capacity':{'confirmed_people':0,'feasibility':'unverified'},'responsible_role_requirement_id':'','execution_status':'planned','work_count':sum(w['stage_id']==s['id'] for w in body['work'])} for s in body['stages']],'roles':roles,'updates':[],'photos':[],'sponsors':[],'discussions':[],'impact':{'verified_outputs':[],'reported_activity_count':0,'accepted_participants':0,'waste_collected_kg':None,'waste_handed_over_kg':None,'area_improved_hectares':None,'cleanup_zones_completed':None,'assessment_sections':None,'cleanup_complete':False},'communications':communications,'participation':c['participation'],'insights':{'enabled':c['tags']['collect_insights'],'status':'suppressed','reason':'No consented accepted participant records in this group','total_participants':0,'counts':{'requested':0,'approved':0,'accepted':0} if owner else None,'minimum_group_size':5,'breakdowns':[],'synthetic':False},'execution_notice':'Planning and publication are not verified execution, staffing or permission.'}

    from app.participation.projections import augment_profile
    from app.execution.coordination import participant
    result['viewer']['can_discuss']=bool(user_id and (owner or participant(session,user_id,event)))
    return augment_profile(session,event,result)
