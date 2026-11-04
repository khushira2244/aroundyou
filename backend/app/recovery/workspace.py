"""Resumable organizer reviews on the existing coordination/recovery aggregates."""
from copy import deepcopy
from typing import Literal
from pydantic import Field
from sqlalchemy import select
from app.memory.schemas import StrictModel,SourceRef
from app.execution.models import CoordinationRecord,WorkIssue,ExecutionRevision,WorkReport,ExecutionReviewGrant
from app.execution.service import record,require_state
from app.events.models import Event
from app.planning.models import PlanVersion
from app.planning.schemas import PlanContent
from app.participation.models import Assignment,AssignmentTerms
from app.participation.service import effective_assignment
from app.recovery.service import impact
from app.recovery.lifecycle import fingerprint
from app.shared.types import uid,digest
from app.api.errors import missing,DomainError

FIELDS={'stage':('stages',{'relative_start','relative_end','purpose','intended_outcomes','dependency_ids'}),'work':('work',{'scope','outcome','schedule','effort','volume','dependency_ids','conditions','evidence_requirements','skills','resource_requirement_ids'}),'resource':('resources',{'quantity','title'}),'actor':('roles',{'proposed_headcount','required_capabilities','responsibilities','safety_considerations','headcount_basis'})}
def scope_nodes(plan,scope):
    affected=set(scope['affected_work_ids'])-set(scope['preserved_complete_ids'])
    return {**{'stage:'+s['id']:s for s in plan['stages'] if any(w['id'] in affected and w['stage_id']==s['id'] for w in plan['work'])},**{'work:'+w['id']:w for w in plan['work'] if w['id'] in affected},**{'resource:'+r['id']:r for r in plan['resources'] if set(r['work_ids'])&affected},**{'actor:'+r['id']:r for r in plan['roles'] if set(r['work_ids'])&affected}}
def apply_patches(content,patches,scope,local=False):
    nodes=scope_nodes(content,scope);changed=[]
    for key,patch in patches.items():
        require_state(key in nodes,'Only scoped existing unfinished nodes may change')
        kind=key.split(':',1)[0];_,allowed=FIELDS[kind];require_state(set(patch)<=allowed,'Unsupported recovery field; never inventory, permissions, identifiers or verification')
        row=nodes[key];before=deepcopy(row);row.update(deepcopy(patch))
        if patch and kind in ('resource','actor'):
            require_state(set(row['work_ids'])<=set(scope['affected_work_ids']),'Shared resource/actor changes require confirmation and review of every linked work unit')
        if row!=before:
            if kind=='work':row['revision']+=1
            changed.append(key)
        from app.planning.schemas import Stage,Work,Resource,ActorRequirement,Schedule
        if kind=='stage' and row['duration']['value'] is not None:row['duration']['value']=row['relative_end']-row['relative_start']+1
        if kind=='work' and row['duration']['value'] is not None:
            sch=Schedule.model_validate(row['schedule']);row['duration']['value']=(sch.finish-sch.start)/60
        {'stage':Stage,'work':Work,'resource':Resource,'actor':ActorRequirement}[kind].model_validate(row)
    if not local:PlanContent.model_validate(content)
    return changed
class Open(StrictModel):
    issue_ids:list[str]=Field(min_length=1,max_length=30)
    expected_plan_id:str
class LocalReview(StrictModel):
    expected_revision:int
    node_key:str
    patch:dict=Field(default_factory=dict)
    status:Literal['draft_change','confirmed_local_change','reviewed_no_change']
    note:str=Field(min_length=1,max_length=2000)
class Finalize(StrictModel):
    expected_revision:int
    title:str=Field(min_length=1,max_length=200)
    rationale:str=Field(min_length=1,max_length=2000)
