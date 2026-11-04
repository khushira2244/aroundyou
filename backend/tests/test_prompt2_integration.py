from sqlalchemy import select
from tests.test_group2 import flow,FakeMuse,FORM
from tests.test_meta_provider import wav
from app.ai.models import AIRun,AIProposal
from app.shared.models import JobTask
from app.events.models import Event,ContextRevision
from app.shared.unit_of_work import unit_of_work
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
import pytest

class LocalTransport(FakeMuse):
    live_provider=True
    accepted_kinds=('understanding','governance')
    calls=0
    def propose(self,request):
        self.calls+=1
        if request.kind=='understanding':return {'scope':['Reading workshop'],'clarifications':['Which room is available?']}
        return {'items':[{'id':'venue','title':'Venue preparation','detail':'Ask the venue contact','responsible_party':'Organizer','applicability_conditions':['In person session'],'preparation_information':['Attendance estimate'],'recommendation_type':'verify_with_authority','supporting_event_facts':['Education']}]}
    def transcribe(self,wav):self.calls+=1;return {'transcript':'Recognized speech from test transport','model':'local-test-transcription'}

def test_background_runs_persist_reuse_and_human_review(flow,app,factory):
    flow.new();adapter=LocalTransport();app.state.planning_adapter=adapter
    run=flow.call('/context-proposals',{},expected=202)
    read=flow.client.get('/v1/ai-runs/'+run['run_id'],headers=flow.headers()).json()['data']
    assert read['status']=='succeeded' and adapter.calls==1
    assert flow.get('/creation').json()['data']['context']['approved_interpretation'] is None
    for _ in range(3):assert flow.get('/creation').status_code==200
    assert adapter.calls==1
    p=read['proposal'];flow.call('/context-proposals/'+p['id']+'/review',{'decision':'accept','reviewed_digest':p['digest']})
    assert flow.get('/creation').json()['data']['context']['approved_interpretation']['scope']==['Reading workshop']
    with factory() as db:assert db.scalar(select(JobTask).where(JobTask.ai_run_id==run['run_id'])).max_attempts==1

def test_governance_uses_saved_context_and_corrections_preserve_original(flow,app,factory):
    flow.new();adapter=LocalTransport();app.state.planning_adapter=adapter
    flow.call('/governance/assessments',{},expected=202)
    p=flow.get('/governance').json()['data']['proposals'][0];corrected={'items':[{**p['items'][0],'detail':'Organizer corrected preparation'}]}
    flow.call('/governance/proposals/'+p['id']+'/review',{'decision':'accept','reviewed_digest':p['digest'],'corrected_governance':corrected})
    assert flow.get('/governance').json()['data']['items'][0]['detail']=='Organizer corrected preparation'
    with factory() as db:assert db.get(AIProposal,p['id']).payload['items'][0]['detail']=='Ask the venue contact'
    with pytest.raises(DBAPIError):
        with unit_of_work(factory) as db:db.execute(text("UPDATE review_decisions SET reviewed_content='{}'::jsonb WHERE subject_id=:id"),{'id':p['id']})
    flow.call('/context-revisions',{'text':'Materially changed activity','source':'written'})
    assert flow.get('/governance').json()['data']['guidance']['status']=='stale_reassessment_required'

def test_voice_private_idempotent_and_not_confirmed(flow,app,factory,headers,tmp_path):
    flow.new();adapter=LocalTransport();app.state.planning_adapter=adapter;app.state.settings.voice_directory=str(tmp_path)
    path='/v1/events/'+flow.id+'/voice-transcriptions';h=flow.headers(key='one-audio')
    for _ in range(2):
        response=flow.client.post(path,headers=h,files={'audio':('speech.wav',wav(),'audio/wav')});assert response.status_code==200,response.text
    assert adapter.calls==1
    value=response.json()['data'];assert value['requires_organizer_review']
    assert flow.client.get(path,headers=headers('outsider-subject')).status_code==404
    assert flow.get('/creation').json()['data']['context']['original_text']==FORM['executionIntent']
    flow.call('/context-revisions',{'text':'Organizer corrected speech','source':'reviewed_transcript','transcript_run_id':value['id']})
    with factory() as db:
        event=db.get(Event,flow.id);source=db.get(ContextRevision,event.active_context_revision_id)
        assert source.snapshot['transcript_run_id']==value['id'] and event.interpretation is None
        assert db.get(AIRun,value['id']).context_manifest['result']['transcript']=='Recognized speech from test transport'

def test_previous_inputs_are_human_only_and_owned(flow,headers):
    first=flow.new();second=flow.new('Another workshop')
    path='/v1/me/previous-creation-inputs?exclude_event_id='+second
    value=flow.client.get(path,headers=flow.headers()).json()['data']['form']
    assert value['title']==FORM['title'] and value['confirmAccuracy'] is False
    assert 'interpretation' not in value and 'clarification_rounds' not in value
    assert flow.client.get(path,headers=headers('outsider-subject')).json()['data']['form'] is None

def test_live_failure_has_one_attempt_no_mutation(flow,app,factory):
    flow.new();adapter=LocalTransport()
    def fail(request):adapter.calls+=1;raise TimeoutError()
    adapter.propose=fail;app.state.planning_adapter=adapter
    run=flow.call('/context-proposals',{},expected=202)
    for _ in range(2):
        value=flow.client.get('/v1/ai-runs/'+run['run_id'],headers=flow.headers()).json()['data']
        assert value['status']=='failed' and value['error']['code']=='provider_timeout'
    assert adapter.calls==1
    assert flow.get('/creation').json()['data']['context']['approved_interpretation'] is None

