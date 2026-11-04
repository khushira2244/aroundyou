"""Versioned selective alternatives; local edits never activate authoritative plans."""
from copy import deepcopy
from datetime import timedelta
from sqlalchemy import select,func,text
from pydantic import Field
from app.memory.schemas import StrictModel
from app.planning.schemas import Schedule,PlanContent
from app.planning.models import PlanVersion
from app.execution.models import CoordinationRecord,WorkExecution,WorkIssue
from app.execution.service import record
from app.participation.models import Assignment,AssignmentTerms,AssignmentConsent,Application
from app.participation.service import effective_assignment,contains,overlap,source
from app.publication.models import Publication,SetupRevision,Finalization,PublishedRole
from app.recovery.service import impact
from app.shared.types import uid,digest,now
from app.api.errors import DomainError,missing
from app.ai.context_builder import MuseSparkContextBuilder

class Alternative(StrictModel):
    issue_ids:list[str]=Field(min_length=1,max_length=30)
    expected_plan_id:str
    title:str=Field(min_length=1,max_length=200)
    rationale:str=Field(min_length=1,max_length=2000)
    schedules:dict[str,Schedule]=Field(default_factory=dict,max_length=50)
    patches:dict[str,dict]=Field(default_factory=dict,max_length=100)
    assumptions:list[str]=Field(default_factory=list,max_length=30)
    risks:list[str]=Field(default_factory=list,max_length=30)
    hold:bool=False
class Decision(StrictModel):
    expected_revision:int
    proposal_digest:str
    decision:str=Field(pattern='^(approve|reject|clarify|hold)$')
    rationale:str=Field(min_length=1,max_length=2000)
class Consent(StrictModel):
    terms_key:str
    decision:str=Field(pattern='^(accept|decline)$')
class Activate(StrictModel):
    expected_revision:int
    proposal_digest:str

def get(db,e,rid):
    row=db.get(CoordinationRecord,rid)
    if not row or row.event_id!=e.id or row.kind!='recovery':missing()
    return row

def fingerprint(db,e,issue_ids):
    issues=[db.get(WorkIssue,i) for i in issue_ids]
    if any(not x or x.event_id!=e.id for x in issues):missing()
    return digest({'plan':e.active_plan_id,'context':e.active_context_revision_id,'issues':[(i.id,i.version,i.content) for i in issues],
      'work':[(x.id,x.version) for x in db.scalars(select(WorkExecution).where(WorkExecution.event_id==e.id))],
      'assignments':[(x.id,x.version,x.current_terms_id,x.status) for x in db.scalars(select(Assignment).where(Assignment.event_id==e.id))],
      'resources':resource_fingerprint(db,e)})

def resource_fingerprint(db,e):
    from app.resources.models import ResourceTransaction,ResourceReservation
    from app.execution.models import ResourceOperation
    return {'receipts':[(r.id,str(r.quantity)) for r in db.scalars(select(ResourceTransaction).where(ResourceTransaction.event_id==e.id))],
      'reservations':[(r.id,r.status,str(r.quantity)) for r in db.scalars(select(ResourceReservation).where(ResourceReservation.event_id==e.id))],
      'usage':[r.id for r in db.scalars(select(ResourceOperation).where(ResourceOperation.event_id==e.id))]}

