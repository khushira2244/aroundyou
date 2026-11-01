from copy import deepcopy
from datetime import datetime,timedelta,date,time,timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select,text
from app.participation.models import Application,ApplicationRevision,Assignment,AssignmentTerms,AssignmentConsent,OperationalSource
from app.participation.schemas import Answers
from app.publication.models import Publication
from app.events.models import Event
from app.access.models import User
from app.access.authorization import allowed,require
from app.shared.types import uid,digest,now
from app.shared.audit import audit
from app.shared.models import ReviewDecision
from app.api.errors import DomainError,missing

def require_state(condition,message):
    if not condition:raise DomainError('invalid_state',message)

def published(session,event,actor=None,current=False):
    release=session.get(Publication,event.current_publication_id) if event.current_publication_id else None
    if not release or (release.visibility!='public' and not (actor and allowed(session,actor,event.id,'event:read'))):missing()
    if current:require_state(release.plan_id==event.active_plan_id and release.snapshot['event']['context_id']==event.active_context_revision_id,'Published plan/context changed; organizer must republish')
    return release

def source(session,actor,event,aggregate,kind,content):
    previous=session.scalar(select(OperationalSource).where(OperationalSource.event_id==event.id,OperationalSource.aggregate_id==aggregate).order_by(OperationalSource.sequence.desc()).limit(1))
    row=OperationalSource(id=uid(),event_id=event.id,aggregate_id=aggregate,sequence=previous.sequence+1 if previous else 1,kind=kind,content=content,digest=digest(content),created_by=actor)
    session.add(row);session.flush()
    from app.events.source_revisions import capture
    from app.memory.schemas import SourceRef
    capture(session,event.creator_id,event.id,SourceRef(source_kind='operational',source_id=row.id,source_revision=row.sequence,source_digest=row.digest))
    audit(session,actor,event.id,kind,aggregate,source_id=row.id)
    return row

def app_for(session,event,app_id,actor,organizer=False):
    row=session.get(Application,app_id)
    if not row or row.event_id!=event.id or (not organizer and row.account_id!=actor) or (organizer and row.status=='application_draft' and row.account_id!=actor):missing()
    return row

def revise(session,actor,event,a,data,status=None,operation='application.revise'):
    a.content=deepcopy(data);a.sequence+=1;a.version+=1
    if status:a.status=status
    snapshot={'status':a.status,'plan_id':a.plan_id,'content':data}
    session.add(ApplicationRevision(event_id=event.id,application_id=a.id,sequence=a.sequence,content=snapshot,digest=digest(snapshot),created_by=actor))
    event.version+=1
    if a.status!='application_draft':source(session,actor,event,a.id,operation,{'application_id':a.id,'revision':a.sequence,'status':a.status,'plan_id':a.plan_id,'notice':'Application/review is not participant consent or work success'})
    session.flush();return {'application':application_dto(session,a)}

def validate_answers(answers,configuration):
    fields=answers['participant_insights']['fields'];insights=answers['participant_insights']
    enabled=configuration.get('fields',{})
    if fields and (not configuration.get('collect_insights') or any(not enabled.get(k) for k in fields)):raise DomainError('invalid_fields','Insight fields are not enabled',422)
    tags={x['id'] for x in configuration.get('custom_tags',[]) if x.get('active',True)}
    if set(insights['tag_ids'])-tags:raise DomainError('invalid_fields','Unknown participant tag',422)
    questions={x['id']:x for x in configuration.get('questions',[]) if x.get('active',True)}
    for k,v in answers['custom_answers'].items():
        if k not in questions:raise DomainError('invalid_fields','Unknown application question',422)
        q=questions[k];values=v if isinstance(v,list) else [v]
        if sum(len(x) for x in values)>4000:raise DomainError('invalid_fields','Answer too long',422)
        if q['answer_type']!='short_answer' and (set(values)-set(q['options']) or (q['answer_type']=='single_choice' and len(values)!=1)):raise DomainError('invalid_fields','Invalid answer option',422)

