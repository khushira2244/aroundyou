import json
from sqlalchemy import select
from pydantic import Field
from app.memory.schemas import StrictModel
from app.participation.models import Application,Assignment
from app.participation.service import published,app_for,require_state,application_dto,assignment_dto
from app.shared.types import digest
from app.api.errors import DomainError
class Match(StrictModel):
    role_id:str
    work_ids:list[str]=Field(max_length=50)
    supporting_statements:list[str]=Field(default_factory=list,max_length=20)
    explanation:str=Field(min_length=1,max_length=2000)
    missing_information:list[str]=Field(default_factory=list,max_length=20)
    trade_offs:list[str]=Field(default_factory=list,max_length=20)
class ResourceAdvice(StrictModel):
    resource_id:str
    explanation:str=Field(min_length=1,max_length=2000)
    unknowns:list[str]=Field(default_factory=list,max_length=20)
class ParticipationAdvice(StrictModel):
    applicant_understanding:list[str]=Field(default_factory=list,max_length=20)
    unknowns:list[str]=Field(default_factory=list,max_length=20)
    clarification_questions:list[str]=Field(default_factory=list,max_length=20)
    recommendations:list[Match]=Field(default_factory=list,max_length=50)
    resource_advice:list[ResourceAdvice]=Field(default_factory=list,max_length=50)
    coverage_explanation:str=Field(default='',max_length=4000)

def context(session,actor,event,application_id=None):
    release=published(session,event,actor,True)
    from app.resources.service import projection
    from app.governance.service import state
    a=app_for(session,event,application_id,actor,True) if application_id else None
    if a:require_state(a.status in ('submitted','pending_review','approved'),'Assess only submitted applicant information')
    assignments=list(session.scalars(select(Assignment).where(Assignment.event_id==event.id)))
    other=[]
    if a:other=[{'id':x.id,'version':x.version,'status':x.status,'terms':x.current_terms_id} for x in session.scalars(select(Assignment).where(Assignment.account_id==a.account_id,Assignment.event_id!=event.id))]
    app={'id':a.id,'version':a.version,'revision':a.sequence,'reported_answers':a.content['answers'],'availability':a.content['intervals'],'requested_roles':a.content['role_ids'],'clarifications':a.content['clarifications'],'capability_reviews':a.content['capability_reviews'],'other_event_assignment_state_digest':digest(other)} if a else None
    return {'scope':{'application_id':application_id},'published_plan_id':release.plan_id,'published_plan':release.snapshot['plan'],'organizer_conditions':release.snapshot['configuration']['communications']['participant_instructions'],'applicant':app,'assignments':[assignment_dto(session,x) for x in assignments],'resources':projection(session,event,actor),'governance':state(session,event)['guidance'],'governance_advice':state(session,event)['items'],'notice':'Self-reported answers, reviewed requirements, inferred suggestions and verified resource receipts are distinct. No automatic consent, skills, legal approval or outcomes.'}

def validate_context(session,actor,event,built):
    current=context(session,actor,event,built['scope']['application_id'])
    if digest(current)!=digest(built):raise DomainError('stale_proposal','Participation/resource source state changed')

def validate_output(result,authoritative):
    data=ParticipationAdvice.model_validate(result).model_dump();ctx=authoritative['participation_and_resources'];roles={r['id']:r for r in ctx['published_plan']['roles']};resources={r['id'] for r in ctx['resources']};reported=json.dumps(ctx.get('applicant'),ensure_ascii=False)
    for match in data['recommendations']:
        if match['role_id'] not in roles or set(match['work_ids'])-set(roles[match['role_id']]['work_ids']):raise DomainError('invalid_model_output','Recommendation references unsupported work/role',422)
        if any(x not in reported for x in match['supporting_statements']):raise DomainError('invalid_model_output','Cited participant statements must come from supplied answers',422)
    if any(x['resource_id'] not in resources for x in data['resource_advice']):raise DomainError('invalid_model_output','Unknown resource in advisory response',422)
    return data


