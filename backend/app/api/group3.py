from copy import deepcopy
from fastapi import APIRouter,Header,Depends,Request,Query,BackgroundTasks
from pydantic import Field
from sqlalchemy import select
from app.api.group2 import USER,DB,ok
from app.api.errors import DomainError,missing
from app.shared.idempotency import execute_once
from app.events.models import Event
from app.access.authorization import require,allowed
from app.access.models import EventGrant
from app.participation import service as ps,projections as pp
from app.participation.models import Application,Assignment,AssignmentTerms
from app.participation.schemas import ApplicationDraft,Submit,Review,Offer,Consent,Clarification,ClarificationAnswer,CapabilityReview,Empty
from app.sponsorship.schemas import OrganizationDraft,SupportDraft,Fulfillment,Receipt,Reservation,Reason
from app.sponsorship import service as ss,projections as sp
from app.sponsorship.models import SupportOffer,SupportFulfillment
from app.resources import service as rs
from app.memory.schemas import StrictModel
router=APIRouter()

class Advance(StrictModel):step:int=Field(ge=1,le=4)
class OrganizationAction(StrictModel):organization_id:str
class AdvisoryRequest(StrictModel):
    application_id:str|None=None
    message:str=Field(default='',max_length=2000)

@router.post('/events/{event_id}/applications/{application_id}/role-suggestions')
def applicant_role_suggestions(event_id:str,application_id:str,body:Empty,request:Request,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    from app.participation.role_suggestions import suggest
    return write(db,user,event_id,'participation.role_suggestions:'+application_id,idempotency_key,if_match,{},lambda e:suggest(db,user.id,e,application_id,request.app.state.planning_adapter))


def write(db,user,eid,operation,key,version,payload,action,organizer=False):
    event=db.get(Event,eid)
    if not event:missing()
    if organizer:require(db,user.id,eid,'plan:write');require(db,user.id,eid,'source:private')
    else:ps.published(db,event,user.id)
    def apply():
        event=db.scalar(select(Event).where(Event.id==eid).with_for_update().execution_options(populate_existing=True))
        # Authorization peeks may have loaded reports before waiting for the event lock.
        # Refresh those identities before exact-version domain validation.
        db.expire_all()
        if str(event.version)!=str(version).strip('"'):raise DomainError('stale_version','Reload the current event state before this command')
        value=action(event);db.flush();return value
    return ok(execute_once(db,user.id,eid,operation,key,{'payload':payload,'version':version},apply),event)

@router.get('/participation-opportunities')
def opportunities(user=USER,db=DB):
    items=[]
    for event in db.scalars(select(Event).where(Event.current_publication_id.is_not(None))):
        try:r=ps.published(db,event,user.id,True)
        except DomainError:continue
        from app.publication.service import profile
        p=profile(db,event,user.id);items.append({'event':p['event'],'roles':p['roles'],'accepted_participants':p['impact']['accepted_participants'],'visibility':p['visibility'],'can_apply':r.snapshot['configuration']['participation']['registration_open'],'recruitment':'open' if r.snapshot['configuration']['participation']['registration_open'] else 'closed'})
    return ok({'items':items})
@router.get('/events/{event_id}/participation/me')
def participation(event_id:str,application_id:str|None=None,user=USER,db=DB):
    event=db.get(Event,event_id)
    if not event:missing()
    return ok(pp.participation_state(db,user.id,event,application_id),event)
@router.get('/events/{event_id}/organizer/participants')
def organizer_participants(event_id:str,user=USER,db=DB):
    event=require(db,user.id,event_id,'plan:write');return ok(pp.organizer_participants(db,user.id,event),event)
@router.post('/events/{event_id}/applications/draft')
def draft(event_id:str,body:ApplicationDraft,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'application.draft',idempotency_key,if_match,body.model_dump(mode='json'),lambda e:ps.save_draft(db,user.id,e,body))
@router.post('/events/{event_id}/applications/{application_id}/advance')
def advance(event_id:str,application_id:str,body:Advance,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'application.advance:'+application_id,idempotency_key,if_match,body.model_dump(),lambda e:ps.transition(db,user.id,e,ps.app_for(db,e,application_id,user.id),'advance',body))
@router.post('/events/{event_id}/applications/{application_id}/submit')
def submit(event_id:str,application_id:str,body:Submit,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'application.submit:'+application_id,idempotency_key,if_match,body.model_dump(),lambda e:ps.transition(db,user.id,e,ps.app_for(db,e,application_id,user.id),'submit',body))
@router.post('/events/{event_id}/applications/{application_id}/withdraw')
def withdraw_application(event_id:str,application_id:str,body:Empty,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'application.withdraw:'+application_id,idempotency_key,if_match,{},lambda e:ps.transition(db,user.id,e,ps.app_for(db,e,application_id,user.id),'withdraw',body))
@router.post('/events/{event_id}/applications/{application_id}/begin-review')
@router.post('/events/{event_id}/applications/{application_id}/reopen-review')
def begin_review(event_id:str,application_id:str,body:Empty,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'application.begin_review:'+application_id,idempotency_key,if_match,{},lambda e:ps.transition(db,user.id,e,ps.app_for(db,e,application_id,user.id,True),'begin-review',body),True)
@router.post('/events/{event_id}/applications/{application_id}/review')
def review(event_id:str,application_id:str,body:Review,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'application.review:'+application_id,idempotency_key,if_match,body.model_dump(),lambda e:ps.transition(db,user.id,e,ps.app_for(db,e,application_id,user.id,True),'review',body),True)
@router.post('/events/{event_id}/applications/{application_id}/clarifications')
def clarify(event_id:str,application_id:str,body:Clarification,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'application.clarify:'+application_id,idempotency_key,if_match,body.model_dump(),lambda e:ps.clarify(db,user.id,e,ps.app_for(db,e,application_id,user.id,True),question=body.question),True)
@router.post('/events/{event_id}/applications/{application_id}/clarifications/{clarification_id}/answer')
def answer(event_id:str,application_id:str,clarification_id:str,body:ClarificationAnswer,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'application.answer:'+clarification_id,idempotency_key,if_match,body.model_dump(),lambda e:ps.clarify(db,user.id,e,ps.app_for(db,e,application_id,user.id),clarification_id=clarification_id,answer=body.answer))
@router.post('/events/{event_id}/applications/{application_id}/capability-reviews')
def capability(event_id:str,application_id:str,body:CapabilityReview,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        a=ps.app_for(db,e,application_id,user.id,True);ps.require_state(body.confirm and body.role_id in a.content['role_ids'],'Explicit review of requested capability required');data=deepcopy(a.content);data['capability_reviews'][body.role_id]={'note':body.note,'reviewer':user.id,'plan_id':a.plan_id};return ps.revise(db,user.id,e,a,data,operation='application.capability_review')
    return write(db,user,event_id,'capability.review:'+application_id,idempotency_key,if_match,body.model_dump(),apply,True)
@router.post('/events/{event_id}/applications/{application_id}/assignment-checks')
def check_assignment(event_id:str,application_id:str,body:Offer,user=USER,db=DB):
    e=require(db,user.id,event_id,'plan:write');require(db,user.id,event_id,'source:private');return ok(ps.candidate_check(db,e,ps.app_for(db,e,application_id,user.id,True),body),e)
@router.post('/events/{event_id}/applications/{application_id}/assignment-offers')
def offer_assignment(event_id:str,application_id:str,body:Offer,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'assignment.offer:'+application_id,idempotency_key,if_match,body.model_dump(mode='json'),lambda e:ps.offer(db,user.id,e,ps.app_for(db,e,application_id,user.id,True),body),True)
@router.post('/events/{event_id}/assignments/{assignment_id}/accept')
@router.post('/events/{event_id}/assignments/{assignment_id}/decline')
def assignment_consent(event_id:str,assignment_id:str,body:Consent,request:Request,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    decision='accept' if request.url.path.endswith('/accept') else 'decline'
    def apply(e):
        result=ps.consent(db,user.id,e,assignment_id,body,decision)
        return result
    return write(db,user,event_id,'assignment.'+decision+':'+assignment_id,idempotency_key,if_match,body.model_dump(),apply)
@router.post('/events/{event_id}/assignments/{assignment_id}/withdraw')
def withdraw_assignment(event_id:str,assignment_id:str,body:Empty,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'assignment.withdraw:'+assignment_id,idempotency_key,if_match,{},lambda e:ps.withdraw_assignment(db,user.id,e,assignment_id,allowed(db,user.id,e.id,'plan:write')))
@router.get('/me/sponsor-portal')
def sponsor_portal(organization_id:str|None=None,user=USER,db=DB):return ok(sp.portal(db,user.id,organization_id))
@router.post('/organizations/draft')
def organization_draft(body:OrganizationDraft,user=USER,db=DB,idempotency_key:str=Header()):
    return ok(execute_once(db,user.id,body.organization_id or user.id,'organization.draft',idempotency_key,body.model_dump(),lambda:ss.save_organization(db,user.id,body)))
@router.post('/organizations/{organization_id}/registration/complete')
def organization_registration(organization_id:str,body:Empty,user=USER,db=DB,idempotency_key:str=Header()):
    ss.member(db,user.id,organization_id)
    return ok(execute_once(db,user.id,organization_id,'organization.register',idempotency_key,{},lambda:ss.complete_organization(db,user.id,organization_id)))
@router.post('/events/{event_id}/support-offers/draft')
def support_draft(event_id:str,body:SupportDraft,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'support.draft',idempotency_key,if_match,body.model_dump(mode='json'),lambda e:ss.save_offer(db,user.id,e,body))
@router.post('/events/{event_id}/sponsor-offers/{offer_id}/fulfillments')
def support_report(event_id:str,offer_id:str,body:Fulfillment,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'support.report:'+offer_id,idempotency_key,if_match,body.model_dump(mode='json'),lambda e:ss.report(db,user.id,e,ss.own_offer(db,user.id,e,offer_id),body))
class SponsorRevision(StrictModel):
    body:str=Field(min_length=1,max_length=2000)
@router.post('/events/{event_id}/sponsor-offers/{offer_id}/revision-requests')
def sponsor_revision(event_id:str,offer_id:str,body:SponsorRevision,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'support.revision:'+offer_id,idempotency_key,if_match,body.model_dump(),lambda e:ss.request_revision(db,user.id,e,offer_id,body.body),True)

@router.post('/events/{event_id}/sponsor-offers/{offer_id}/{action}')
def support_transition(event_id:str,offer_id:str,action:str,body:Empty,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    if action not in ('submit','accept','reject','withdraw'):raise DomainError('invalid_action','Unknown support action',422)
    organizer=action in ('accept','reject')
    return write(db,user,event_id,'support.'+action+':'+offer_id,idempotency_key,if_match,{},lambda e:ss.transition(db,user.id,e,db.get(SupportOffer,offer_id) if organizer else ss.own_offer(db,user.id,e,offer_id),action) if not organizer or (db.get(SupportOffer,offer_id) and db.get(SupportOffer,offer_id).event_id==e.id) else missing(),organizer)
@router.get('/events/{event_id}/organizer/sponsor-offers')
def organizer_support(event_id:str,user=USER,db=DB):
    e=require(db,user.id,event_id,'plan:write');require(db,user.id,event_id,'source:private');needs=next((o['needs'] for o in sp.opportunities(db,user.id) if o['id']==e.id),[])
    from app.resources.models import ResourceTransaction
    reports=[{'id':f.id,'offer_id':f.offer_id,'quantity':float(f.quantity),'reference':f.reference,'verified':ss.fulfillment_credit(db,f)} for f in db.scalars(select(SupportFulfillment).where(SupportFulfillment.event_id==e.id))]
    return ok({'event_id':e.id,'fulfillments':reports,'offers':[ss.offer_dto(db,o) for o in db.scalars(select(SupportOffer).where(SupportOffer.event_id==e.id,SupportOffer.status!='draft'))],'needs':needs},e)
@router.get('/events/{event_id}/resources')
def resources(event_id:str,user=USER,db=DB):
    e=require(db,user.id,event_id,'plan:write');return ok({'resources':rs.projection(db,e,user.id)},e)
@router.post('/events/{event_id}/resource-receipts')
def receipt(event_id:str,body:Receipt,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'resource.receipt',idempotency_key,if_match,body.model_dump(mode='json'),lambda e:rs.receipt(db,user.id,e,body),True)
@router.post('/events/{event_id}/resource-receipts/{receipt_id}/corrections')
def correction(event_id:str,receipt_id:str,body:Reason,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'resource.correct:'+receipt_id,idempotency_key,if_match,body.model_dump(),lambda e:rs.correct_receipt(db,user.id,e,receipt_id,body.reason),True)
@router.post('/events/{event_id}/resource-reservations')
def reservation(event_id:str,body:Reservation,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'resource.reserve',idempotency_key,if_match,body.model_dump(mode='json'),lambda e:rs.reserve(db,user.id,e,body),True)
@router.post('/events/{event_id}/resource-reservations/{reservation_id}/release')
def release_reservation(event_id:str,reservation_id:str,body:Empty,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    return write(db,user,event_id,'resource.release:'+reservation_id,idempotency_key,if_match,{},lambda e:rs.release(db,user.id,e,reservation_id),True)

@router.post('/events/{event_id}/participation-assessments',status_code=202)
@router.post('/events/{event_id}/resource-assessments',status_code=202)
def advisory(event_id:str,body:AdvisoryRequest,request:Request,background_tasks:BackgroundTasks,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    from app.ai.service import request_run
    kind='resources' if '/resource-assessments' in request.url.path else 'participation'
    result=write(db,user,event_id,'ai.'+kind,idempotency_key,if_match,body.model_dump(),lambda e:request_run(db,user.id,e,kind,body.message,request.app.state.planning_adapter,body.application_id),True)
    if kind=='participation' and getattr(request.app.state.planning_adapter,'live_provider',False):
        from app.ai.service import work_ai_once
        background_tasks.add_task(work_ai_once,request.app.state.session_factory,request.app.state.planning_adapter,run_id=result['data']['run_id'])
    return result
class AdvisoryReview(StrictModel):
    decision:str
    reviewed_digest:str
@router.post('/events/{event_id}/participation-proposals/{proposal_id}/review')
@router.post('/events/{event_id}/resource-proposals/{proposal_id}/review')
def advisory_review(event_id:str,proposal_id:str,body:AdvisoryReview,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    from app.ai.service import review_advice
    if body.decision not in ('accept','reject'):raise DomainError('invalid_decision','Accept or reject the advisory proposal',422)
    return write(db,user,event_id,'ai.group3.review:'+proposal_id,idempotency_key,if_match,body.model_dump(),lambda e:review_advice(db,user.id,e,proposal_id,body.decision,body.reviewed_digest),True)

class InformationRevision(StrictModel):
    answers:__import__('app.participation.schemas',fromlist=['Answers']).Answers|None=None
    intervals:list[__import__('app.planning.schemas',fromlist=['Schedule']).Schedule]|None=None
@router.post('/events/{event_id}/applications/{application_id}/information-revisions')
def information_revision(event_id:str,application_id:str,body:InformationRevision,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        a=ps.app_for(db,e,application_id,user.id);data=deepcopy(a.content)
        if body.answers is not None:data['answers']=body.answers.model_dump();ps.validate_answers(data['answers'],ps.published(db,e,user.id).snapshot['configuration']['tags'])
        if body.intervals is not None:
            intervals=[x.model_dump() for x in body.intervals]
            for assignment in db.scalars(select(Assignment).where(Assignment.application_id==a.id)):
                if ps.effective_assignment(db,assignment)=='assignment_accepted':ps.require_state(any(ps.contains(x,db.get(AssignmentTerms,assignment.current_terms_id).content['schedule']) for x in intervals),'Withdraw or renegotiate commitments before removing accepted availability')
            data['intervals']=intervals
        data['capability_reviews']={};data['approved_role_ids']=[]
        return ps.revise(db,user.id,e,a,data,'pending_review' if a.status!='application_draft' else 'application_draft','application.information_revision')
    return write(db,user,event_id,'application.information:'+application_id,idempotency_key,if_match,body.model_dump(mode='json'),apply)
class AlternativeRequest(StrictModel):
    role_id:str
    work_ids:list[str]=Field(min_length=1,max_length=50)
    message:str=Field(min_length=1,max_length=2000)
class AlternativeResponse(StrictModel):decision:str
@router.post('/events/{event_id}/applications/{application_id}/alternatives')
def alternative_request(event_id:str,application_id:str,body:AlternativeRequest,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        a=ps.app_for(db,e,application_id,user.id,True);release=ps.published(db,e,user.id,True);role=next((r for r in release.snapshot['plan']['roles'] if r['id']==body.role_id),None)
        ps.require_state(role is not None and not(set(body.work_ids)-set(role['work_ids'])),'Choose published alternative work')
        data=deepcopy(a.content);data['alternatives'].append({'id':__import__('uuid').uuid4().hex,'role_requirement_id':body.role_id,'role_title':role['title'],'work_ids':body.work_ids,'message':body.message,'status':'pending','plan_id':release.plan_id})
        return ps.revise(db,user.id,e,a,data,operation='application.alternative_request')
    return write(db,user,event_id,'application.alternative:'+application_id,idempotency_key,if_match,body.model_dump(),apply,True)
@router.post('/events/{event_id}/applications/{application_id}/alternatives/{alternative_id}/response')
def alternative_response(event_id:str,application_id:str,alternative_id:str,body:AlternativeResponse,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        a=ps.app_for(db,e,application_id,user.id);data=deepcopy(a.content);alt=next((x for x in data['alternatives'] if x['id']==alternative_id),None)
        if not alt:missing()
        ps.require_state(alt['status']=='pending' and alt['plan_id']==ps.published(db,e,user.id,True).plan_id and body.decision in ('agree','decline'),'Review current alternative request')
        alt['status']='agreed' if body.decision=='agree' else 'declined'
        if body.decision=='agree':
            data['role_ids']=list(dict.fromkeys(data['role_ids']+[alt['role_requirement_id']]));a.plan_id=alt['plan_id'];data['capability_reviews']={};data['approved_role_ids']=[]
        return ps.revise(db,user.id,e,a,data,'pending_review','application.alternative_response')
    return write(db,user,event_id,'application.alternative.response:'+alternative_id,idempotency_key,if_match,body.model_dump(),apply)

class OrganizationOffer(SupportDraft):event_id:str
@router.get('/organizations/{organization_id}/sponsor-portal')
def explicit_portal(organization_id:str,user=USER,db=DB):
    ss.member(db,user.id,organization_id);return ok(sp.portal(db,user.id,organization_id))
@router.patch('/organizations/{organization_id}/registration')
def organization_edit(organization_id:str,body:OrganizationDraft,user=USER,db=DB,idempotency_key:str=Header()):
    if body.organization_id and body.organization_id!=organization_id:missing()
    ss.member(db,user.id,organization_id);body=body.model_copy(update={'organization_id':organization_id})
    return ok(execute_once(db,user.id,organization_id,'organization.profile',idempotency_key,body.model_dump(),lambda:ss.save_organization(db,user.id,body)))
@router.post('/organizations/{organization_id}/offers')
def organization_offer(organization_id:str,body:OrganizationOffer,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    ss.member(db,user.id,organization_id)
    if body.organization_id and body.organization_id!=organization_id:missing()
    clean=SupportDraft.model_validate(body.model_dump(exclude={'event_id'})|{'organization_id':organization_id})
    return write(db,user,body.event_id,'support.draft',idempotency_key,if_match,body.model_dump(mode='json'),lambda e:ss.save_offer(db,user.id,e,clean))
@router.post('/organizations/{organization_id}/offers/{offer_id}/submit')
@router.post('/organizations/{organization_id}/offers/{offer_id}/withdraw')
def organization_offer_action(organization_id:str,offer_id:str,body:Empty,request:Request,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    ss.member(db,user.id,organization_id);row=db.get(SupportOffer,offer_id)
    if not row or row.organization_id!=organization_id or row.account_id!=user.id:missing()
    action='submit' if request.url.path.endswith('/submit') else 'withdraw'
    return write(db,user,row.event_id,'support.'+action+':'+offer_id,idempotency_key,if_match,{},lambda e:ss.transition(db,user.id,e,ss.own_offer(db,user.id,e,offer_id),action))
@router.post('/organizations/{organization_id}/offers/{offer_id}/fulfillment-reports')
def organization_report(organization_id:str,offer_id:str,body:Fulfillment,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    ss.member(db,user.id,organization_id);row=db.get(SupportOffer,offer_id)
    if not row or row.organization_id!=organization_id or row.account_id!=user.id:missing()
    return write(db,user,row.event_id,'support.report:'+offer_id,idempotency_key,if_match,body.model_dump(mode='json'),lambda e:ss.report(db,user.id,e,ss.own_offer(db,user.id,e,offer_id),body))

@router.get('/events/{event_id}/organizer/dashboard')
def dashboard(event_id:str,user=USER,db=DB):
    from app.shared.models import AuditEvent
    from app.participation.models import OperationalSource
    e=require(db,user.id,event_id,'plan:write');require(db,user.id,e.id,'source:private')
    if not e.current_publication_id:
        from app.events.dto import event_dto
        return ok({'runtime_mode':'http','current_actor_id':user.id,'event':event_dto(e),'revision':e.version,'active_plan_id':e.active_plan_id,'candidate_plan_id':None,'resources':[],'notes':[],'resource_requests':[],'updates':[],'meetings':[],'actions':[],'accounts':[],'blockers':[],'alternatives':[],'blocker_scenario':None,'audit':[{'id':a.id,'operation':a.operation,'sequence':i+1} for i,a in enumerate(db.scalars(select(AuditEvent).where(AuditEvent.event_id==e.id).order_by(AuditEvent.created_at)))],'profile_settings':{},'investigation':None,'candidate':None,'unavailable_modules':['publication_required']},e)
    people=pp.organizer_participants(db,user.id,e)
    from app.execution.projections import communications,state
    com=communications(db,user.id,e);ex=state(db,user.id,e)
    requests=[{'id':r.aggregate_id,**r.content,'status':'open'} for r in db.scalars(select(OperationalSource).where(OperationalSource.event_id==e.id,OperationalSource.kind=='resource.request'))]
    return ok({'runtime_mode':'http','current_actor_id':user.id,'event':people['event'],'revision':e.version,'active_plan_id':e.active_plan_id,'candidate_plan_id':None,'resources':rs.projection(db,e,user.id),'notes':[x for x in com if x['kind']=='note'],'resource_requests':requests,'updates':[x for x in com if x['kind']=='announcement'],'meetings':[x for x in com if x['kind']=='meeting'],'actions':[{**x,'meeting_id':x['parent_id'],'human_approval_status':x.get('human_approval_status','pending')} for x in com if x['kind']=='action'],'accounts':[{'id':a['account_id'],'label':a['applicant_label']} for a in people['applications']],'blockers':[{**x,'initial_facts':{},'investigation_questions':[],'ai_response':'No live AI investigation','outcome':None} for x in ex['blockers']],'alternatives':[],'blocker_scenario':None,'audit':[{'id':a.id,'operation':a.operation,'sequence':i+1} for i,a in enumerate(db.scalars(select(AuditEvent).where(AuditEvent.event_id==e.id).order_by(AuditEvent.created_at)))],'profile_settings':{},'investigation':None,'candidate':None,'unavailable_modules':['blocker_recovery']},e)
class ResourceRequest(Reservation):
    reason:str=Field(min_length=1,max_length=2000)
@router.post('/events/{event_id}/resource-requests')
def resource_request(event_id:str,body:ResourceRequest,user=USER,db=DB,if_match:str=Header(),idempotency_key:str=Header()):
    def apply(e):
        release=ps.published(db,e,user.id,True);ps.require_state(body.expected_plan_id==release.plan_id,'Request against current published plan');work=next((w for w in release.snapshot['plan']['work'] if w['id']==body.work_id),None);ps.require_state(work is not None and body.resource_id in work['resource_requirement_ids'],'Request must reference work-linked resources');r=rs.find_resource(db,e,body.resource_id,user.id);ps.require_state(r['unit']==body.unit,'Exact requirement units required');id=__import__('uuid').uuid4().hex
        ps.source(db,user.id,e,id,'resource.request',{'resource_id':r['id'],'quantity':float(body.quantity),'unit':body.unit,'reason':body.reason});e.version+=1;return {'request_id':id}
    return write(db,user,event_id,'resource.request',idempotency_key,if_match,body.model_dump(mode='json'),apply,True)
