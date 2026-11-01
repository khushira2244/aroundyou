import pytest
from sqlalchemy import select,func
from app.shared.unit_of_work import unit_of_work
from app.events.models import Event
from app.events.source_revisions import append_context,record_observation_decision
from app.shared.source_resolver import decision_digest
from app.memory.models import MemoryRun,MemoryEntry
from app.memory.service import enqueue
from app.memory.schemas import ExtractionRequest
from app.memory.worker import work_once
from app.memory.retrieval import retrieve
from app.access.models import EventGrant
from app.cli import provision
from app.api.errors import DomainError

def test_retrieval_manifest_is_persisted(seeded,factory):
    from test_group1 import extracted
    mid=extracted(factory,seeded)
    with unit_of_work(factory) as db:bundle=retrieve(db,seeded['owner'],seeded['event'])
    with factory() as db:
        run=db.get(MemoryRun,bundle['retrieval_id']);assert run.kind=='retrieval';assert run.selection_manifest[0]['memory_id']==mid;assert run.query_digest==bundle['query_digest']


def test_corrected_verification_invalidates_previous_outcome(seeded,factory):
    with unit_of_work(factory) as db:
        event=db.get(Event,seeded['event']);source=append_context(db,seeded['owner'],event.id,'Original inspection observation',event.version,source_kind='observation')
        decision=record_observation_decision(db,seeded['owner'],event.id,source.id,'verified','successful','Inspection criterion','Initially reviewed success')
        source_id=source.id;ref={'source_kind':'decision','source_id':decision.id,'source_revision':1,'source_digest':decision_digest(decision)}
        enqueue(db,seeded['owner'],event.id,ExtractionRequest(source_refs=[ref]))
    assert work_once(factory) is True
    with unit_of_work(factory) as db:
        record_observation_decision(db,seeded['owner'],seeded['event'],source_id,'verified','failed','Corrected inspection criterion','Correction after evidence review')
    with factory() as db:assert retrieve(db,seeded['owner'],seeded['event'])['items']==[]


def test_stage_scoped_grant_does_not_unlock_whole_event(seeded,factory):
    with unit_of_work(factory) as db:
        for grant in db.scalars(select(EventGrant).where(EventGrant.user_id==seeded['viewer'])):grant.scope={'stage_ids':['only-one-stage']}
    with factory() as db:
        with pytest.raises(DomainError,match='not_found'):retrieve(db,seeded['viewer'],seeded['event'])


def test_generic_provisioning_has_no_cleanup_template(seeded,factory):
    created=provision(factory,'teacher','Teacher','Neighborhood language lessons','Education','Organize language lessons for local adults')
    with factory() as db:
        event=db.get(Event,created['event_id']);assert event.title=='Neighborhood language lessons';assert event.active_plan_id is None


def test_read_only_viewer_cannot_review(seeded,factory,client,headers):
    from test_group1 import extracted,details,FakeModal
    mid=extracted(factory,seeded,'open_weight',FakeModal());hashed,rev,version=details(factory,mid)
    url=f"/v1/events/{seeded['event']}/memory/{mid}/review"
    assert client.post(url,json={'decision':'publish','reviewed_digest':hashed,'expected_revision':rev},headers=headers('viewer-subject')).status_code==404


def test_worker_no_provider_never_simulates_success(seeded,factory):
    with unit_of_work(factory) as db:
        run=enqueue(db,seeded['owner'],seeded['event'],ExtractionRequest(source_refs=[seeded['ref']],extractor='open_weight'))
    assert work_once(factory) is False
    with factory() as db:
        assert db.get(MemoryRun,run['run_id']).failure_code=='extractor_unavailable'
        assert db.scalar(select(func.count()).select_from(MemoryEntry))==0


def test_pagination_only_counts_eligible_rows_and_binds_query(seeded,factory):
    from test_group1 import extracted
    first=extracted(factory,seeded)
    with unit_of_work(factory) as db:
        event=db.get(Event,seeded['event'])
        from app.events.source_revisions import append_plan
        plan=append_plan(db,seeded['owner'],event.id,{'stages':[{'id':'s','title':'Reading'}]},event.version)
        enqueue(db,seeded['owner'],event.id,ExtractionRequest(source_refs=[{'source_kind':'plan','source_id':plan.id,'source_revision':plan.sequence,'source_digest':plan.digest}]))
    assert work_once(factory) is True
    with unit_of_work(factory) as db:
        a=retrieve(db,seeded['owner'],seeded['event'],limit=1)
        assert a['next_cursor'] and len(a['items'])==1
        b=retrieve(db,seeded['owner'],seeded['event'],limit=1,cursor=a['next_cursor'])
        assert len(b['items'])==1 and b['items'][0]['memory_id']!=a['items'][0]['memory_id']
        with pytest.raises(DomainError,match='invalid_cursor'):retrieve(db,seeded['owner'],seeded['event'],q='changed',cursor=a['next_cursor'])


def test_retry_backoff_and_attempt_exhaustion(seeded,factory):
    from test_group1 import FakeModal
    from app.shared.models import JobTask
    from app.shared.types import now
    from datetime import timedelta
    class Broken(FakeModal):
        def extract(self,r):raise TimeoutError('not stored')
    with unit_of_work(factory) as db:
        run=enqueue(db,seeded['owner'],seeded['event'],ExtractionRequest(source_refs=[seeded['ref']],extractor='open_weight'))
    for n in range(3):
        assert work_once(factory,Broken()) is False
        if n<2:
            assert work_once(factory,Broken()) is None
            with unit_of_work(factory) as db:db.scalar(select(JobTask)).available_at=now()-timedelta(seconds=1)
    with factory() as db:
        task=db.scalar(select(JobTask));assert task.status=='failed' and task.attempt_count==3
        assert db.get(MemoryRun,run['run_id']).status=='failed'


def test_health_and_openapi_are_available_without_identity(client):
    assert client.get('/health').json()['status']=='ok'
    document=client.get('/openapi.json').json()
    assert '/v1/events/{event_id}/memory/extractions' in document['paths']
    assert '/v1/events/{event_id}/memory/{memory_id}/corrections' in document['paths']
