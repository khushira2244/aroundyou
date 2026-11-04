from copy import deepcopy
import time
import pytest
from sqlalchemy import select,text
from sqlalchemy.exc import DBAPIError
from tests.test_group2 import flow,FakeMuse,FORM
from app.ai.service import work_ai_once
from app.ai.models import AIRun
from app.ai.context_builder import MuseSparkContextBuilder
from app.events.models import Event,ContextRevision
from app.shared.unit_of_work import unit_of_work
from app.shared.source_resolver import resolve
from app.memory.schemas import SourceRef
from app.api.errors import DomainError


def proposal(flow,app,factory,kind='context'):
    app.state.planning_adapter=FakeMuse()
    run=flow.call('/context-proposals' if kind=='context' else '/governance/assessments',{},expected=202)
    assert work_ai_once(factory,app.state.planning_adapter) is True
    return flow.client.get('/v1/ai-runs/'+run['run_id'],headers=flow.headers()).json()['data']['proposal']


def test_multiple_clarifications_exact_confirmation_and_memory_invalidation(flow,app,factory):
    flow.new();initial=flow.get('/creation').json()['data']['context'];p=proposal(flow,app,factory)
    for question,answer in [('Which room?','Library reading room'),('Which equipment?','Projector is not confirmed')]:
        ctx=flow.get('/creation').json()['data']['context']
        flow.call('/context-clarifications',{'context_version':ctx['version'],'answers':[{'question':question,'answer':answer}]})
    ctx=flow.get('/creation').json()['data']['context'];assert len(ctx['clarification_rounds'])==2
    assert ctx['original_text']==FORM['executionIntent']
    flow.call('/context-proposals/'+p['id']+'/review',{'decision':'accept','reviewed_digest':p['digest']},expected=409)
    flow.call('/context-interpretations',{'context_version':ctx['version'],'interpretation':{'reported_facts':['Library reading room'],'scope':['Small reading sessions'],'assumptions':['Power may be available'],'unknowns':['Power confirmation']}})
    saved=flow.get('/creation').json()['data']['context'];assert saved['approved_interpretation']['assumptions']==['Power may be available']
    with factory() as db:
        event=db.get(Event,flow.id);source=db.get(ContextRevision,event.active_context_revision_id)
        assert source.snapshot['confirmed_interpretation']['scope']==['Small reading sessions']
        bundle=MuseSparkContextBuilder().build(db,event.creator_id,event.id)
        assert bundle['authoritative_current']['confirmed_context']['scope']==['Small reading sessions']
        old=db.get(ContextRevision,initial['id'])
        with pytest.raises(DomainError):resolve(db,event.creator_id,event.id,SourceRef(source_kind='context',source_id=old.id,source_revision=old.sequence,source_digest=old.content_hash))
        new=resolve(db,event.creator_id,event.id,SourceRef(source_kind='context',source_id=source.id,source_revision=source.sequence,source_digest=source.content_hash));assert 'Small reading sessions' in new.text
    with pytest.raises(DBAPIError):
        with unit_of_work(factory) as db:db.execute(text("UPDATE event_context_revisions SET snapshot='{}'::jsonb WHERE id=:id"),{'id':saved['id']})


def test_clarification_scope_authorization_idempotency_conflicts(flow,headers):
    flow.new();ctx=flow.get('/creation').json()['data']['context'];version=flow.get('').json()['data']['version']
    path='/v1/events/'+flow.id+'/context-clarifications';body={'context_version':ctx['version'],'answers':[{'question':'Attendance?','answer':'Unknown'}]};h=flow.headers(key='clarification',version=str(version))
    a=flow.client.post(path,json=body,headers=h);b=flow.client.post(path,json=body,headers=h);assert a.status_code==b.status_code==200;assert a.json()['data']==b.json()['data']
    assert flow.client.post(path,json=body,headers=flow.headers(key='stale',version=str(version))).status_code==409
    assert flow.client.post(path,json=body,headers=headers('outsider-subject')).status_code==404