def intelligence(session,event,a):
    from app.ai.models import AIProposal,AIRun
    from app.ai.context_builder import MuseSparkContextBuilder
    from app.participation.schemas import Offer
    from app.participation.service import candidate_check
    rows=list(session.scalars(select(AIProposal).join(AIRun,AIProposal.run_id==AIRun.id).where(AIProposal.event_id==event.id,AIProposal.kind=='participation').order_by(AIRun.created_at.desc())))
    rows=[p for p in rows if session.get(AIRun,p.run_id).context_manifest['authoritative_current']['participation_and_resources']['scope']['application_id']==a.id and p.status!='rejected']
    if not rows:return {'status':'not_assessed','assessment':None,'history':[],'alternatives':a.content.get('alternatives',[]),'clarifications':a.content['clarifications']}
    p=rows[0];run=session.get(AIRun,p.run_id);fresh=True
    try:
        validate_context(session,run.requester_id,event,run.context_manifest['authoritative_current']['participation_and_resources']);MuseSparkContextBuilder().validate_memories(session,run.requester_id,event.id,run.context_manifest)
    except DomainError:fresh=False
    plan=published(session,event,run.requester_id).snapshot['plan'];roles={r['id']:r for r in plan['roles']};work={w['id']:w for w in plan['work']};recommendations=[]
    for i,m in enumerate(p.payload['recommendations']):
        role=roles.get(m['role_id'])
        if not role:continue
        checks={wid:candidate_check(session,event,a,Offer(role_id=role['id'],work_ids=[wid],schedule=work[wid]['schedule'],expected_plan_id=a.plan_id)) for wid in m['work_ids'] if wid in work} if fresh else {}
        compatible=[w for w,c in checks.items() if not c['conflicts']]
        from app.participation.projections import accepted
        count=sum(session.get(__import__('app.participation.models',fromlist=['AssignmentTerms']).AssignmentTerms,x.current_terms_id).content['role_requirement_id']==role['id'] for x in accepted(session,event))
        recommendations.append({'id':p.id+':'+str(i),'application_id':a.id,'participant_id':a.account_id,'event_id':event.id,'plan_id':a.plan_id,'role_requirement_id':role['id'],'role_title':role['title'],'work_ids':m['work_ids'],'stage_ids':role['stage_ids'],'category':'requested_role_match' if role['id'] in a.content['role_ids'] else 'alternative_suggestion','supporting_statements':m['supporting_statements'],'required_capabilities':role['required_capabilities'],'relevant_capabilities':[],'interpreted_interests':p.payload['applicant_understanding'],'leadership_willingness':'self_reported_only','availability':{'status':'deterministic_check_required','compatible_work_ids':compatible,'conflicting_work_ids':[w for w in checks if w not in compatible]},'capacity':{'status':'unknown' if role['proposed_headcount'] is None else 'full' if count>=role['proposed_headcount'] else 'open','required':role['proposed_headcount'],'accepted':count},'missing_qualifications':m['missing_information'],'dependency_conflicts':[],'limitations_conflict':None if a.content['answers'].get('limitations') and not a.content['capability_reviews'].get(role['id']) else False,'recommendable':fresh and p.status=='approved','offerable_work_ids':compatible if fresh and p.status=='approved' else [],'explanation':m['explanation'],'uncertainty':'; '.join(p.payload['unknowns']+m['trade_offs']),'human_review_required':True,'provenance':{**p.provenance,'simulation':not p.provenance['model_execution']}})
    return {'status':'current' if fresh else 'stale','assessment':{'id':p.id,'version':len(rows),'plan_id':a.plan_id,'recommendations':recommendations,'questions':p.payload['clarification_questions'],'review_status':p.status,'digest':p.digest},'history':[{'id':x.id,'version':i+1,'plan_id':a.plan_id} for i,x in enumerate(reversed(rows))],'alternatives':a.content.get('alternatives',[]),'clarifications':a.content['clarifications']}
