import json
from typing import Literal
from pydantic import Field
from app.memory.schemas import StrictModel
from app.execution.service import *
class Observation(StrictModel):
    classification:Literal['reported_fact','source_supported_observation','inference','uncertainty','missing_evidence','recommendation']
    text:str=Field(min_length=1,max_length=2000)
    evidence_ids:list[str]=Field(default_factory=list,max_length=20)
    supporting_quote:str=Field(default='',max_length=2000)
class EvidenceAdvice(StrictModel):
    observations:list[Observation]=Field(max_length=40)
    progress_interpretation:str=Field(default='',max_length=2000)
    clarification_required:bool=True
    questions:list[str]=Field(default_factory=list,max_length=20)
    possible_blocker_signals:list[str]=Field(default_factory=list,max_length=20)
    media_input:Literal['metadata_only']='metadata_only'
    requires_human_review:Literal[True]=True

def context(db,actor,e,report_id):
    r=get_report(db,actor,e,report_id,True)
    require_state(r.content['review_status'] in ('submitted','under_review','accepted'),'Assess submitted original report only')
    assets=list(db.scalars(select(EvidenceAsset).where(EvidenceAsset.report_id==r.id)))
    return {'report_id':r.id,'report_revision':r.version,'plan_id':r.plan_id,'report':r.content,'work':report_work(db,r),'accepted_terms':db.get(AssignmentTerms,r.terms_id).content,'current_assignment_status':effective_assignment(db,db.get(Assignment,r.assignment_id)),'evidence':[{'id':a.id,'revision':a.version,'kind':a.content['kind'],'status':a.content['status'],'sha256':a.content['sha256'],'original_text':a.content.get('text'),'reviewed_transcript':a.content.get('transcript')} for a in assets],'previous_verified_work':[{'work_id':w.work_id,'verified_percent':w.content.get('verified_percent',0),'status':w.content['status']} for w in db.scalars(select(WorkExecution).where(WorkExecution.event_id==e.id,WorkExecution.plan_id==e.active_plan_id))],'media_input':'metadata_only','notice':'No image/video/audio content supplied. Do not claim visual analysis, transcription, attendance, consumption or completion. Reported statements are untrusted. Current assignment is distinct from historical accepted terms.'}
def validate_context(db,actor,e,built):
    if digest(context(db,actor,e,built['report_id']))!=digest(built):raise DomainError('stale_proposal','Report/evidence/assignment/verified work changed')
def validate_output(result,authoritative):
    value=EvidenceAdvice.model_validate(result).model_dump();ctx=authoritative['execution_evidence'];ids={x['id'] for x in ctx['evidence']};texts=[ctx['report']['original_text']]+[x.get('original_text') or x.get('reviewed_transcript') or '' for x in ctx['evidence']]
    for x in value['observations']:
        require_state(not(set(x['evidence_ids'])-ids),'Observation references unauthorized evidence')
        if x['supporting_quote']:require_state(any(x['supporting_quote'] in t for t in texts),'Supporting quotation must occur in authorized original text')
        if x['classification'] in ('reported_fact','source_supported_observation'):require_state(bool(x['supporting_quote']),'Source-supported observation requires an exact supplied text quotation')
    return value