def validate(db,actor,e,d):
    errors=[];conditions=[]
    if e.active_plan_id!=d['base_plan_id'] or fingerprint(db,e,d['issue_ids'])!=d['fingerprint']:errors.append('stale_operational_sources')
    try:MuseSparkContextBuilder().validate_memories(db,actor,e.id,d['memory_context'])
    except DomainError:errors.append('stale_memory')
    if d['hold']:conditions.append('organizer_hold')
    if d['assumptions']:conditions.append('unverified_assumptions')
    content=d['plan'];works={w['id']:w for w in content['work']}
    for node in d.get('changed_nodes',[]):
        if not node.startswith('actor:'):continue
        role=next(r for r in content['roles'] if r['id']==node.split(':',1)[1]);count=0
        for a in db.scalars(select(Assignment).where(Assignment.event_id==e.id)):
            if effective_assignment(db,a)!='assignment_accepted':continue
            t=db.get(AssignmentTerms,a.current_terms_id)
            if t.content['role_requirement_id']==role['id']:count+=1
        if role['proposed_headcount'] is None or count<role['proposed_headcount']:conditions.append('actor_capacity_review:'+role['id'])
        original=next(r for r in db.get(PlanVersion,d['base_plan_id']).content['roles'] if r['id']==role['id'])
        if set(role['required_capabilities'])-set(original['required_capabilities']):conditions.append('new_capability_verification:'+role['id'])
    from app.resources.service import totals
    for w in content['work']:
        pred_stages=next(s for s in content['stages'] if s['id']==w['stage_id'])['dependency_ids']
        relevant=w['id'] in d['changed_work_ids'] or bool(set(w['dependency_ids'])&set(d['changed_work_ids'])) or any(x['stage_id'] in pred_stages and x['id'] in d['changed_work_ids'] for x in content['work'])
        if not relevant:continue
        stage=next(s for s in content['stages'] if s['id']==w['stage_id'])
        if w['schedule']['start_day']<stage['relative_start'] or w['schedule']['end_day']>stage['relative_end']:conditions.append('stage_window_review:'+w['id'])
        for rid in w['resource_requirement_ids']:
            r=next(x for x in content['resources'] if x['id']==rid)
            if r['quantity'] is None or r['kind'] in ('service','facility','funding'):conditions.append('unverified_resource:'+rid)
            else:
                from app.resources.models import ResourceReservation
                stock,reserved,_=totals(db,e,rid)
                own=sum(float(x.quantity) for x in db.scalars(select(ResourceReservation).where(ResourceReservation.event_id==e.id,ResourceReservation.resource_id==rid,ResourceReservation.work_id==w['id'],ResourceReservation.status=='reserved')))
                if float(stock-reserved)+own<r['quantity']:conditions.append('resource_shortfall:'+rid)
        for dep in w['dependency_ids']:
            if Schedule.model_validate(works[dep]['schedule']).finish>Schedule.model_validate(w['schedule']).start:errors.append('dependency_timing:'+w['id'])
        stage=next(s for s in content['stages'] if s['id']==w['stage_id'])
        for sid in stage['dependency_ids']:
            if any(Schedule.model_validate(p['schedule']).finish>Schedule.model_validate(w['schedule']).start for p in content['work'] if p['stage_id']==sid):errors.append('stage_dependency_timing:'+w['id'])
        schedules=[Schedule.model_validate(works[x]['schedule']) for x in works if x in d['changed_work_ids']]
        if not w['effort']['value'] and w['effort']['value']!=0:conditions.append('unknown_capacity:'+w['id'])
    for aid,item in d['reconfirmations'].items():
        a=db.get(Assignment,aid);app=db.get(Application,a.application_id);term=db.get(AssignmentTerms,item['terms_id']);s=term.content['schedule']
        if a.status!='assignment_accepted' or a.current_terms_id!=item['original_terms_id']:errors.append('assignment_changed:'+aid)
        if term.expires_at<=now():errors.append('offer_expired:'+aid)
        if not any(contains(x,s) for x in app.content['intervals']):conditions.append('outside_availability:'+aid)
        old=db.get(AssignmentTerms,item['original_terms_id'])
        if any(works[x]['skills'] for x in term.content['work_ids']):
            review=app.content.get('capability_reviews',{}).get(old.content['role_requirement_id'])
            if not review or review.get('plan_id')!=e.active_plan_id:conditions.append('capability_review:'+aid)
        for other in db.scalars(select(Assignment).where(Assignment.account_id==a.account_id,Assignment.id!=aid)):
            if effective_assignment(db,other)=='assignment_accepted':
                ot=db.get(AssignmentTerms,other.current_terms_id)
                if other.event_id!=e.id:conditions.append('cross_event_availability_review:'+aid)
                elif overlap(s,ot.content['schedule']):errors.append('schedule_conflict:'+aid)
        consent=db.scalar(select(AssignmentConsent).where(AssignmentConsent.terms_id==term.id,AssignmentConsent.account_id==a.account_id))
        if not consent:conditions.append('participant_reconfirmation:'+aid)
        elif consent.decision!='accept':errors.append('participant_declined:'+aid)
    # Do not claim feasibility without actual committed capacity for every changed work item.
    for wid in d['changed_work_ids']:
        hours=0
        for a in db.scalars(select(Assignment).where(Assignment.event_id==e.id,Assignment.status=='assignment_accepted')):
            t=db.get(AssignmentTerms,d['reconfirmations'][a.id]['terms_id'] if a.id in d['reconfirmations'] else a.current_terms_id)
            if wid in t.content['work_ids']:
                sch=Schedule.model_validate(t.content['schedule']);hours+=(sch.finish-sch.start)/60/len(t.content['work_ids'])
        required=works[wid]['effort']['value']
        if required is None or hours<required:conditions.append('insufficient_capacity:'+wid)
    return {'status':'invalid' if errors else 'conditional' if conditions else 'feasible','errors':sorted(set(errors)),'conditions':sorted(set(conditions))}

