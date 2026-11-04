from app.execution.service import *
from app.execution.models import CoordinationRecord,WorkIssue

def participant(db,actor,e):
    return any(effective_assignment(db,a)=='assignment_accepted' for a in db.scalars(select(Assignment).where(Assignment.event_id==e.id,Assignment.account_id==actor)))
def visible(db,actor,e,row):
    d=row.content
    if owner(db,actor,e):return True
    if row.kind=='meeting':return actor in d['invited_account_ids']
    if row.kind in ('decision','action'):
        parent=db.get(CoordinationRecord,d['parent_id']);return bool(parent and visible(db,actor,e,parent))
    if d['status']=='draft':return row.account_id==actor
    return d['audience']=='public' or d['audience']=='participants' and participant(db,actor,e)
def create(db,actor,e,b):
    published(db,e,actor,True);p=plan(db,e,actor);isowner=owner(db,actor,e)
    if not isowner:
        require_state(participant(db,actor,e) and b.kind in ('discussion','note') and b.audience!='internal','Only organizers create announcements, meetings, decisions or internal messages')
    require_state(not(set(b.stage_ids)-{x['id'] for x in p['stages']}) and not(set(b.work_ids)-{x['id'] for x in p['work']}),'Unknown stage/work reference')
    for aid in b.invited_account_ids:
        require_state(aid==e.creator_id or participant(db,aid,e),'Invite only actual accepted participants or organizer')
    if b.kind=='discussion' and b.parent_id:
        parent=db.get(CoordinationRecord,b.parent_id);require_state(parent and parent.event_id==e.id and parent.kind=='discussion' and visible(db,actor,e,parent) and parent.content['audience']==b.audience,'Reply must preserve the authorized thread audience')
    if b.kind in ('decision','action'):
        parent=db.get(CoordinationRecord,b.parent_id)
        require_state(parent and parent.event_id==e.id and parent.kind=='meeting','Meeting association required')
        require_state(b.status!='completed','Meeting action requires a separate human approval transition')
    if b.kind=='meeting':require_state(b.schedule is not None,'Meeting schedule required')
    d=b.model_dump(mode='json');d.update(rsvp={},conducted=False,invitation_delivery='not_sent',created_at=now().isoformat(),sequence=1,proposed_schedule=d.pop('schedule'),confirmed_schedule=None,purpose=b.body,stage_ids=b.stage_ids,work_ids=b.work_ids)
    row=CoordinationRecord(id=uid(),event_id=e.id,account_id=actor,kind=b.kind,content={});db.add(row);db.flush();record(db,actor,e,row,'coordination.create',d)
    return {'record':dto(row)}
def update(db,actor,e,rid,b):
    row=db.get(CoordinationRecord,rid)
    if not row or row.event_id!=e.id or not visible(db,actor,e,row):missing()
    require_state(row.version==b.expected_revision,'Review current coordination revision');d=deepcopy(row.content)
    if b.action=='rsvp':
        require_state(row.kind=='meeting' and actor in d['invited_account_ids'],'Only invited participant may RSVP');d['rsvp']={**d['rsvp'],actor:b.response}
    else:
        if not owner(db,actor,e):missing()
        if b.action=='revise_invitees':
            require_state(row.kind=='meeting' and d['status'] in ('draft','proposed'),'Revise invitees before confirmation')
            require_state(all(aid==e.creator_id or participant(db,aid,e) for aid in b.invited_account_ids),'Invite only actual accepted participants or organizer')
            d['invited_account_ids']=b.invited_account_ids
        elif b.action=='confirm':require_state(row.kind=='meeting' and d['status']!='cancelled','Confirm current meeting');d['confirmed_schedule']=d['proposed_schedule'];d['status']='scheduled'
        elif b.action=='publish':require_state(row.kind in ('announcement','discussion','note') and d['status']=='draft','Publish draft communication');d['status']='published'
        elif b.action=='approve_action':require_state(row.kind=='action' and b.note and d['status'] in ('open','draft'),'Approve exact proposed follow-up');d['status']='approved';d['human_approval_status']='approved';d['approval_note']=b.note
        elif b.action=='complete_action':require_state(row.kind=='action' and b.note and d['status']=='approved','Record human follow-up approval with reason');d['status']='completed';d['human_approval_status']='approved';d['completion_note']=b.note
        else:d['status']='cancelled'
    record(db,actor,e,row,'coordination.'+b.action,d,'verified' if b.action=='complete_action' else 'attempted','inconclusive',b.note or None);return {'record':dto(row)}