def save_draft(session,actor,event,body):
    release=published(session,event,actor,True);config=release.snapshot['configuration']
    require_state(config['participation']['registration_open'],'Registration is closed')
    a=session.scalar(select(Application).where(Application.event_id==event.id,Application.account_id==actor))
    if body.application_id and (not a or a.id!=body.application_id):missing()
    if not a:
        a=Application(id=uid(),event_id=event.id,account_id=actor,plan_id=release.plan_id,content={});session.add(a);session.flush()
    require_state(a.status=='application_draft','Only a private draft can be autosaved')
    data=deepcopy(a.content or {'role_ids':[],'work_ids':[],'intervals':[],'answers':Answers().model_dump(),'wizard_step':1,'approved_role_ids':[],'clarifications':[],'capability_reviews':{},'alternatives':[]})
    roles={r['id']:r for r in release.snapshot['plan']['roles']};work={w['id']:w for w in release.snapshot['plan']['work']}
    if body.role_ids is not None:
        if len(set(body.role_ids))!=len(body.role_ids) or set(body.role_ids)-roles.keys():raise DomainError('invalid_roles','Choose published role requirements',422)
        data['role_ids']=body.role_ids
    if body.work_ids is not None:
        permitted={wid for rid in data['role_ids'] for wid in roles[rid]['work_ids']}
        if set(body.work_ids)-permitted:raise DomainError('invalid_work','Work must belong to selected roles',422)
        data['work_ids']=body.work_ids
    if set(data.get('work_ids',[]))-{wid for rid in data['role_ids'] for wid in roles[rid]['work_ids']}:raise DomainError('invalid_work','Selected work must remain linked to selected roles',422)
    if body.intervals is not None:
        for interval in body.intervals:
            if interval.timezone!=release.snapshot['event']['schedule']['timezone']:raise DomainError('invalid_schedule','Use the event timezone',422)
        data['intervals']=[x.model_dump() for x in body.intervals]
    if body.answers is not None:
        data['answers']=body.answers.model_dump();validate_answers(data['answers'],config['tags'])
    if body.step is not None:data['wizard_step']=body.step
    a.plan_id=release.plan_id
    return revise(session,actor,event,a,data)

def transition(session,actor,event,a,action,body):
    data=deepcopy(a.content)
    if action=='advance':
        require_state(a.status=='application_draft','Only drafts have wizard steps');data['wizard_step']=body.step
    elif action=='submit':
        require_state(a.status=='application_draft' and body.acknowledged,'Explicit reviewed submission required')
        from app.participation import dynamic_insights as di
        config=di.configuration(session,event)
        required=[q['id'] for q in config['questions'] if q['enabled'] and q['required']]
        response=di.latest(session,event.id,'insight.response',actor)
        require_state(not required or (response and response.content['configuration_revision']==config['revision'] and all(k in response.content['answers'] for k in required)),'Save current required event question answers before submitting')
        release=published(session,event,actor,True)
        require_state(release.plan_id==a.plan_id and release.snapshot['configuration']['participation']['registration_open'],'Application plan is stale or recruitment closed')
        require_state(bool(data['role_ids'] and data['intervals']),'Select roles and availability')
        validate_answers(data['answers'],release.snapshot['configuration']['tags'])
        return revise(session,actor,event,a,data,'submitted','application.submit')
    elif action in ('begin-review','reopen-review'):
        require_state(a.status in ('submitted','approved','pending_review'),'Application is not reviewable');return revise(session,actor,event,a,data,'pending_review','application.begin_review')
    elif action=='review':
        require_state(a.status=='pending_review' and body.reviewed_revision==a.sequence,'Review exact application revision')
        require_state(a.plan_id==published(session,event,actor,True).plan_id,'Review current published plan')
        require_state(not (set(body.approved_role_ids)-set(data['role_ids'])),'Only requested roles can be approved')
        data['approved_role_ids']=body.approved_role_ids;data['review_note']=body.note
        session.add(ReviewDecision(event_id=event.id,actor_id=actor,subject_kind='application',subject_id=a.id,subject_digest=digest(a.content),decision='partial_approval' if body.approved_role_ids else 'reject',note=body.note))
        return revise(session,actor,event,a,data,'approved' if body.approved_role_ids else 'rejected','application.review')
    elif action=='withdraw':
        require_state(not session.scalar(select(Assignment.id).where(Assignment.application_id==a.id,Assignment.status.in_(['assignment_offered','assignment_accepted']))),'Withdraw live offers/commitments first')
        return revise(session,actor,event,a,data,'withdrawn','application.withdraw')
    return revise(session,actor,event,a,data)