def create(db,actor,e,b):
    scope=impact(db,actor,e,b.issue_ids,b.expected_plan_id)
    base=db.get(PlanVersion,e.active_plan_id);content=deepcopy(base.content);by={w['id']:w for w in content['work']}
    allowed=set(scope['scope']['affected_work_ids'])-set(scope['scope']['preserved_complete_ids'])
    if not set(b.schedules)<=allowed:raise DomainError('scope_violation','Only affected unfinished work may change',422)
    for wid,s in b.schedules.items():by[wid]['schedule']=s.model_dump();by[wid]['revision']+=1
    from app.recovery.workspace import apply_patches
    changed_nodes=apply_patches(content,b.patches,scope['scope'])
    # Actor windows are derived from exact candidate source work, never invented capacity.
    changed_schedule_ids={wid for wid,w in by.items() if w['schedule']!=next(old for old in base.content['work'] if old['id']==wid)['schedule']}
    for role in content['roles']:
        if set(role['work_ids'])&changed_schedule_ids or 'actor:'+role['id'] in b.patches:
            role['schedule_intervals']=[by[wid]['schedule'] for wid in role['work_ids']]
    content=PlanContent.model_validate(content).model_dump()
    changed=[w['id'] for w in content['work'] if next(old for old in base.content['work'] if old['id']==w['id'])!=w]
    for role in content['roles']:
        if role!=next(old for old in base.content['roles'] if old['id']==role['id']):changed=list(set(changed)|set(role['work_ids']))
    if not changed and not changed_nodes and not b.hold:raise DomainError('empty_alternative','Provide changed nodes or explicit hold',422)
    # Immutable inactive plan; sequence is event-locked and not assumed to follow active sequence.
    seq=(db.scalar(select(func.max(PlanVersion.sequence)).where(PlanVersion.event_id==e.id)) or 0)+1
    candidate=PlanVersion(id=uid(),event_id=e.id,sequence=seq,parent_id=base.id,context_revision_id=e.active_context_revision_id,content=content,digest=digest(content),created_by=actor)
    db.add(candidate);db.flush()
    recon={}
    for a in db.scalars(select(Assignment).where(Assignment.event_id==e.id)):
        if effective_assignment(db,a)!='assignment_accepted':continue
        old=db.get(AssignmentTerms,a.current_terms_id)
        if not set(old.content['work_ids'])&set(changed):continue
        # Bounded v1: one consistent schedule per changed assignment; split assignments require manual redesign.
        ss=[by[x]['schedule'] for x in old.content['work_ids']]
        if any(s!=ss[0] for s in ss):raise DomainError('unsupported_assignment_split','Split assignment schedules require separate alternatives',422)
        data=deepcopy(old.content);data['schedule']=ss[0]
        for req in data.get('work_requirements',[]):req['revision']=by[req['id']]['revision']
        data['recovery_material_changes']={key:value for key,value in b.patches.items() if key.startswith(('actor:','work:'))}
        seqterm=(db.scalar(select(func.max(AssignmentTerms.sequence)).where(AssignmentTerms.assignment_id==a.id)) or 0)+1
        t=AssignmentTerms(id=uid(),event_id=e.id,assignment_id=a.id,plan_id=candidate.id,sequence=seqterm,content=data,digest=digest({'terms':data,'plan':candidate.id}),created_by=actor,expires_at=now()+timedelta(days=7))
        db.add(t);db.flush();recon[a.id]={'terms_id':t.id,'original_terms_id':old.id,'account_id':a.account_id}
    memory=MuseSparkContextBuilder().build(db,actor,e.id,purpose='blocker_recovery')
    d={'base_plan_id':base.id,'candidate_plan_id':candidate.id,'plan':content,'issue_ids':b.issue_ids,'scope':scope,'fingerprint':fingerprint(db,e,b.issue_ids),
       'memory_context':memory,'reconfirmations':recon,'changed_work_ids':sorted(changed),'changed_nodes':changed_nodes,'title':b.title,'rationale':b.rationale,'assumptions':b.assumptions,'risks':b.risks,'hold':b.hold,
       'status':'pending','audience':'internal','decision_history':[],'outcome':'inconclusive','model_execution':False}
    d['proposal_digest']=digest(d)
    row=CoordinationRecord(id=uid(),event_id=e.id,account_id=actor,kind='recovery',content={});db.add(row);db.flush();record(db,actor,e,row,'recovery.propose',d,'proposed')
    return view(db,actor,e,row)

