from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import jwt
import pytest
from sqlalchemy import select, func, text
from sqlalchemy.exc import DBAPIError
from app.shared.unit_of_work import unit_of_work
from app.shared.types import now
from app.memory.schemas import ExtractionRequest, ReviewRequest, CorrectionRequest, RetractionRequest
from app.memory.service import enqueue,review,correct,retract
from app.memory.worker import work_once,process_lease
from app.memory.models import MemoryEntry, MemoryRun, MemorySource
from app.memory.retrieval import retrieve
from app.shared.models import JobTask,AuditEvent,OutboxEvent
from app.shared.jobs import claim
from app.shared.outbox import dispatch_one
from app.events.models import Event,ContextRevision
from app.events.source_revisions import append_context,append_plan,record_observation_decision
from app.access.models import EventGrant,User
from app.ai.context_builder import MuseSparkContextBuilder
from app.api.errors import DomainError


def request(data,mode="deterministic"):
    return ExtractionRequest(source_refs=[data["ref"]],extractor=mode,purpose="event_review")

def extracted(factory,data,mode="deterministic",port=None):
    with unit_of_work(factory) as db:r=enqueue(db,data["owner"],data["event"],request(data,mode))
    assert work_once(factory,port) is True
    with factory() as db:
        run=db.get(MemoryRun,r["run_id"])
        return run.output_entry_ids[0]

def details(factory,memory_id):
    with factory() as db:
        e=db.get(MemoryEntry,memory_id)
        return e.digest,e.revision,e.version

def test_authentication_and_scoped_event_api(seeded,client,headers,settings):
    assert client.get('/v1/me').status_code==401
    assert client.get('/v1/me',headers={"Authorization":"Bearer invalid"}).status_code==401
    payload={"sub":"owner-subject","iss":"tests","aud":"wrong","iat":now(),"nbf":now(),"exp":now()+timedelta(minutes=5),"jti":"id"}
    invalid=jwt.encode(payload,settings.session_secret.get_secret_value(),algorithm="HS256")
    assert client.get('/v1/me',headers={"Authorization":"Bearer "+invalid}).status_code==401
    assert client.get('/v1/me',headers=headers()).json()['data']['user']['id']==seeded['owner']
    assert client.get('/v1/events/'+seeded['event'],headers=headers()).status_code==200
    assert client.get('/v1/events/'+seeded['other'],headers=headers()).status_code==404
    assert client.get('/v1/events/'+seeded['event']+'/sources/current',headers=headers('viewer-subject')).status_code==404

@pytest.mark.parametrize("claim",["exp","iss","aud","jti"])
def test_missing_required_token_claim(seeded,client,settings,claim):
    payload={"sub":"owner-subject","iss":"tests","aud":"aroundyou-tests","iat":now(),"nbf":now(),"exp":now()+timedelta(minutes=5),"jti":"id"};payload.pop(claim)
    token=jwt.encode(payload,settings.session_secret.get_secret_value(),algorithm="HS256")
    assert client.get('/v1/me',headers={"Authorization":"Bearer "+token}).status_code==401


def test_expired_and_inactive_user_denied(seeded,client,settings,headers,factory):
    from app.access.authentication import issue_token
    assert client.get('/v1/me',headers={"Authorization":"Bearer "+issue_token(settings,'owner-subject',-1)}).status_code==401
    with unit_of_work(factory) as db:db.get(User,seeded['owner']).active=False
    assert client.get('/v1/me',headers=headers()).status_code==401


def test_extraction_api_idempotency_and_source_validation(seeded,client,headers,factory):
    url=f"/v1/events/{seeded['event']}/memory/extractions"
    body=request(seeded).model_dump()
    a=client.post(url,json=body,headers=headers());assert a.status_code==202,a.text
    assert client.post(url,json=body,headers=headers()).json()==a.json()
    assert client.post(url,json={**body,'purpose':'planning'},headers=headers()).status_code==409
    bad={**body,'actor_id':seeded['owner']};assert client.post(url,json=bad,headers=headers(key='bad')).status_code==422
    foreign={**body,'source_refs':[{**seeded['ref'],'source_id':'unknown'}]};assert client.post(url,json=foreign,headers=headers(key='foreign')).status_code==404
    wrong={**body,'source_refs':[{**seeded['ref'],'source_digest':'b'*64}]};assert client.post(url,json=wrong,headers=headers(key='hash')).status_code==409
    assert client.post(url,json=body,headers=headers('viewer-subject')).status_code==404
    assert client.post(url,json={**body,'extractor':'open_weight'},headers=headers(key='model')).status_code==503
    assert work_once(factory) is True
    run_id=a.json()['data']['run']['run_id']
    assert client.get(url+'/'+run_id,headers=headers()).json()['data']['run']['status']=='succeeded'
    assert client.get(url+'/'+run_id,headers=headers('viewer-subject')).status_code==404