def clarify(session,actor,event,a,question=None,clarification_id=None,answer=None):
    require_state(a.status in ('submitted','pending_review','approved'),'Submitted application required')
    data=deepcopy(a.content)
    if question:
        require_state(len(data['clarifications'])<30,'Clarification limit reached');data['clarifications'].append({'id':uid(),'question':question,'answer':None,'status':'requested'})
    else:
        q=next((x for x in data['clarifications'] if x['id']==clarification_id),None)
        if not q:missing()
        q['answer']=answer;q['status']='answered';data['approved_role_ids']=[]
    return revise(session,actor,event,a,data,'pending_review','application.clarification')

def effective_assignment(session,a):
    t=session.get(AssignmentTerms,a.current_terms_id)
    event=session.get(Event,a.event_id)
    if a.status=='assignment_offered' and t.expires_at<=now():return 'assignment_expired'
    if a.status=='assignment_accepted':
        release=session.get(Publication,event.current_publication_id) if event.current_publication_id else None
        if ((event.active_plan_id!=t.plan_id or (release and release.plan_id!=t.plan_id)) and not (release and release.plan_id==event.active_plan_id and t.id in release.snapshot.get('retained_assignment_terms',[]))) or not release or release.snapshot['event']['context_id']!=event.active_context_revision_id:return 'requires_reconfirmation'
    return a.status

def assignment_dto(session,a):
    t=session.get(AssignmentTerms,a.current_terms_id)
    return {'id':a.id,'application_id':a.application_id,'account_id':a.account_id,'event_id':a.event_id,**t.content,'status':effective_assignment(session,a),'terms_key':t.digest,'plan_id':t.plan_id,'version':a.version,'expires_at':t.expires_at.isoformat()}

def application_dto(session,a):
    data=a.content
    from app.participation.advisory import intelligence
    return {'id':a.id,'event_id':a.event_id,'account_id':a.account_id,'plan_id':a.plan_id,'version':a.version,'revision':a.sequence,'role_requirement_ids':data['role_ids'],'work_ids':data.get('work_ids',[]),'availability_id':a.id,'availability_snapshot':data['intervals'],'availability':data['intervals'],'answers':data['answers'],'status':a.status,'wizard_step':data['wizard_step'],'approved_role_ids':data['approved_role_ids'],'applicant_label':session.get(User,a.account_id).display_name,'intelligence':intelligence(session,session.get(Event,a.event_id),a)}

def bounds(s):return ((s['start_day']-1)*1440+s['start_minute'],(s['end_day']-1)*1440+s['end_minute'])
def contains(a,b):return a['timezone']==b['timezone'] and bounds(a)[0]<=bounds(b)[0] and bounds(a)[1]>=bounds(b)[1]
def overlap(a,b):return bounds(a)[0]<bounds(b)[1] and bounds(b)[0]<bounds(a)[1]
def absolute(event,s):
    anchor=event.draft_form.get('startDate')
    if not anchor:return None
    base=datetime.combine(date.fromisoformat(anchor),time(),ZoneInfo(s['timezone']))
    return ((base+timedelta(minutes=bounds(s)[0])).astimezone(timezone.utc),(base+timedelta(minutes=bounds(s)[1])).astimezone(timezone.utc))