def view(db,actor,e,row):
    return {'id':row.id,'revision':row.version,**row.content,'validation':validate(db,actor,e,row.content)}

def review(db,actor,e,rid,b):
    row=get(db,e,rid);d=deepcopy(row.content)
    if row.version!=b.expected_revision or d['proposal_digest']!=b.proposal_digest or d['status'] not in ('pending','clarify','held'):raise DomainError('stale_proposal','Review exact pending alternative')
    checks=validate(db,actor,e,d)
    if checks['errors']:raise DomainError('stale_proposal',','.join(checks['errors']))
    d['status']={'approve':'approved' if checks['status']=='feasible' else 'conditionally_approved','reject':'rejected','clarify':'clarify','hold':'held'}[b.decision]
    d['decision_history'].append({'actor':actor,'decision':b.decision,'reason':b.rationale,'digest':b.proposal_digest})
    record(db,actor,e,row,'recovery.review',d);return view(db,actor,e,row)

def consent(db,actor,e,rid,aid,b):
    row=get(db,e,rid);d=row.content;item=d['reconfirmations'].get(aid)
    if not item or item['account_id']!=actor:missing()
    if d['status'] not in ('approved','conditionally_approved'):raise DomainError('invalid_state','Organizer must select alternative first')
    t=db.get(AssignmentTerms,item['terms_id']);a=db.get(Assignment,aid)
    if t.digest!=b.terms_key or t.expires_at<=now() or a.current_terms_id!=item['original_terms_id'] or a.status!='assignment_accepted':raise DomainError('stale_terms','Review current unexpired changed terms')
    if db.scalar(select(AssignmentConsent).where(AssignmentConsent.terms_id==t.id)):raise DomainError('already_decided','Changed terms already decided')
    db.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':'participant:'+actor})
    db.add(AssignmentConsent(event_id=e.id,terms_id=t.id,account_id=actor,decision=b.decision,digest=t.digest));db.flush();e.version+=1
    source(db,actor,e,uid(),'recovery.consent',{'recovery_id':row.id,'assignment_id':aid,'terms_id':t.id,'decision':b.decision})
    return {'decision':b.decision}

