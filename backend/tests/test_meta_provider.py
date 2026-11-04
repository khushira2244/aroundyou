import io
import json
import wave
import httpx
import pytest
from app.ai.meta_provider import MetaProvider,BASE_URL
from app.ai.planning_port import MuseSparkRequest
from app.ai.service import output_schema
from app.ai.voice import normalize_audio
from app.api.errors import DomainError

def request(kind='understanding'):
    return MuseSparkRequest(kind,{'original_context':'Reading workshop'}, {}, {},'Interpret the actual event',output_schema(kind))

def test_structured_transport_and_no_fallback():
    calls=[]
    def handler(r):
        calls.append(r);body=json.loads(r.content)
        assert body['model']=='muse-spark-1.3' and body['max_completion_tokens']==4096
        assert body['response_format']['type']=='json_schema' and body['store'] is False
        assert r.headers['authorization']=='Bearer test-key'
        return httpx.Response(200,json={'id':'test-response','model':'muse-spark-1.3','choices':[{'finish_reason':'stop','message':{'content':'{"scope":["Reading workshop"]}'}}],'usage':{'completion_tokens':12}})
    provider=MetaProvider('test-key',client=httpx.Client(transport=httpx.MockTransport(handler)))
    result=provider.propose(request());assert result['scope']==['Reading workshop']
    assert result['_provider_metadata']['request_id']=='test-response'
    with pytest.raises(DomainError,match='provider_scope_disabled'):provider.propose(request('recovery'))
    assert len(calls)==1

@pytest.mark.parametrize('status,code',[(401,'provider_authentication_failed'),(403,'provider_access_denied'),(404,'provider_model_unavailable'),(429,'provider_rate_limited'),(503,'provider_unavailable')])
def test_provider_errors_are_sanitized_and_not_retried(status,code):
    calls=[]
    def handler(r):calls.append(r);return httpx.Response(status,json={'secret':'never echo me'})
    p=MetaProvider('test-key',client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(DomainError) as caught:p.propose(request())
    assert caught.value.code==code and 'never echo me' not in caught.value.message and len(calls)==1

@pytest.mark.parametrize('content,finish',[('not json','stop'),('{}','length')])
def test_bad_or_truncated_output_is_not_a_proposal(content,finish):
    p=MetaProvider('test-key',client=httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'choices':[{'finish_reason':finish,'message':{'content':content}}]}))))
    with pytest.raises(DomainError) as caught:p.propose(request())
    assert caught.value.code=='invalid_model_output'

def test_voice_multipart_contract():
    def handler(r):
        assert str(r.url)==BASE_URL+'/asr/transcribe'
        assert b'muse-voice-transcribe-1.0' in r.content and b'PUSH_TO_TALK' in r.content and b'audioEncoding' in r.content
        return httpx.Response(200,json={'sessionId':'speech-test','transcript':'User spoken words','audioDurationMs':1000})
    p=MetaProvider('key',client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert p.transcribe(b'wav')['transcript']=='User spoken words'

def wav(seconds=1):
    buffer=io.BytesIO()
    with wave.open(buffer,'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b'\0\0'*16000*seconds)
    return buffer.getvalue()

def test_audio_validation_and_normalization():
    value,seconds=normalize_audio(wav());assert seconds==1
    with wave.open(io.BytesIO(value)) as f:assert (f.getnchannels(),f.getsampwidth(),f.getframerate())==(1,2,24000)
    for raw in [b'not audio',wav(61)]:
        with pytest.raises(DomainError):normalize_audio(raw)

def test_review_digest_preserves_legacy_and_binds_new_corrections():
    from types import SimpleNamespace
    from app.shared.source_resolver import decision_digest
    from app.shared.types import digest
    values={k:None for k in ['event_id','actor_id','supersedes_id','subject_kind','subject_id','subject_digest','decision','evidence_stage','outcome','criteria','note']}
    row=SimpleNamespace(**values,reviewed_content=None)
    assert decision_digest(row)==digest(values)
    row.reviewed_content={'governance':{'items':[]}}
    assert decision_digest(row)!=digest(values)

def test_governance_uses_extended_deadline_without_retry():
    calls = []
    def handler(req):
        calls.append(req)
        assert req.extensions['timeout']['read'] == 68
        raise httpx.ReadTimeout('simulated governance timeout', request=req)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = MetaProvider('test-key', client=client)
        with pytest.raises(DomainError) as error:
            provider.propose(request('governance'))
    assert error.value.code == 'provider_timeout'
    assert len(calls) == 1