def dto(row):return {'id':row.id,'revision':row.version,'kind':row.kind,**row.content,'status':'proposed' if row.kind=='meeting' and row.content['status']=='draft' else 'suggested' if row.kind=='action' and row.content['status']=='open' else row.content['status']}
def issue(db,actor,e,b):
    published(db,e,actor,True)
    w=work(db,e,actor,b.work_id)
    for wid in b.affected_work_ids:
        candidate=work(db,e,actor,wid)
        if not reviewer(db,actor,e,candidate):assignment(db,actor,e,wid)
    if b.resource_count:
        from pydantic import BaseModel,ConfigDict,Field
        class Count(BaseModel):
            model_config=ConfigDict(extra='forbid')
            resource_id:str
            required:float|None=Field(default=None,ge=0,allow_inf_nan=False)
            available:float|None=Field(default=None,ge=0,allow_inf_nan=False)
            unit:str
            source:str=Field(min_length=1,max_length=500)
        count=Count.model_validate(b.resource_count)
        resource=next((r for r in plan(db,e,actor)['resources'] if r['id']==count.resource_id),None)
        require_state(resource and count.resource_id in w['resource_requirement_ids'] and count.unit==resource['unit'],'Count must reference actual work resource and exact unit')
    require_state(not(set(b.resource_ids)-set(w['resource_requirement_ids'])),'Issue resources must belong to affected work')
    if not reviewer(db,actor,e,w):assignment(db,actor,e,w['id'])
    from app.execution.evidence import get
    for aid in b.evidence_ids:
        asset=get(db,actor,e,aid);r=db.get(WorkReport,asset.report_id);require_state(r.work_id==w['id'],'Issue evidence must match affected work')
    row=WorkIssue(id=uid(),event_id=e.id,plan_id=e.active_plan_id,account_id=actor,work_id=w['id'],content={});db.add(row);db.flush()
    d={**b.model_dump(),'work_ids':list(dict.fromkeys([w['id'],*b.affected_work_ids])),'stage_id':w['stage_id'],'resolution_status':'reported','investigation_status':'reported','condition_cleared':False,'blocking':False,'protective_hold':b.severity in ('unsafe','impossible') or b.can_continue is False,'private_personal':b.category in ('personal_unavailability','assignment_conflict'),'recorded_at':now().isoformat(),'source_type':'participant_entry','history':[]}
    record(db,actor,e,row,'issue.report',d);return {'blocker':{'id':row.id,'revision':row.version,**row.content}}
def review_issue(db,actor,e,rid,b):
    row=db.get(WorkIssue,rid)
    if not row or row.event_id!=e.id:missing()
    w=work(db,e,actor,row.work_id)
    if not reviewer(db,actor,e,w):missing()
    require_state(row.version==b.expected_revision,'Review current issue revision')
    transitions={'reported':{'acknowledged','nonblocking'},'acknowledged':{'investigating','nonblocking'},'investigating':{'resolved','closed','nonblocking'},'nonblocking':{'investigating','closed'},'resolved':{'investigating','closed'},'closed':{'investigating'}}
    require_state(b.state in transitions[row.content['investigation_status']],'Invalid issue handling transition')
    require_state(not b.condition_cleared or b.state in ('resolved','closed'),'Clear condition only with recorded resolution evidence')
    d={**row.content,'investigation_status':b.state,'resolution_status':b.state,'condition_cleared':b.condition_cleared,'history':row.content['history']+[{'actor_id':actor,'at':now().isoformat(),'note':b.note,'state':b.state,'condition_cleared':b.condition_cleared}]}
    d.pop('confirmed_blocking_condition',None)  # Any subsequent issue review requires renewed exact-source confirmation.
    d['blocking']=False
    if b.state=='nonblocking':d['protective_hold']=False
    record(db,actor,e,row,'issue.review',d,'verified' if b.condition_cleared else 'attempted','inconclusive',b.note)
    return {'blocker':{'id':row.id,'revision':row.version,**row.content}}