class Communication(StrictModel):
    expected_revision:int
    mode:Literal['none','targeted','meeting']
    message:str=Field(default='Operational recovery review; check your current work and any revised offers.',max_length=2000)
    invited_account_ids:list[str]=Field(default_factory=list,max_length=100)
    schedule:dict|None=None
    agenda:list[str]=Field(default_factory=list,max_length=30)
class Outcome(StrictModel):
    expected_revision:int
    outcome:Literal['successful','mixed','failed','inconclusive']
    criteria:str=Field(min_length=8,max_length=2000)
    report_ids:list[str]=Field(min_length=1,max_length=30)

def get(db,e,rid):
    row=db.get(CoordinationRecord,rid)
    if not row or row.event_id!=e.id or row.kind!='recovery_workspace':missing()
    return row

def people(db,e,affected):
    p=db.get(PlanVersion,e.active_plan_id).content;recipients=[]
    for a in db.scalars(select(Assignment).where(Assignment.event_id==e.id)):
        if effective_assignment(db,a)!='assignment_accepted':continue
        t=db.get(AssignmentTerms,a.current_terms_id)
        if not set(t.content['work_ids'])&set(affected):continue
        leads=list(db.scalars(select(ExecutionReviewGrant).where(ExecutionReviewGrant.event_id==e.id,ExecutionReviewGrant.account_id==a.account_id,ExecutionReviewGrant.active.is_(True))))
        recipients.append({'account_id':a.account_id,'assignment_id':a.id,'work_ids':t.content['work_ids'],'role_requirement_id':t.content['role_requirement_id'],'classification':'affected_stage_lead' if leads else 'affected_participant','operational_message_only':True})
    from app.sponsorship.models import SupportOffer
    resource_ids={r['id'] for r in p['resources'] if set(r['work_ids'])&set(affected)}
    for offer in db.scalars(select(SupportOffer).where(SupportOffer.event_id==e.id,SupportOffer.status.in_(('accepted','partially_fulfilled','fulfilled','verified')))):
        if offer.content.get('resource_id') in resource_ids:
            recipients.append({'account_id':offer.account_id,'offer_id':offer.id,'resource_id':offer.content['resource_id'],'classification':'affected_resource_sponsor','operational_message_only':True})
    return recipients

def view(db,actor,e,row):
    d=deepcopy(row.content);base=db.get(PlanVersion,d['base_plan_id']).content
    d['stale']=d['base_plan_id']!=e.active_plan_id or fingerprint(db,e,d['issue_ids'])!=d['fingerprint']
    d['people']=people(db,e,d['scope']['affected_work_ids'])
    if d.get('alternative_id'):
        a=db.get(CoordinationRecord,d['alternative_id']);decisions=[]
        if a:
            from app.participation.models import AssignmentConsent
            for aid,terms in a.content.get('reconfirmations',{}).items():
                consent=db.scalar(select(AssignmentConsent).where(AssignmentConsent.terms_id==terms['terms_id']))
                decisions.append({'assignment_id':aid,'account_id':terms['account_id'],'decision':consent.decision if consent else 'pending','status':'reconfirmation_required' if not consent else 'unresolved_staffing' if consent.decision=='decline' else 'commitment_confirmed'})
            d['commitments']=decisions;d['status']='recovery_active' if a.content['status']=='activated' else 'recovery_approved_pending_commitments' if a.content['status'] in ('approved','conditionally_approved') else 'awaiting_overall_approval'
    d['nodes']=[{'key':k,'original':v,'patch':d['reviews'].get(k,{}).get('patch',{}),'status':d['reviews'].get(k,{}).get('status','needs_review')} for k,v in scope_nodes(base,d['scope']).items()]
    return {'id':row.id,'revision':row.version,**d}