def test_memory_retrieval_filter_privacy_and_provenance(seeded,factory,client,headers):
    mid=extracted(factory,seeded)
    url=f"/v1/events/{seeded['event']}/memory"
    result=client.get(url,params={'q':'projectors','category':'Education','tags':'learning','conditions':'indoor'},headers=headers())
    assert result.status_code==200,result.text
    item=result.json()['data']['items'][0]
    assert item['memory_id']==mid and item['assertions'][0]['outcome']=='unknown'
    assert item['assertions'][0]['citations'][0]['permitted_source_reference']['id']==seeded['source']
    assert client.get(url,params={'category':'Environment'},headers=headers()).json()['data']['items']==[]
    assert client.get(url,headers=headers('viewer-subject')).json()['data']['items']==[]
    assert client.get(url+'/'+mid,headers=headers('viewer-subject')).status_code==404
    assert client.get(url+'/'+mid,headers=headers('outsider-subject')).status_code==404
    assert client.get(url,params={'include_reusable':'true'},headers=headers('outsider-subject')).status_code==404
    assert client.get(url,params={'limit':21},headers=headers()).status_code==422
    assert client.get(url,params={'cursor':'bad'},headers=headers()).status_code==422
    assert client.get(url+'/'+mid,headers=headers()).status_code==200


def test_uow_rollback_and_atomic_source_capture(seeded,factory):
    with pytest.raises(RuntimeError):
        with unit_of_work(factory) as db:
            e=db.get(Event,seeded['event']);append_context(db,seeded['owner'],e.id,'Should rollback',e.version)
            raise RuntimeError()
    with factory() as db:
        assert db.get(Event,seeded['event']).active_context_revision_id==seeded['source']
        assert db.scalar(select(func.count()).select_from(ContextRevision))==1
        assert db.scalar(select(func.count()).select_from(OutboxEvent))==1


def test_outbox_dispatch_dedup_and_no_duplicate_capture(seeded,factory):
    assert dispatch_one(factory) is True
    assert dispatch_one(factory) is False
    assert work_once(factory) is True
    with unit_of_work(factory) as db:
        result=enqueue(db,seeded['owner'],seeded['event'],request(seeded))
        assert result['status']=='succeeded'
    assert work_once(factory) is None
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(MemoryEntry))==1


def test_source_invalidation_and_memory_supersession(seeded,factory,client,headers):
    old=extracted(factory,seeded);hashed,revision,version=details(factory,old)
    with unit_of_work(factory) as db:
        e=db.get(Event,seeded['event']);new=append_context(db,seeded['owner'],e.id,'Power is unavailable; use printed material',e.version,{'category':'Education'})
        refs=[{'source_kind':'context','source_id':new.id,'source_revision':new.sequence,'source_digest':new.content_hash}]
    url=f"/v1/events/{seeded['event']}/memory"
    assert client.get(url,headers=headers()).json()['data']['items']==[]
    assert client.get(url+'/'+old,headers=headers()).status_code==404
    body={'reason':'Corrected source','correcting_source_refs':refs,'reviewed_digest':hashed,'expected_revision':revision}
    corrected=client.post(url+'/'+old+'/corrections',json=body,headers=headers(key='correct',version=str(version)))
    assert corrected.status_code==200,corrected.text
    new_id=corrected.json()['data']['replacement_candidate_id']
    assert client.post(url+'/'+old+'/corrections',json=body,headers=headers(key='correct',version=str(version))).json()==corrected.json()
    new_hash,new_revision,new_version=details(factory,new_id)
    review_body={'decision':'publish','reviewed_digest':new_hash,'expected_revision':new_revision}
    reviewed=client.post(url+'/'+new_id+'/review',json=review_body,headers=headers(key='review',version=str(new_version)));assert reviewed.status_code==200,reviewed.text
    assert client.get(url,headers=headers()).json()['data']['items'][0]['memory_id']==new_id
    stale=client.post(url+'/'+new_id+'/review',json=review_body,headers=headers(key='stale',version=str(new_version)));assert stale.status_code==409
    rbody={'reason':'No longer applicable','reviewed_digest':new_hash,'expected_revision':new_revision}
    assert client.post(url+'/'+new_id+'/retract',json=rbody,headers=headers(key='retract',version='2')).status_code==200
    assert client.get(url,headers=headers()).json()['data']['items']==[]
    with factory() as db:
        assert db.get(MemoryEntry,old).lifecycle=='superseded'
        assert db.get(ContextRevision,seeded['source']).original_text.startswith('Reading workshop')