def candidate_check(session,event,a,body,exclude_id=None):
    release=published(session,event,a.account_id,True);roles={r['id']:r for r in release.snapshot['plan']['roles']};works={w['id']:w for w in release.snapshot['plan']['work']}
    r=roles.get(body.role_id);schedule=body.schedule.model_dump();conflicts=[]
    if not r or body.expected_plan_id!=release.plan_id or a.plan_id!=release.plan_id:return {'candidate':{},'conflicts':['stale_plan_or_role'],'explanation':'Current published work required','model_execution':False}
    if a.status!='approved' or body.role_id not in a.content['approved_role_ids']:conflicts.append('role_not_approved')
    if len(set(body.work_ids))!=len(body.work_ids) or set(body.work_ids)-set(r['work_ids']):conflicts.append('work_not_in_role')
    if a.content.get('work_ids') and set(body.work_ids)-set(a.content['work_ids']):conflicts.append('work_not_requested')
    if not any(contains(x,schedule) for x in a.content['intervals']):conflicts.append('outside_availability')
    for wid in body.work_ids:
        if wid not in works or works[wid]['schedule']['timezone']!=schedule['timezone'] or not overlap(works[wid]['schedule'],schedule):conflicts.append('outside_work_schedule')
    selected=[works[w]['schedule'] for w in body.work_ids if w in works]
    if selected and (bounds(schedule)[0]<min(bounds(x)[0] for x in selected) or bounds(schedule)[1]>max(bounds(x)[1] for x in selected)):conflicts.append('outside_work_schedule')
    required=r['required_capabilities']
    review=a.content.get('capability_reviews',{}).get(body.role_id)
    if required and (not review or review.get('plan_id')!=release.plan_id):conflicts.append('capabilities_require_human_review')
    if a.content['answers'].get('limitations') and (not review or review.get('plan_id')!=release.plan_id):conflicts.append('limitations_require_human_review')
    capacity=r['proposed_headcount'];accepted=0
    for other in session.scalars(select(Assignment).where(Assignment.id!=exclude_id if exclude_id else Assignment.id.is_not(None))):
        if effective_assignment(session,other)!='assignment_accepted':continue
        t=session.get(AssignmentTerms,other.current_terms_id);s=t.content['schedule']
        if other.event_id==event.id and t.content['role_requirement_id']==body.role_id and overlap(s,schedule):accepted+=1
        if other.account_id==a.account_id:
            if other.event_id==event.id:
                if set(t.content['work_ids'])&set(body.work_ids):conflicts.append('duplicate_work_commitment')
                if overlap(s,schedule):conflicts.append('schedule_overlap')
            else:
                x=absolute(event,schedule);y=absolute(session.get(Event,other.event_id),s)
                if not x or not y:conflicts.append('cross_event_anchor_unknown')
                elif x[0]<y[1] and y[0]<x[1]:conflicts.append('cross_event_schedule_overlap')
    if capacity is None:conflicts.append('capacity_unknown')
    elif accepted>=capacity:conflicts.append('role_capacity_exhausted')
    return {'candidate':{'role_requirement_id':body.role_id,'work_ids':body.work_ids,'schedule':schedule},'conflicts':sorted(set(conflicts)),'explanation':'Deterministic checks; no AI acceptance or guarantee of task competence','model_execution':False}