def open_workspace(db,actor,e,b):
    scope=impact(db,actor,e,b.issue_ids,b.expected_plan_id)
    row=db.scalar(select(CoordinationRecord).where(CoordinationRecord.event_id==e.id,CoordinationRecord.kind=='recovery_workspace',CoordinationRecord.content['issue_ids']==b.issue_ids,CoordinationRecord.content['base_plan_id'].astext==b.expected_plan_id))
    if row:return view(db,actor,e,row)
    row=CoordinationRecord(id=uid(),event_id=e.id,account_id=actor,kind='recovery_workspace',content={});db.add(row);db.flush()
    record(db,actor,e,row,'recovery.workspace_open',{'issue_ids':b.issue_ids,'base_plan_id':e.active_plan_id,'fingerprint':fingerprint(db,e,b.issue_ids),'scope':scope['scope'],'reviews':{},'status':'recovery_planning','audience':'internal','communication':None,'alternative_id':None})
    return view(db,actor,e,row)

def local_review(db,actor,e,rid,b):
    row=get(db,e,rid);d=deepcopy(row.content)
    require_state(row.version==b.expected_revision and not view(db,actor,e,row)['stale'] and not d['alternative_id'],'Review exact current workspace before overall submission')
    plan=deepcopy(db.get(PlanVersion,d['base_plan_id']).content)
    require_state(b.node_key in scope_nodes(plan,d['scope']),'Unknown or unaffected node')
    require_state(b.status!='reviewed_no_change' or not b.patch,'No-change review cannot contain a patch')
    patches={k:r['patch'] for k,r in d['reviews'].items()};patches[b.node_key]=b.patch;apply_patches(plan,patches,d['scope'],local=True)
    d['reviews'][b.node_key]={'patch':b.patch,'status':b.status,'note':b.note,'actor_id':actor}
    from app.recovery.impact import affected_scope
    new=affected_scope(plan,d['scope']['direct_work_ids'],d['scope']['preserved_complete_ids']);d['candidate_impact']=new
    record(db,actor,e,row,'recovery.local_review',d);return view(db,actor,e,row)

def finalize(db,actor,e,rid,b):
    from app.recovery.lifecycle import Alternative,create
    row=get(db,e,rid);d=deepcopy(row.content);v=view(db,actor,e,row)
    require_state(row.version==b.expected_revision and not v['stale'] and not d['alternative_id'],'Finalize current workspace only once')
    require_state(all(n['status'] in ('confirmed_local_change','reviewed_no_change') for n in v['nodes']),'Review stage, work, resource and actor nodes separately before overall approval')
    result=create(db,actor,e,Alternative(issue_ids=d['issue_ids'],expected_plan_id=d['base_plan_id'],title=b.title,rationale=b.rationale,patches={k:r['patch'] for k,r in d['reviews'].items() if r['patch']}))
    d['alternative_id']=result['id'];d['status']='awaiting_overall_approval';record(db,actor,e,row,'recovery.workspace_submit',d);return {'workspace':view(db,actor,e,row),'alternative':result}

def communicate(db,actor,e,rid,b):
    from app.execution.coordination import create
    from app.execution.schemas import Coordination
    row=get(db,e,rid);d=deepcopy(row.content);require_state(row.version==b.expected_revision,'Review current communication decision')
    recipients=sorted({r['account_id'] for r in people(db,e,d['scope']['affected_work_ids'])});permitted=set(recipients)|{e.creator_id}
    require_state(set(b.invited_account_ids)<=permitted,'Only actual affected people or organizer may receive this scoped communication')
    if any(db.get(WorkIssue,i).content.get('private_personal') for i in d['issue_ids']):
        require_state(b.message in ('Operational recovery review; check your current work and any revised offers.','Operational recovery update. Review your current responsibilities and any changed assignment offers.'),'Personal issues permit sanitized operational notices only')
    ids=[]
    if b.mode=='meeting':
        require_state(b.schedule is not None,'Meeting schedule required')
        from app.execution.coordination import participant
        require_state(all(account==e.creator_id or participant(db,account,e) for account in b.invited_account_ids),'Sponsor updates use targeted notices; existing meeting workspace requires organizer or accepted participant')
        meeting=create(db,actor,e,Coordination(kind='meeting',title='Recovery coordination',body=b.message,parent_id=rid,work_ids=d['scope']['affected_work_ids'],invited_account_ids=b.invited_account_ids,schedule=b.schedule,agenda=b.agenda))['record'];ids.append(meeting['id'])
    if b.mode in ('targeted','meeting'):
        for account in b.invited_account_ids:
            notice=CoordinationRecord(id=uid(),event_id=e.id,account_id=actor,kind='recovery_notice',content={});db.add(notice);db.flush()
            record(db,actor,e,notice,'recovery.notice',{'recipient_id':account,'workspace_id':rid,'message':b.message,'status':'unread','audience':'targeted','event_id':e.id,'meeting_id':ids[0] if ids else None})
    d['communication']={'mode':b.mode,'recipient_ids':b.invited_account_ids,'meeting_ids':ids,'confirmed_by':actor};record(db,actor,e,row,'recovery.communication',d);return view(db,actor,e,row)