class FakeModal:
    model_profile='test-open-weight-no-network'
    def extract(self,request):
        from app.memory.projections import project
        return project(request.sources)


def test_modal_port_candidate_and_review_no_plan_mutation(seeded,factory):
    with factory() as db:before=db.get(Event,seeded['event']).version
    mid=extracted(factory,seeded,'open_weight',FakeModal())
    with factory() as db:
        entry=db.get(MemoryEntry,mid);assert entry.lifecycle=='candidate';assert entry.model_profile==FakeModal.model_profile
        assert db.get(Event,seeded['event']).version==before
    hashed,revision,version=details(factory,mid)
    with unit_of_work(factory) as db:
        assert review(db,seeded['owner'],seeded['event'],mid,ReviewRequest(decision='publish',reviewed_digest=hashed,expected_revision=revision),'review','1')['lifecycle']=='published'
    with factory() as db:assert db.get(Event,seeded['event']).version==before


def test_fabricated_success_is_terminal_failure(seeded,factory):
    class Bad(FakeModal):
        def extract(self,r):
            result=super().extract(r);result[0].assertions[0].outcome='successful';result[0].assertions[0].evidence_stage='verified';return result
    with unit_of_work(factory) as db:r=enqueue(db,seeded['owner'],seeded['event'],request(seeded,'open_weight'))
    assert work_once(factory,Bad()) is False
    with factory() as db:
        run=db.get(MemoryRun,r['run_id']);assert run.status=='failed' and run.failure_code=='unsupported_outcome'
        assert db.scalar(select(func.count()).select_from(MemoryEntry))==0


def test_job_retry_and_lease_fencing(seeded,factory):
    class Broken(FakeModal):
        def extract(self,r):raise TimeoutError('should not leak provider secret')
    with unit_of_work(factory) as db:r=enqueue(db,seeded['owner'],seeded['event'],request(seeded,'open_weight'))
    assert work_once(factory,Broken()) is False
    with unit_of_work(factory) as db:
        task=db.scalar(select(JobTask));assert task.status=='retry' and task.last_error=='extractor_failed';task.available_at=now()-timedelta(seconds=1)
    lease=claim(factory,'old')
    with unit_of_work(factory) as db:db.get(JobTask,lease.job_id).lease_until=now()-timedelta(seconds=1)
    new=claim(factory,'new');assert new.token>lease.token
    assert process_lease(factory,lease,FakeModal()) is False
    assert process_lease(factory,new,FakeModal()) is True
    with factory() as db:assert db.scalar(select(func.count()).select_from(MemoryEntry))==1


def test_expired_final_attempt_cannot_stick(seeded,factory):
    with unit_of_work(factory) as db:
        enqueue(db,seeded['owner'],seeded['event'],request(seeded));task=db.scalar(select(JobTask));task.max_attempts=1
    lease=claim(factory,'dead')
    with unit_of_work(factory) as db:db.get(JobTask,lease.job_id).lease_until=now()-timedelta(seconds=1)
    assert claim(factory,'next') is None
    with factory() as db:assert db.get(JobTask,lease.job_id).status=='failed'


def test_source_changes_during_model_run_reject_output(seeded,factory):
    class Race(FakeModal):
        def extract(self,r):
            with unit_of_work(factory) as db:
                event=db.get(Event,seeded['event']);append_context(db,seeded['owner'],event.id,'Changed while extraction running',event.version)
            return super().extract(r)
    with unit_of_work(factory) as db:run=enqueue(db,seeded['owner'],seeded['event'],request(seeded,'open_weight'))
    assert work_once(factory,Race()) is False
    with factory() as db:
        assert db.get(MemoryRun,run['run_id']).status=='stale'
        assert db.scalar(select(func.count()).select_from(MemoryEntry))==0