@pytest.mark.parametrize('category,city,scale,start',[('Education','Hazaribagh','15','09:00'),('Health','Ranchi','300','18:00')])
def test_governance_receives_actual_event_facts_and_uncertain_legal_sources(flow,app,factory,category,city,scale,start):
    flow.new();form={**FORM,'category':category,'city':city,'expectedAttendees':scale,'startTime':start,'endTime':'20:00'}
    flow.call('/draft',{'step':4,'form':form},method='PATCH')
    class Scoped(FakeMuse):
        def propose(self,r):
            details=r.authoritative_current['organizer_reported_event_details'];assert details['category']==category and details['city']==city and details['expectedAttendees']==scale and details['startTime']==start
            return {'items':[{'id':'venue','title':'Confirm '+category+' venue access','detail':'Ask the venue contact','classification':'conditional_recommendation','rationale':'Venue access remains unconfirmed','supporting_event_facts':[city,category],'uncertainty':['Applicable local rules have not been verified'],'next_action':'Organizer checks venue conditions','suggest_ticket':True}]}
    app.state.planning_adapter=Scoped();run=flow.call('/governance/assessments',{},expected=202);assert work_ai_once(factory,app.state.planning_adapter)
    g=flow.get('/governance').json()['data'];p=g['proposals'][0];assert p['items'][0]['rule_sources']==[] and g['items']==[]
    flow.call('/governance/proposals/'+p['id']+'/review',{'decision':'accept','reviewed_digest':p['digest']})
    assert flow.get('/governance').json()['data']['guidance']['permission_status']=='not_verified'
    flow.create();flow.call('/context-details',{**form,'city':'A changed venue city'},method='PATCH')
    g=flow.get('/governance').json()['data'];assert g['items']==[] and g['guidance']['status']=='stale_reassessment_required'


def test_internal_ticket_status_and_private_documents_never_external_approval(flow,headers,app,factory,tmp_path):
    flow.new()
    flow.call('/governance/tickets',{},expected=422)
    app.state.planning_adapter=FakeMuse()
    flow.call('/governance/assessments',{},expected=202)
    assert work_ai_once(factory,app.state.planning_adapter)
    proposal=flow.get('/governance').json()['data']['proposals'][0]
    flow.call('/governance/proposals/'+proposal['id']+'/review',{'decision':'accept','reviewed_digest':proposal['digest']})
    from app.execution.storage import LocalPrivateStorage
    app.state.evidence_storage=LocalPrivateStorage(tmp_path)
    requirement=proposal['items'][0]['id']
    original=b'%PDF-1.4\nprivate notes'
    base='/v1/events/'+flow.id+'/governance/tickets'
    response=flow.client.post(base+'/with-files',files=[(requirement,('notes.pdf',original,'application/pdf'))],headers=flow.headers(key='governance-file-confirm',version=str(flow.get('').json()['data']['version'])))
    assert response.status_code==200,response.text
    ticket=response.json()['data']['ticket']
    document=ticket['documents'][0]
    assert document['name']=='notes.pdf' and 'storage_key' not in document
    content=base+'/'+ticket['id']+'/documents/'+document['id']+'/content'
    assert flow.client.get(content,headers=flow.headers()).content==original
    assert flow.client.get(content,headers=headers('viewer-subject')).status_code==404
    assert flow.get('/governance').json()['data']['ticket']['documents']==[document]
    assert ticket['advisory_id']==proposal['id'] and ticket['confirmed_at']
    assert flow.call('/governance/tickets',{})['ticket']['id']==ticket['id']
    path='/governance/tickets/'+ticket['id']
    for status in ['in_review','waiting_for_documents','closed','open']:
        value=flow.call(path,{'status':status,'note':'Organizer follow-up only'},method='PATCH')['ticket'];assert value['status']==status and value['permission_status']=='not_verified' and value['external_submission'] is False
    flow.call(path+'/documents',{'name':'Private venue notes','document_type':'venue','document_reference':'Private organizer folder'})
    assert flow.client.get('/v1/events/'+flow.id+'/governance',headers=headers('viewer-subject')).status_code==404
    assert len(flow.get('/governance').json()['data']['ticket']['history'])==4
    flow.call(path,{'status':'approved','note':'Not permitted'},method='PATCH',expected=422)


@pytest.mark.parametrize('failure',['malformed','invented_rule','invented_fact','timeout'])
def test_provider_fails_closed_without_authoritative_mutation(flow,app,factory,failure):
    flow.new()
    class Bad(FakeMuse):
        def propose(self,r):
            if failure=='timeout':time.sleep(.08);return {'items':[]}
            if failure=='malformed':return {'approved':True}
            return {'items':[{'id':'bad','title':'Unsupported claim','detail':'Unverified','classification':'verified_requirement' if failure=='invented_rule' else 'ai_advisory_suggestion','supporting_event_facts':['FACT NOT IN ANY INPUT'] if failure=='invented_fact' else []}]}
    app.state.planning_adapter=Bad();run=flow.call('/governance/assessments',{},expected=202);assert work_ai_once(factory,app.state.planning_adapter,timeout_seconds=.01) is False
    with factory() as db:
        record=db.get(AIRun,run['run_id']);assert record.proposal_id is None;assert record.failure_code=='provider_timeout' if failure=='timeout' else record.failure_code=='invalid_model_output'
    time.sleep(.1)
    assert flow.get('/governance').json()['data']['items']==[]