def outcome(db,actor,e,rid,b):
    from app.recovery.lifecycle import get as alternative
    row=alternative(db,e,rid);require_state(row.version==b.expected_revision and row.content['status']=='activated','Verify outcome only after recovery activation')
    reports=[db.get(WorkReport,i) for i in b.report_ids]
    require_state(all(r and r.event_id==e.id and r.plan_id==e.active_plan_id and r.account_id!=actor and r.content['review_status']=='accepted' for r in reports),'Independent accepted current-plan report sources required')
    require_state(set(row.content['changed_work_ids'])<=set(r.work_id for r in reports),'Every changed work requires an independently reviewed source')
    data_class=e.memory_data_class
    summary={'recovery_id':rid,'changed_work_ids':row.content['changed_work_ids'],'outcome':b.outcome,'criteria':b.criteria,'reports':[{'id':r.id,'revision':r.version} for r in reports],'data_class':data_class,'category':e.category,'actions_attempted':row.content['changed_nodes'] if 'changed_nodes' in row.content else row.content['changed_work_ids']}
    original=db.get(PlanVersion,row.content['base_plan_id']).content;candidate=row.content['plan'];interventions=[]
    for kind,collection,fields in [('stage','stages',('relative_start','relative_end')),('work','work',('schedule','effort')),('resource','resources',('quantity','unit','kind')),('actor','roles',('proposed_headcount',))]:
        for current in candidate[collection]:
            before=next(x for x in original[collection] if x['id']==current['id'])
            a={k:before[k] for k in fields};b_after={k:current[k] for k in fields}
            if a!=b_after:interventions.append({'kind':kind,'before':a,'after':b_after})
    summary['interventions']=interventions;summary['blocker_categories']=sorted({db.get(WorkIssue,i).content['category'] for i in row.content['issue_ids']})
    if b.outcome=='successful':
        from app.execution.models import WorkExecution
        require_state(all((x:=db.scalar(select(WorkExecution).where(WorkExecution.event_id==e.id,WorkExecution.plan_id==e.active_plan_id,WorkExecution.work_id==wid))) and x.content.get('status')=='completed' for wid in row.content['changed_work_ids']),'Successful outcome needs separately completed changed work')
    record_row=CoordinationRecord(id=uid(),event_id=e.id,account_id=actor,kind='recovery_outcome',content={});db.add(record_row);db.flush();record(db,actor,e,record_row,'recovery.outcome',summary,'verified',b.outcome,b.criteria)
    rev=db.scalar(select(ExecutionRevision).where(ExecutionRevision.aggregate_id==record_row.id).order_by(ExecutionRevision.sequence.desc()))
    return {'outcome_id':record_row.id,'outcome':b.outcome,'source_ref':SourceRef(source_kind='execution',source_id=rev.id,source_revision=rev.sequence,source_digest=rev.digest).model_dump(),'memory_eligible':data_class=='real'}
