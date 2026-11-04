"""Disabled-by-default Modal adapter. Exact source excerpts only; no operational tools."""
import json,re
import httpx
from pydantic import Field
from app.memory.schemas import StrictModel,Candidate,Assertion,Applicability
from app.api.errors import DomainError
MODEL='Qwen/Qwen2.5-1.5B-Instruct'
REVISION='989aa7980e4cf806f80c7fef2b1adb7bc71aa306'
class Extract(StrictModel):
    source_id:str
    title:str=Field(min_length=1,max_length=200)
    excerpt:str=Field(min_length=8,max_length=2000)
class Output(StrictModel):
    lessons:list[Extract]=Field(min_length=1,max_length=4)
def safe_sources(request, *, allow_synthetic_test=False):
    sources=[]
    for source in request.sources:
        value=json.loads(source.text)
        if value.get('kind')!='recovery.outcome' or source.evidence_stage!='verified':raise DomainError('unsupported_memory_source','Model extraction requires exact human-verified recovery outcomes',422)
        record=value['source_record']['record']
        if record.get('data_class')!='real' and not (allow_synthetic_test and record.get('data_class')=='synthetic'):raise DomainError('synthetic_memory','Synthetic or unclassified events cannot produce trusted lessons',422)
        # No issue descriptions, participant identifiers, report text, names or medical context.
        text=json.dumps({k:record[k] for k in ('data_class','category','outcome','actions_attempted','changed_work_ids','interventions','blocker_categories') if k in record},sort_keys=True)
        sources.append({'source_id':source.ref.source_id,'text':text})
    if not 1<=len(sources)<=4 or sum(len(s['text']) for s in sources)>8000:raise DomainError('input_budget_exceeded','Use one to four bounded operational outcome sources',422)
    return sources
class ModalHTTPExtractor:
    model_profile=MODEL+'@'+REVISION
    live_provider=True
    def __init__(self,endpoint,key,secret,client=None,*,allow_synthetic_test=False):
        from urllib.parse import urlparse
        parsed=urlparse(endpoint)
        if parsed.scheme!='https' or not parsed.hostname or not parsed.hostname.endswith('.modal.run') or parsed.username or parsed.password or parsed.query:raise ValueError('Verified HTTPS Modal web-function URL required')
        self.endpoint=endpoint;self.key=key;self.secret=secret;self.client=client
        # Explicit verification harness only; never enabled by application settings.
        self.allow_synthetic_test=allow_synthetic_test
    def extract(self,request):
        minimized=safe_sources(request,allow_synthetic_test=self.allow_synthetic_test)
        body={'schema_version':'memory-v1','sources':minimized}
        try:
            if self.client:response=self.client.post(self.endpoint,json=body,headers={'Modal-Key':self.key,'Modal-Secret':self.secret},timeout=120)
            else:
                with httpx.Client(follow_redirects=False) as client:response=client.post(self.endpoint,json=body,headers={'Modal-Key':self.key,'Modal-Secret':self.secret},timeout=120)
            if response.status_code==422:raise DomainError('invalid_model_output','Modal rejected the structured extraction; no automatic retry',422)
            if not response.is_success:raise DomainError('extractor_unavailable','Modal rejected extraction; no automatic retry',503)
            if len(response.content)>16000:raise ValueError('Output budget')
            result=response.json()
            if result.get('model')!=MODEL or result.get('revision')!=REVISION:raise ValueError('Pinned model mismatch')
            output=Output.model_validate(result['output'])
        except httpx.RequestError:raise DomainError('extractor_unavailable','Modal unavailable; manual recovery remains available',503) from None
        originals={s.ref.source_id:s for s in request.sources};allowed={s['source_id']:s['text'] for s in minimized};candidates=[]
        for lesson in output.lessons:
            if lesson.source_id not in allowed or lesson.excerpt not in allowed[lesson.source_id]:raise DomainError('invalid_provenance','Memory excerpt must be an exact permitted source quotation',422)
            s=originals[lesson.source_id]
            candidates.append(Candidate(kind='lesson',title=lesson.title,assertions=[Assertion(assertion_id='source',text=lesson.excerpt,claim_kind='lesson',evidence_stage=s.evidence_stage,outcome=s.outcome,evaluation_criteria=s.criteria,source_refs=[s.ref],confidence_basis='model_estimate',uncertainty_reasons=['Model-selected factual excerpt; applicability requires human review'])],applicability=Applicability.model_validate(s.applicability)))
        return candidates