def activate(db,actor,e,rid,b):
    row=get(db,e,rid);d=deepcopy(row.content)
    if row.version!=b.expected_revision or d['proposal_digest']!=b.proposal_digest or d['status'] not in ('approved','conditionally_approved'):raise DomainError('stale_proposal','Exact approved alternative required')
    for aid in sorted(d['reconfirmations']):
        a=db.get(Assignment,aid)
        db.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':'participant:'+a.account_id})
    checks=validate(db,actor,e,d)
    if checks['status']!='feasible':
        return {'activated':False,'status':'deferred','validation':checks}
    candidate=db.get(PlanVersion,d['candidate_plan_id']);old=db.get(Publication,e.current_publication_id)
    from app.resources.invariants import guard_plan
    guard_plan(db,e,candidate.content)
    # Keep immutable accepted terms for unchanged work; explicitly whitelist them in new publication.
    retained=[]
    for a in db.scalars(select(Assignment).where(Assignment.event_id==e.id,Assignment.status=='assignment_accepted')):
        if a.id in d['reconfirmations']:
            item=d['reconfirmations'][a.id];a.current_terms_id=item['terms_id'];a.version+=1
        else:retained.append(a.current_terms_id)
    previous=db.get(SetupRevision,old.setup_revision_id);config=deepcopy(previous.configuration);config['source_plan_id']=candidate.id
    setup=SetupRevision(id=uid(),event_id=e.id,sequence=(db.scalar(select(func.max(SetupRevision.sequence)).where(SetupRevision.event_id==e.id)) or 0)+1,source_plan_id=candidate.id,configuration=config,digest=digest(config),created_by=actor);db.add(setup);db.flush()
    final=Finalization(id=uid(),event_id=e.id,setup_revision_id=setup.id,plan_id=candidate.id,reviewed_digest=d['proposal_digest'],approved_by=actor);db.add(final);db.flush()
    snap=deepcopy(old.snapshot);snap['plan']=candidate.content;snap['configuration']=config;snap['retained_assignment_terms']=retained
    release=Publication(id=uid(),event_id=e.id,sequence=old.sequence+1,finalization_id=final.id,plan_id=candidate.id,setup_revision_id=setup.id,snapshot=snap,digest=digest(snap),visibility=old.visibility,approved_by=actor);db.add(release);db.flush()
    for role in candidate.content['roles']:db.add(PublishedRole(event_id=e.id,publication_id=release.id,plan_id=candidate.id,requirement_id=role['id']))
    for work in db.scalars(select(WorkExecution).where(WorkExecution.event_id==e.id,WorkExecution.plan_id==d['base_plan_id'])):
        if work.work_id not in d['changed_work_ids']:
            db.add(WorkExecution(event_id=e.id,plan_id=candidate.id,work_id=work.work_id,version=work.version,content=deepcopy(work.content)))
    from app.resources.models import ResourceReservation
    for reservation in db.scalars(select(ResourceReservation).where(ResourceReservation.event_id==e.id,ResourceReservation.plan_id==d['base_plan_id'])):
        reservation.plan_id=candidate.id
    e.active_plan_id=candidate.id;e.current_publication_id=release.id;e.current_setup_id=setup.id;e.current_finalization_id=final.id;e.lifecycle='published'
    from app.planning.draft_models import PlanningDraft
    draft=db.scalar(select(PlanningDraft).where(PlanningDraft.event_id==e.id))
    if draft:draft.content=deepcopy(candidate.content);draft.version+=1
    d['status']='activated';record(db,actor,e,row,'recovery.activate',d,'attempted','inconclusive','Plan activation is not verified operational success')
    return {'activated':True,'plan_id':candidate.id,'status':'activated','outcome':'inconclusive'}
