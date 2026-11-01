"""Versioned insight documents in the existing immutable operational source journal.
No recovery tables and no demographic data is sent to a model.
"""
from collections import Counter
from typing import Literal
from pydantic import Field,model_validator
from sqlalchemy import select
from app.memory.schemas import StrictModel
from app.participation.models import OperationalSource
from app.participation.projections import accepted
from app.participation.service import published
from app.shared.types import uid,digest
from app.shared.audit import audit
from app.api.errors import DomainError

class Question(StrictModel):
    id:str=Field(pattern=r'^[a-z][a-z0-9_]{0,59}$')
    label:str=Field(min_length=1,max_length=120)
    description:str=Field(default='',max_length=500)
    dimension:Literal['age_range','neighborhood','experience_level','participation_interest','tags','custom']
    choices:list[str]=Field(min_length=1,max_length=30)
    required:bool=False
    enabled:bool=True
    aggregate:bool=True
    @model_validator(mode='after')
    def bounded(self):
        if len(set(self.choices))!=len(self.choices) or any(not c.strip() or len(c)>100 for c in self.choices):raise ValueError('Invalid or duplicate choices')
        return self
class Configuration(StrictModel):
    expected_revision:int=Field(ge=0)
    public_aggregates:bool=False
    questions:list[Question]=Field(max_length=30)
    @model_validator(mode='after')
    def unique(self):
        if len({q.id for q in self.questions})!=len(self.questions) or len({q.label.casefold() for q in self.questions})!=len(self.questions):raise ValueError('Duplicate question identifiers or labels')
        return self
class Response(StrictModel):
    configuration_revision:int=Field(ge=1)
    answers:dict[str,str]=Field(default_factory=dict,max_length=30)
    consent:bool


def latest(db,eid,kind,actor=None):
    q=select(OperationalSource).where(OperationalSource.event_id==eid,OperationalSource.kind==kind)
    if actor:q=q.where(OperationalSource.created_by==actor)
    return db.scalar(q.order_by(OperationalSource.sequence.desc()))

def append(db,actor,e,kind,content,previous):
    row=OperationalSource(id=uid(),event_id=e.id,aggregate_id=previous.aggregate_id if previous else uid(),sequence=previous.sequence+1 if previous else 1,kind=kind,content=content,digest=digest(content),created_by=actor)
    db.add(row);db.flush();e.version+=1;audit(db,actor,e.id,kind,row.id)
    from app.shared.models import OutboxEvent
    db.add(OutboxEvent(event_id=e.id,actor_id=actor,dedup_key="insight:"+row.id,payload={"kind":kind,"source_id":row.id}))
    return row

def configuration(db,e):
    row=latest(db,e.id,'insight.configuration')
    return {'revision':row.sequence if row else 0,'public_aggregates':row.content['public_aggregates'] if row else False,'questions':row.content['questions'] if row else []}

def configure(db,actor,e,b):
    old=latest(db,e.id,'insight.configuration')
    if b.expected_revision!=(old.sequence if old else 0):raise DomainError('stale_configuration','Reload current field configuration')
    # A changed question gets a new configuration lineage; no old answers are reinterpreted.
    row=append(db,actor,e,'insight.configuration',b.model_dump(exclude={'expected_revision'}),old)
    return {'revision':row.sequence,**row.content}

def respond(db,actor,e,b):
    published(db,e,actor,True);config=configuration(db,e)
    if b.configuration_revision!=config['revision']:raise DomainError('stale_configuration','Answer the current enabled questions')
    questions={q['id']:q for q in config['questions'] if q['enabled']}
    if not b.answers.keys()<=questions.keys():raise DomainError('invalid_answers','Unknown or disabled question',422)
    if any(q['required'] and key not in b.answers for key,q in questions.items()) or any(value not in questions[key]['choices'] for key,value in b.answers.items()):raise DomainError('invalid_answers','Missing required answer or invalid choice',422)
    old=latest(db,e.id,'insight.response',actor)
    row=append(db,actor,e,'insight.response',b.model_dump(),old)
    return {'revision':row.sequence,**row.content}

def revoke(db,actor,e):
    old=latest(db,e.id,'insight.response',actor)
    if not old:raise DomainError('not_found','No insight response',404)
    row=append(db,actor,e,'insight.response',{**old.content,'consent':False},old)
    return {'revision':row.sequence,'consent':False}

def aggregate(db,actor,e,filters=None):
    published(db,e,actor,True);config=configuration(db,e)
    # No arbitrary filters: suppress rather than allow complementary/differencing queries.
    if filters or not config['public_aggregates']:return {'status':'suppressed','breakdowns':[]}
    db.execute(__import__('sqlalchemy').text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':'insight-release:'+e.id})
    ids={a.account_id for a in accepted(db,e)};responses=[];cohort={}
    for aid in ids:
        row=latest(db,e.id,'insight.response',aid)
        if row and row.content['consent'] and row.content['configuration_revision']==config['revision']:responses.append(row.content['answers']);cohort[aid]=digest(row.content)
    old=latest(db,e.id,'insight.release')
    if old and old.content['cohort']!=cohort:
        changed={k for k in set(old.content['cohort'])|set(cohort) if old.content['cohort'].get(k)!=cohort.get(k)}
        if len(changed)<5:return {'status':'suppressed','breakdowns':[],'reason':'Cohort changes below safe release threshold'}
    output=[]
    for q in config['questions']:
        if not q['enabled'] or not q['aggregate']:continue
        counts=Counter(r[q['id']] for r in responses if q['id'] in r)
        # Suppress the entire dimension if a bucket OR missing-response complement is small.
        missing=len(responses)-sum(counts.values())
        safe=len(responses)>=5 and bool(counts) and min(counts.values())>=5 and (missing==0 or missing>=5)
        output.append({'question_id':q['id'],'dimension':q['dimension'],'label':q['label'],'status':'available' if safe else 'suppressed','buckets':[{'label':k,'count':v} for k,v in sorted(counts.items())] if safe else []})
    if any(x['status']=='available' for x in output) and (not old or old.content['cohort']!=cohort):
        row=OperationalSource(id=uid(),event_id=e.id,aggregate_id=old.aggregate_id if old else uid(),sequence=old.sequence+1 if old else 1,kind='insight.release',content={'cohort':cohort},digest=digest(cohort),created_by=e.creator_id)
        db.add(row);db.flush()
    return {'status':'available' if any(x['status']=='available' for x in output) else 'suppressed','breakdowns':output,'configuration_revision':config['revision']}
