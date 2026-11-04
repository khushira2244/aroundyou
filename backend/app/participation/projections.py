from collections import Counter
from copy import deepcopy
from sqlalchemy import select
from app.participation.models import Application,Assignment,AssignmentTerms
from app.participation.service import published,application_dto,assignment_dto,effective_assignment
from app.events.models import Event
from app.events.dto import event_dto
from app.access.models import User
from app.access.authorization import allowed,require
from app.publication.models import Publication
from app.api.errors import missing

def accepted(session,event):return [a for a in session.scalars(select(Assignment).where(Assignment.event_id==event.id)) if effective_assignment(session,a)=='assignment_accepted']
def role_view(r):return {**r,'commitment':{'effort_person_hours':r['effort_person_hours'],'schedule_intervals':r['schedule_intervals']},'delegated_permissions':[],'status':'planned_requirement'}

def augment_profile(session,event,profile):
    release=session.get(Publication,event.current_publication_id) if event.current_publication_id else None
    if not release:return profile
    rows=accepted(session,event);ids={a.account_id for a in rows};roles=Counter(session.get(AssignmentTerms,a.current_terms_id).content['role_requirement_id'] for a in rows)
    for r in profile['roles']:
        r['accepted_positions']=roles[r['id']];r['open_positions']=None if r['positions'] is None else max(0,r['positions']-r['accepted_positions'])
    profile['impact']['accepted_participants']=len(ids)
    config=release.snapshot['configuration']['tags'];apps=list(session.scalars(select(Application).where(Application.event_id==event.id)));consented=[a for a in apps if a.account_id in ids and a.content['answers']['participant_insights']['consent']]
    breakdowns=[]
    for key,label in [('age_range','Age Range'),('neighborhood','Neighborhood Distribution'),('experience_level','Experience Level'),('participation_interest','Participation Interests'),('tags','Participant Tags')]:
        enabled=config['collect_insights'] and config['public_aggregates'] and (key=='tags' or config['fields'].get(key,False))
        buckets=Counter()
        labels={x['id']:x['label'] for x in config['custom_tags'] if x['active']}
        for a in consented:
            answer=a.content['answers']['participant_insights']
            values=[labels[x] for x in set(answer['tag_ids']) if x in labels] if key=='tags' else [answer['fields'].get(key,'')]
            buckets.update(x for x in values if x)
        eligible=enabled and len(consented)>=5 and bool(buckets) and min(buckets.values())>=5
        breakdowns.append({'key':key,'label':label,'status':'available' if eligible else 'suppressed' if enabled else 'disabled','reason':'Consented aggregates only' if eligible else 'Minimum five consented accepted people in every displayed category' if enabled else 'Not enabled in the published configuration','buckets':[{'label':name,'count':count,'percent':round(count/len(consented)*100,1)} for name,count in sorted(buckets.items())] if eligible else []})
    profile['insights']={'enabled':config['collect_insights'] and config['public_aggregates'],'status':'available' if any(b['status']=='available' for b in breakdowns) else 'suppressed','reason':'Consented accepted participants; small groups suppressed','total_participants':len(ids),'counts':{'requested':sum(a.status not in ('application_draft','withdrawn') for a in apps),'approved':sum(a.status=='approved' for a in apps),'accepted':len(ids)} if profile['viewer']['is_organizer'] else None,'minimum_group_size':5,'breakdowns':breakdowns,'synthetic':False}
    from app.participation.dynamic_insights import latest,aggregate,configuration
    if latest(session,event.id,'insight.configuration'):
        dynamic=aggregate(session,None,event)
        config2=configuration(session,event)
        keys=['age_range','neighborhood','experience_level','participation_interest','tags']
        profile['insights']['enabled']=config2['public_aggregates']
        profile['insights']['status']=dynamic['status']
        profile['insights']['breakdowns']=[{'key':key,'label':key.replace('_',' ').title(),'status':next((b['status'] for b in dynamic['breakdowns'] if b['dimension']==key),'suppressed'),
            'reason':'Versioned consented aggregates; small buckets and cohort changes suppressed',
            'buckets':[{**v,'percent':0} for b in dynamic['breakdowns'] if b['dimension']==key for v in b['buckets']]} for key in keys]
    from app.sponsorship.models import SupportOffer,Organization
    from app.sponsorship.service import offer_dto
    for offer in session.scalars(select(SupportOffer).where(SupportOffer.event_id==event.id,SupportOffer.status=='accepted')):
        org=session.get(Organization,offer.organization_id) if offer.organization_id else None
        if org and org.profile.get('recognition',{}).get('show_profile'):
            dto=offer_dto(session,offer);profile['sponsors'].append({'id':offer.id,'label':org.profile['name'],'status':'accepted_commitment','quantity':float(offer.content['quantity']) if org.profile['recognition']['show_contributions'] else None,'unit':offer.content['unit'],'verified_fulfillment':dto['verified'] if org.profile['recognition']['show_contributions'] else None})
    from app.execution.projections import augment_public
    from app.execution.coordination import participant
    # Viewer identity was authorized by the canonical profile service.
    return augment_public(session,event,profile)

