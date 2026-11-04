"""Offline regression tests. These tests never contact Modal."""
import httpx,pytest
from app.memory.modal_adapter import ModalHTTPExtractor,MODEL,REVISION
from app.memory.ports import ExtractionInput
from app.api.errors import DomainError
from tests.test_prompt7_workspace import source

def test_synthetic_verification_opt_in_keeps_original_provenance():
    sent=[]
    def handler(request):
        sent.append(request.content.decode())
        return httpx.Response(200,json={'model':MODEL,'revision':REVISION,'output':{'lessons':[{'source_id':'outcome-id','title':'Synthetic excerpt','excerpt':'"outcome": "mixed"'}]}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        request=ExtractionInput('event',(source('synthetic'),))
        with pytest.raises(DomainError,match='synthetic_memory'):
            ModalHTTPExtractor('https://example.modal.run','fake','fake',client).extract(request)
        assert not sent
        candidate=ModalHTTPExtractor('https://example.modal.run','fake','fake',client,allow_synthetic_test=True).extract(request)[0]
        assert len(sent)==1 and 'synthetic' in sent[0]
        assert candidate.assertions[0].source_refs==[request.sources[0].ref]

def test_provider_invalid_json_is_terminal_not_availability_retry():
    with httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(422,json={'detail':'Invalid structured extraction; no retries'}))) as client:
        with pytest.raises(DomainError) as caught:
            ModalHTTPExtractor('https://example.modal.run','fake','fake',client).extract(ExtractionInput('event',(source(),)))
        assert caught.value.code=='invalid_model_output' and caught.value.status==422
