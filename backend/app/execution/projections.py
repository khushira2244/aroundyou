from app.execution.service import *
from app.execution.evidence import dto as evidence_dto
from app.execution.coordination import visible,dto,participant
from app.resources.service import projection as resource_projection
from app.resources.models import ResourceReservation
from app.execution.ledger import amounts

def state(db,actor,e):
    p=plan(db,e,actor);isowner=owner(db,actor,e);works=[];review_stages=set();permitted=set()
    for w in p['work']:
        can_report=False
        try:assignment(db,actor,e,w['id']);can_report=True
        except DomainError:pass
        can_review=reviewer(db,actor,e,w)
        if can_review:review_stages.add(w['stage_id'])
        if not(can_report or can_review):continue
        permitted.add(w['id']);row=execution(db,e,w['id']);r=readiness(db,e,actor,w);data=row.content if row else {}
        status=data.get('status','ready' if r['ready'] and not r['preconditions'] else 'not_started')
        if r['blocking_issue_ids']:status='blocked'
        elif r['unverified_dependencies'] and status!='completed':status='blocked'
        works.append({**w,'execution_status':status,'can_report':can_report,'can_review':can_review,'verified_percent':data.get('verified_percent',0),'reported_percent':data.get('reported_percent'),'actual_started_at':data.get('started_at'),'actual_completed_at':data.get('completed_at'),'readiness':r})
    reports=[];assets=[]
    for r in db.scalars(select(WorkReport).where(WorkReport.event_id==e.id)):
        if r.account_id==actor or r.content['review_status']!='draft' and (isowner or r.work_id in permitted and reviewer(db,actor,e,report_work(db,r))):
            reports.append(report_dto(db,actor,e,r));assets.extend(evidence_dto(x) for x in db.scalars(select(EvidenceAsset).where(EvidenceAsset.report_id==r.id)))
    stages=[]
    for st in p['stages']:
        ws=[w for w in works if w['stage_id']==st['id']];allws=[w for w in p['work'] if w['stage_id']==st['id']]
        if not ws:continue
        full=len(ws)==len(allws);stage_done=any(x.content['plan_id']==e.active_plan_id and x.content['stage_id']==st['id'] and all(execution(db,e,k) and execution(db,e,k).version==v and execution(db,e,k).content['status']=='completed' for k,v in x.content['work_versions'].items()) for x in db.scalars(select(CoordinationRecord).where(CoordinationRecord.event_id==e.id,CoordinationRecord.kind=='stage_completion')));known=full and all(w['effort']['value'] is not None and w['effort']['unit']=='person_hours' for w in ws);weight=sum(w['effort']['value'] for w in ws) if known else 0
        stages.append({'id':st['id'],'title':st['title'],'status':'completed' if stage_done else 'ready_for_completion' if full and all(w['execution_status']=='completed' for w in ws) else 'in_progress' if any(w['verified_percent'] or w['execution_status']!='not_started' for w in ws) else 'not_started','can_complete':not stage_done and isowner and full and all(w['execution_status']=='completed' for w in ws),'verified_progress_percent':sum(w['verified_percent']*w['effort']['value'] for w in ws)/weight if known and weight else None,'progress_basis':'confirmed_effort_weight' if known and weight else 'unknown_or_partial_scope','completed_work_count':sum(w['execution_status']=='completed' for w in ws),'total_work_count':len(allws)})
    reservations=[]
    if isowner:
        for r in db.scalars(select(ResourceReservation).where(ResourceReservation.event_id==e.id)):
            c,i,t=amounts(db,e,reservation_id=r.id);reservations.append({'id':r.id,'stock_id':r.resource_id,'resource_id':r.resource_id,'work_ids':[r.work_id],'remaining':float(Decimal(r.quantity)-c-i+t),'status':r.status})
    loans=[{'id':o.id,'report_id':o.report_id,'usage_id':o.usage_id,'quantity':float(o.quantity),'returned':float(sum((x.quantity for x in db.scalars(select(ResourceOperation).where(ResourceOperation.reservation_id==o.reservation_id,ResourceOperation.report_id==o.report_id,ResourceOperation.usage_id==o.usage_id,ResourceOperation.kind=='return'))),Decimal(0))),'reservation_id':o.reservation_id} for o in db.scalars(select(ResourceOperation).where(ResourceOperation.event_id==e.id,ResourceOperation.kind=='checkout')) if isowner or o.report_id in {r['id'] for r in reports}]
    issues=[{'id':i.id,'revision':i.version,**i.content} for i in db.scalars(select(WorkIssue).where(WorkIssue.event_id==e.id)) if isowner or i.account_id==actor or (not i.content.get('private_personal') and i.work_id in permitted)]
    # Participants see requirement quantities only, never private sponsor/receipt metadata.
    resources=resource_projection(db,e,actor) if isowner else [{**r,'sources':[],'transactions':[]} for r in p['resources']]
    return {'storage_mode':'private_backend','event_id':e.id,'viewer':{'account_id':actor,'is_organizer':isowner,'review_stage_ids':sorted(review_stages)},'plan_id':e.active_plan_id,'work':works,'stages':stages,'attendance':[{'id':a.id,'assignment_id':a.assignment_id,'account_id':a.account_id,'revision':a.version,**a.content} for a in db.scalars(select(AttendanceRecord).where(AttendanceRecord.event_id==e.id)) if isowner or a.account_id==actor],'reports':reports,'evidence':assets,'resources':resources,'reservations':reservations,'loans':loans,'blockers':issues,'analysis_provider':{'configured':False,'status':'provider_unavailable','message':'No live model or transcription configured; human review remains authoritative'}}