def offer(session,actor,event,a,body):
    session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':'participant:'+a.account_id})
    existing=session.get(Assignment,body.replaces_assignment_id) if body.replaces_assignment_id else None
    if body.replaces_assignment_id and (not existing or existing.application_id!=a.id or existing.event_id!=event.id):missing()
    check=candidate_check(session,event,a,body,existing.id if existing else None)
    require_state(not check['conflicts'],'Assignment conflicts: '+', '.join(check['conflicts']))
    if not existing:
        existing=Assignment(id=uid(),event_id=event.id,application_id=a.id,account_id=a.account_id);session.add(existing);session.flush()
    previous=session.get(AssignmentTerms,existing.current_terms_id) if existing.current_terms_id else None
    release=published(session,event,actor);work={w['id']:w for w in release.snapshot['plan']['work']};role=next(r for r in release.snapshot['plan']['roles'] if r['id']==body.role_id)
    requirements=[{k:work[wid][k] for k in ('id','title','revision','scope','conditions','exclusion_constraints','evidence_requirements','resource_requirement_ids')} for wid in body.work_ids]
    conditions=list(dict.fromkeys(body.conditions+[x for wid in body.work_ids for x in work[wid]['conditions']+work[wid]['exclusion_constraints']]))
    data={**check['candidate'],'role_title':role['title'],'location':release.snapshot['event']['location'],'conditions':conditions,'work_requirements':requirements,'organizer_instructions':release.snapshot['configuration']['communications']['participant_instructions'],'application_revision':a.sequence}
    expires=now()+timedelta(hours=body.expires_in_hours)
    term=AssignmentTerms(id=uid(),event_id=event.id,assignment_id=existing.id,plan_id=body.expected_plan_id,sequence=previous.sequence+1 if previous else 1,content=data,digest=digest({'terms':data,'plan':body.expected_plan_id,'expires_at':expires.isoformat()}),created_by=actor,expires_at=expires)
    session.add(term);session.flush();existing.current_terms_id=term.id;existing.status='assignment_offered';existing.version+=1;event.version+=1
    source(session,actor,event,existing.id,'assignment.offer',{'assignment_id':existing.id,'terms_id':term.id,'terms_digest':term.digest,'state':'offered','outcome':'unknown'})
    return {'assignment':assignment_dto(session,existing)}

def consent(session,actor,event,assignment_id,body,decision):
    a=session.get(Assignment,assignment_id)
    if not a or a.event_id!=event.id or a.account_id!=actor:missing()
    t=session.get(AssignmentTerms,a.current_terms_id)
    session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':'participant:'+actor})
    if body.terms_key!=t.digest:raise DomainError('stale_terms','Review exact current offer terms')
    require_state(a.status=='assignment_offered' and t.expires_at>now(),'Offer is expired, withdrawn or already decided')
    require_state(body.confirmed,'Explicit participant consent required')
    if decision=='accept':
        from app.participation.schemas import Offer
        app=app_for(session,event,a.application_id,actor)
        check=candidate_check(session,event,app,Offer(role_id=t.content['role_requirement_id'],work_ids=t.content['work_ids'],schedule=t.content['schedule'],expected_plan_id=t.plan_id),a.id)
        require_state(not check['conflicts'],'Acceptance conflicts: '+', '.join(check['conflicts']))
    session.add(AssignmentConsent(event_id=event.id,terms_id=t.id,account_id=actor,decision=decision,digest=t.digest));a.status='assignment_accepted' if decision=='accept' else 'assignment_declined';a.version+=1;event.version+=1
    source(session,actor,event,a.id,'assignment.consent',{'assignment_id':a.id,'terms_id':t.id,'terms_digest':t.digest,'decision':decision,'outcome':'unknown','notice':'Consent is not attendance or completed work'})
    return {'assignment':assignment_dto(session,a)}

def withdraw_assignment(session,actor,event,assignment_id,organizer=False):
    a=session.get(Assignment,assignment_id)
    if not a or a.event_id!=event.id or (not organizer and a.account_id!=actor):missing()
    require_state(a.status in ('assignment_offered','assignment_accepted'),'No live offer or commitment to withdraw')
    a.status='assignment_withdrawn';a.version+=1;event.version+=1
    source(session,actor,event,a.id,'assignment.withdraw',{'assignment_id':a.id,'state':'withdrawn','outcome':'unknown'})
    return {'assignment':assignment_dto(session,a)}
