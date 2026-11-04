"""Offline: parser, constraints, redaction, and backend factual validation."""
import json
import httpx,pytest
from modal_memory.structured import TITLE,choices,schema_for,constrained_parser,validate_output,diagnostic
from app.memory.modal_adapter import MODEL,REVISION,ModalHTTPExtractor,safe_sources
from app.memory.ports import ExtractionInput
from app.api.errors import DomainError
from tests.test_prompt7_workspace import source

SOURCES=[{'source_id':'source-1','text':json.dumps({'outcome':'mixed','actions_attempted':['work:1']},sort_keys=True)}]
def valid():return {'lessons':[{'source_id':'source-1','title':TITLE,'excerpt':'"outcome": "mixed"'}]}
def test_valid_json_and_character_constraint():
    text=json.dumps(valid(),separators=(',',':'));assert validate_output(text,SOURCES)==valid()
    parser=constrained_parser(SOURCES)
    for char in text:
        assert char in parser.get_allowed_characters()
        parser=parser.add_character(char)
    assert parser.can_end()
    assert '`' not in constrained_parser(SOURCES).get_allowed_characters()

@pytest.mark.parametrize('text',['not JSON','```json\n{}\n```','{"lessons":[','{"lessons":[],"outcome":"successful"}','{"lessons":[],"lessons":[]}'])
def test_malformed_truncated_extra_duplicate_rejected(text):
    with pytest.raises(ValueError):validate_output(text,SOURCES)

@pytest.mark.parametrize('change',[{'source_id':'unknown'},{'excerpt':'"outcome": "successful"'},{'title':'This recovery always succeeds'}])
def test_unsupported_references_outcomes_titles_rejected(change):
    output=valid();output['lessons'][0].update(change)
    with pytest.raises(ValueError):validate_output(json.dumps(output),SOURCES)

def test_private_diagnostic_redacts_content_and_reports_truncation():
    raw='{"secret":"api-secret-123", "medical":"private diagnosis"'
    try:json.loads(raw)
    except json.JSONDecodeError as error:
        d=diagnostic(raw,model=MODEL,revision=REVISION,sources=SOURCES,generated_tokens=384,max_tokens=384,eos_reached=False,error=error)
    assert d['possibly_truncated'] and d['finish_reason']=='length' and d['json_error_position'] is not None
    assert len(d['redacted_excerpt'])<=320 and 'secret' not in d['redacted_excerpt'] and 'diagnosis' not in d['redacted_excerpt']
    assert len(d['source_digest'])==64

@pytest.mark.parametrize('change',[{'source_id':'unsupported'},{'excerpt':'"outcome": "successful"'},{'outcome':'successful'}])
def test_backend_rejects_unsupported_model_claims(change):
    request=ExtractionInput('event',(source(),));allowed=safe_sources(request)
    lesson={'source_id':allowed[0]['source_id'],'title':'Neutral source excerpt','excerpt':'"outcome": "mixed"'};lesson.update(change)
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'model':MODEL,'revision':REVISION,'output':{'lessons':[lesson]}}))) as client:
        with pytest.raises((DomainError,ValueError)):
            ModalHTTPExtractor('https://example.modal.run','fake','fake',client).extract(request)

@pytest.mark.parametrize('bad',['broken','{"lessons":[',json.dumps({'lessons':[{'source_id':'unknown','title':TITLE,'excerpt':'"outcome": "successful"'}]})])
def test_invalid_generation_persists_failed_run_without_memory(seeded,factory,bad):
    from sqlalchemy import select,func
    from app.memory.service import enqueue
    from app.memory.schemas import ExtractionRequest,SourceRef
    from app.memory.worker import work_once
    from app.memory.models import MemoryRun,MemoryEntry
    from app.shared.models import JobTask
    class Invalid:
        model_profile='offline-invalid'
        def extract(self,request):return validate_output(bad,SOURCES)
    with factory.begin() as db:
        run=enqueue(db,seeded['owner'],seeded['event'],ExtractionRequest(extractor='open_weight',source_refs=[SourceRef.model_validate(seeded['ref'])]),live=True)
    assert work_once(factory,Invalid()) is False
    with factory() as db:
        record=db.get(MemoryRun,run['run_id'])
        assert record.status=='failed' and record.failure_code=='invalid_model_output' and record.output_entry_ids==[]
        assert db.scalar(select(func.count()).select_from(MemoryEntry))==0
        task=db.scalar(select(JobTask).where(JobTask.run_id==record.id))
        assert task.attempt_count==1 and task.max_attempts==1