def communications(db,actor,e,kind=None):
    return [dto(x) for x in db.scalars(select(CoordinationRecord).where(CoordinationRecord.event_id==e.id).order_by(CoordinationRecord.id)) if x.kind in ('announcement','note','discussion','meeting','decision','action') and (kind is None or x.kind==kind) and visible(db,actor,e,x)]

def public_progress(db,e):
    p=published(db,e,e.creator_id).snapshot['plan'];completed=0;verified=0;weights=[]
    current={x.work_id:x for x in db.scalars(select(WorkExecution).where(WorkExecution.event_id==e.id,WorkExecution.plan_id==e.active_plan_id))}
    for w in p['work']:
        row=current.get(w['id']);percent=row.content.get('verified_percent',0) if row else 0
        completed+=bool(row and row.content['status']=='completed');verified+=percent
        if w['effort']['value'] is not None and w['effort']['unit']=='person_hours':weights.append((w['effort']['value'],percent))
    weight=sum(x for x,y in weights)
    return {'completed_work_count':completed,'total_work_count':len(p['work']),'verified_progress_percent':sum(x*y for x,y in weights)/weight if len(weights)==len(p['work']) and weight else None,'weight_basis':'confirmed_person_hours' if len(weights)==len(p['work']) and weight else 'unknown','impact_measurements':None}


def augment_public(db,e,result):
    result['progress']=public_progress(db,e)
    rows=list(db.scalars(select(CoordinationRecord).where(CoordinationRecord.event_id==e.id).order_by(CoordinationRecord.id)))
    result['updates']=[dto(r) for r in rows if r.kind=='announcement' and r.content['audience']=='public' and r.content['status']=='published']
    from app.access.models import User
    discussions=[r for r in rows if r.kind=='discussion' and r.content['audience']=='public' and r.content['status']=='published']
    result['discussions']=[{**dto(r),'author_label':db.get(User,r.account_id).display_name,'replies':[{'id':x.id,'body':x.content['body'],'author_label':db.get(User,x.account_id).display_name} for x in discussions if x.content['parent_id']==r.id]} for r in discussions if not r.content['parent_id']]
    result['updates']=[{**x,'author_label':'Event organizer'} for x in result['updates']]
    measurements={}
    for r in rows:
        if r.kind!='measurement' or r.content.get('status')!='verified':continue
        report=db.get(WorkReport,r.content['report_id'])
        if not report or report.version!=r.content['report_revision'] or report.content['review_status']!='accepted':continue
        m=r.content
        measurements[(report.id,report.version,m['metric'])]={'id':r.id,'qualification':'Explicit human-verified measured value; not inferred from task count','metric':m['metric'],'value':m['value'],'unit':m['unit'],'source_report_id':report.id,'source_revision':report.version}
        units={'waste_collected_kg':'kg','waste_handed_over_kg':'kg','area_improved_hectares':'ha','cleanup_zones_completed':'zones','assessment_sections':'stair_sections'}
    result['impact']['verified_outputs']=list(measurements.values())
    for metric,unit in units.items() if measurements else []:
        values=[m for m in measurements.values() if m['metric']==metric and m['unit']==unit]
        if len(values)==1:result['impact'][metric]=values[0]['value']
        # Multiple source measurements are not silently summed or selected as an event total.
    for st in result['stages']:
        ws=[w for w in plan(db,e,e.creator_id)['work'] if w['stage_id']==st['id']]
        complete=any(r.kind=='stage_completion' and r.content['stage_id']==st['id'] and r.content['plan_id']==e.active_plan_id and all(execution(db,e,wid) and execution(db,e,wid).version==v and execution(db,e,wid).content['status']=='completed' for wid,v in r.content['work_versions'].items()) for r in rows)
        st['execution_status']='completed' if complete else 'planned'
    return result