def participation_state(session,actor,event,application_id=None):
    from app.publication.service import profile
    release=published(session,event,actor);p=profile(session,event,actor)
    a=session.scalar(select(Application).where(Application.event_id==event.id,Application.account_id==actor))
    if application_id and (not a or a.id!=application_id):missing()
    assignments=[assignment_dto(session,x) for x in session.scalars(select(Assignment).where(Assignment.event_id==event.id,Assignment.account_id==actor))]
    from app.execution.projections import state as execution_state,communications
    ex=execution_state(session,actor,event);com=communications(session,actor,event)
    p['updates']=[{**x,'author_label':'Event organizer'} for x in com if x['kind']=='announcement' and x['status']=='published']
    work_ids={w for x in assignments if x['status']=='assignment_accepted' for w in x['work_ids']};works=release.snapshot['plan']['work'];user=session.get(User,actor)
    return {'event':p['event'],'account':{'id':actor,'label':user.display_name,'synthetic':False},'profile':p,'application':application_dto(session,a) if a else None,'applications':[application_dto(session,a)] if a else [],'availability':a.content['intervals'] if a else [],'limitations':[a.content['answers']['limitations']] if a and a.content['answers']['limitations'] else [],'configuration':{**release.snapshot['configuration']['tags'],'version':release.sequence},'roles':p['roles'],'assignments':assignments,'accepted_work':[w for w in ex['work'] if w['id'] in work_ids],'commitments':[{'id':x['id'],'assignment_id':x['id'],'terms_key':x['terms_key'],'status':'accepted'} for x in assignments if x['status']=='assignment_accepted'],'meetings':[x for x in com if x['kind']=='meeting'],'blockers':[{'id':x['id'],'title':x['description'],'status':x['resolution_status']} for x in ex['blockers']],'reports':[{'id':x['id'],'review_status':x['review_status']} for x in ex['reports']],'day_count':max(p['event']['schedule']['relative_days'] or [1])}

def organizer_participants(session,actor,event):
    require(session,actor,event.id,'plan:write');require(session,actor,event.id,'source:private');release=published(session,event,actor)
    apps=list(session.scalars(select(Application).where(Application.event_id==event.id,Application.status!='application_draft')))
    work={x['id']:x for x in release.snapshot['plan']['work']};templates=[]
    for a in apps:
        for r in release.snapshot['plan']['roles']:
            if r['id'] in a.content['role_ids']:
                for wid in r['work_ids']:
                    templates.append({'id':r['id']+':'+wid,'account_id':a.account_id,'role_requirement_id':r['id'],'work_ids':[wid],'schedule':work[wid]['schedule']})
    return {'event':event_dto(event),'plan_id':release.plan_id,'applications':[application_dto(session,a) for a in apps],'assignments':[assignment_dto(session,x) for x in session.scalars(select(Assignment).where(Assignment.event_id==event.id))],'roles':[role_view(r) for r in release.snapshot['plan']['roles']],'work':list(work.values()),'templates':templates,'configuration':release.snapshot['configuration']['tags']}

def my_events(session,actor):
    result=[]
    for event in session.scalars(select(Event).where(Event.lifecycle!='deleted').order_by(Event.id)):
        organizer=allowed(session,actor,event.id,'plan:write') and allowed(session,actor,event.id,'event:read')
        apps=list(session.scalars(select(Application).where(Application.event_id==event.id,Application.account_id==actor)))
        assignments=[assignment_dto(session,a) for a in session.scalars(select(Assignment).where(Assignment.event_id==event.id,Assignment.account_id==actor)) if effective_assignment(session,a)=='assignment_accepted']
        if organizer or apps or assignments:
            release=session.get(Publication,event.current_publication_id) if event.current_publication_id else None
            e=event_dto(event) if organizer else {**release.snapshot['event'],'context_id':None} if release else {'id':event.id,'title':'Unavailable event','location':{'label':''},'schedule':{'timezone':'UTC','anchor_date':None,'relative_days':[]}}
            item={'event':e,'organizer':organizer,'can_delete':organizer and event.creator_id==actor,'applications':[application_dto(session,a) for a in apps],'accepted_assignments':assignments}
            if organizer:
                from app.planning.draft_models import PlanningDraft
                from app.planning.service import reviewed_stages
                from urllib.parse import quote
                base=f'/events/{event.id}'
                draft=session.scalar(select(PlanningDraft).where(PlanningDraft.event_id==event.id))
                saved=(draft.stage_reviews or {}).get('workflow_progress',{}) if draft else {}
                if event.lifecycle=='published':
                    path=base+'/manage/overview'
                elif event.lifecycle=='draft':
                    path=f'/events/{event.id}/create/{event.draft_step}'
                elif saved.get('step') in ('governance','governance/ticket','planning','work','actors','setup','finalize'):
                    path=base+'/'+saved['step']
                    if saved['step']=='work' and draft:
                        stage=saved.get('stage_id')
                        if stage in {s['id'] for s in draft.content['stages']}:
                            path+='/'+quote(stage,safe='')
                elif not draft:
                    path=base+'/governance'
                elif not draft.stage_confirmed:
                    path=base+'/planning'
                elif not draft.work_confirmed:
                    remaining=next((s['id'] for s in draft.content['stages'] if s['id'] not in reviewed_stages(draft,'work')),None)
                    path=base+'/work'+('/'+quote(remaining,safe='') if remaining else '')
                elif not draft.actors_confirmed:
                    path=base+'/actors'
                else:
                    path=base+'/setup'
                item['resume_path']=path
            result.append(item)
    return result