def test_source_grant_revocation_removes_eligibility(seeded,factory):
    mid=extracted(factory,seeded)
    with unit_of_work(factory) as db:
        grant=db.scalar(select(EventGrant).where(EventGrant.user_id==seeded['owner'],EventGrant.permission=='source:private'));grant.active=False
    with factory() as db:assert retrieve(db,seeded['owner'],seeded['event'])['items']==[]


def test_muse_context_labels_and_revalidates(seeded,factory):
    with unit_of_work(factory) as db:
        e=db.get(Event,seeded['event']);append_plan(db,seeded['owner'],e.id,{'stages':[{'id':'s','title':'Workshop'}]},e.version)
    mid=extracted(factory,seeded)
    builder=MuseSparkContextBuilder()
    with factory() as db:
        built=builder.build(db,seeded['owner'],seeded['event']);assert built['authoritative_current']['plan']['stages'][0]['title']=='Workshop';assert built['derived_historical']['memory']['items'];builder.validate(db,seeded['owner'],seeded['event'],built)
    hashed,revision,version=details(factory,mid)
    with unit_of_work(factory) as db:retract(db,seeded['owner'],seeded['event'],mid,RetractionRequest(reason='Correction',reviewed_digest=hashed,expected_revision=revision),'ret','1')
    with factory() as db:
        with pytest.raises(DomainError,match='stale_memory'):builder.validate(db,seeded['owner'],seeded['event'],built)

@pytest.mark.parametrize('outcome',['successful','failed','inconclusive'])
def test_reviewed_observation_retains_exact_outcome(seeded,factory,outcome):
    with unit_of_work(factory) as db:
        e=db.get(Event,seeded['event']);source=append_context(db,seeded['owner'],e.id,'Human observation: projector test result',e.version,source_kind='observation')
        decision=record_observation_decision(db,seeded['owner'],e.id,source.id,'verified',outcome,'Test image visible for 10 minutes','Explicitly reviewed bounded observation')
        from app.shared.source_resolver import decision_digest
        payload={**seeded,'ref':{'source_kind':'decision','source_id':decision.id,'source_revision':1,'source_digest':decision_digest(decision)}}
    mid=extracted(factory,payload)
    with factory() as db:assert db.get(MemoryEntry,mid).assertions[0]['outcome']==outcome


def test_concurrent_extraction_deduplicates(seeded,factory):
    def enqueue_one(_):
        with unit_of_work(factory) as db:return enqueue(db,seeded['owner'],seeded['event'],request(seeded))['run_id']
    with ThreadPoolExecutor(max_workers=2) as pool:ids=list(pool.map(enqueue_one,range(2)))
    assert ids[0]==ids[1]
    with factory() as db:assert db.scalar(select(func.count()).select_from(JobTask))==1

@pytest.mark.parametrize('table',['event_context_revisions','plan_versions','review_decisions','audit_events','memory_sources'])
def test_immutable_tables_have_database_triggers(seeded,factory,table):
    with factory() as db:
        assert db.scalar(text("SELECT count(*) FROM pg_trigger WHERE tgname=:name"),{'name':'immutable_'+table})==1


def test_immutable_source_and_memory_content_rejected(seeded,factory):
    mid=extracted(factory,seeded)
    for sql in ["UPDATE event_context_revisions SET original_text='rewritten'", "UPDATE memory_entries SET title='rewritten'", "DELETE FROM memory_sources"]:
        with pytest.raises(DBAPIError):
            with unit_of_work(factory) as db:db.execute(text(sql))


def test_cross_event_source_fk_constraint(seeded,factory):
    from app.memory.models import MemoryEntry
    mid=extracted(factory,seeded)
    with pytest.raises(DBAPIError):
        with unit_of_work(factory) as db:
            db.add(MemorySource(event_id=seeded['other'],memory_entry_id=mid,assertion_id='forged',source_kind='context',source_id=seeded['source'],source_revision=1,source_digest='a'*64,source_state_at_capture='proposed',access_class='private'))