def test_pending_context_reload_rejection_and_acknowledgement_preserve_confirmation(flow,app,factory):
    flow.new();p=proposal(flow,app,factory)
    pending=flow.get('/creation').json()['data']['context']['pending_interpretations'];assert pending[0]['id']==p['id'] and pending[0]['interpretation']['scope']==['Reading sessions']
    flow.call('/context-proposals/'+p['id']+'/review',{'decision':'reject','reviewed_digest':p['digest']})
    assert flow.get('/creation').json()['data']['context']['pending_interpretations']==[]
    ctx=flow.get('/creation').json()['data']['context']
    flow.call('/context-interpretations',{'context_version':ctx['version'],'interpretation':{'scope':['Organizer corrected sessions']}})
    before=flow.get('/creation').json()['data']['context'];flow.call('/draft',{'step':4,'form':{**FORM,'confirmAccuracy':False}},method='PATCH')
    after=flow.get('/creation').json()['data']['context'];assert after['version']==before['version'];assert after['approved_interpretation']['scope']==['Organizer corrected sessions']


def test_governance_inputs_include_planned_work_and_reported_setup_without_emergency_contact(flow,app,factory):
    flow.new();flow.create();flow.confirmed()
    flow.call('/setup/sections/location',{'data':{'facilities':'Evening classroom','access_instructions':'Library side door','emergency_contact':'PRIVATE-NOT-FOR-MODEL'}},method='PATCH')
    class Inspect(FakeMuse):
        def propose(self,r):
            ctx=r.authoritative_current['reported_operating_context']
            assert ctx['unconfirmed_planning_draft']['work'][0]['title']=='Reading practice'
            assert ctx['organizer_reported_setup']['location']['facilities']=='Evening classroom'
            assert 'PRIVATE-NOT-FOR-MODEL' not in str(ctx)
            return super().propose(r)
    app.state.planning_adapter=Inspect();run=flow.call('/governance/assessments',{},expected=202);assert work_ai_once(factory,app.state.planning_adapter)
    p=flow.get('/governance').json()['data']['proposals'][0]
    flow.call('/governance/proposals/'+p['id']+'/review',{'decision':'accept','reviewed_digest':p['digest']})
    flow.call('/setup/sections/location',{'data':{'facilities':'Outdoor venue'}},method='PATCH')
    assert flow.get('/governance').json()['data']['guidance']['status']=='stale_reassessment_required'


@pytest.mark.parametrize('kind,approved',[('context',False),('governance',False),('governance',True)])
def test_retracted_memory_blocks_advice_acceptance_and_current_governance(flow,app,factory,kind,approved):
    from app.memory.schemas import ExtractionRequest,RetractionRequest
    from app.memory.service import enqueue,retract
    from app.memory.worker import work_once
    from app.memory.models import MemoryEntry
    flow.new()
    with unit_of_work(factory) as db:
        event=db.get(Event,flow.id);source=db.get(ContextRevision,event.active_context_revision_id);actor=event.creator_id
        enqueue(db,actor,event.id,ExtractionRequest(source_refs=[SourceRef(source_kind='context',source_id=source.id,source_revision=source.sequence,source_digest=source.content_hash)]))
    assert work_once(factory)
    p=proposal(flow,app,factory,kind)
    path=('/context-proposals/' if kind=='context' else '/governance/proposals/')+p['id']+'/review'
    if approved:flow.call(path,{'decision':'accept','reviewed_digest':p['digest']})
    with unit_of_work(factory) as db:
        run=db.get(AIRun,db.get(__import__('app.ai.models',fromlist=['AIProposal']).AIProposal,p['id']).run_id)
        assert run.context_manifest['context_manifest']['retrieved_memories']
        memory=db.scalar(select(MemoryEntry).where(MemoryEntry.event_id==flow.id,MemoryEntry.lifecycle=='published'))
        retract(db,actor,flow.id,memory.id,RetractionRequest(reason='Organizer correction',reviewed_digest=memory.digest,expected_revision=memory.revision),'retract-used-memory',str(memory.version))
    if approved:assert flow.get('/governance').json()['data']['guidance']['status']=='stale_reassessment_required'
    else:flow.call(path,{'decision':'accept','reviewed_digest':p['digest']},expected=409)



