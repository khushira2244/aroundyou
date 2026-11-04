"""One explicitly approved synthetic live extraction. Durable one-shot guard; no retries."""
import json,sys,time
from pathlib import Path
from datetime import timedelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import app.models
import httpx
from sqlalchemy import select
from app.settings import Settings
from app.shared.database import database
from app.shared.types import now
from app.shared.jobs import Lease
from app.shared.models import JobTask
from app.events.models import Event
from app.execution.models import ExecutionRevision
from app.memory.models import MemoryRun,MemoryEntry,MemorySource
from app.memory.schemas import ExtractionRequest,SourceRef,ReviewRequest
from app.memory.service import enqueue,review
from app.memory.worker import process_lease
from app.memory.modal_adapter import ModalHTTPExtractor
from app.memory.repository import eligible
from app.api.errors import DomainError

EVENT='01b19638-0f30-47ff-af9f-cfc51bde2354'
OUT=ROOT/'.tmp/modal-live-result.json';GUARD=ROOT/'.tmp/modal-live-attempted.json'
STRUCTURED_V2='--structured-v2' in sys.argv
if STRUCTURED_V2:
    OUT=ROOT/'.tmp/modal-structured-v2-result.json';GUARD=ROOT/'.tmp/modal-structured-v2-attempted.json'

def main():
    if GUARD.exists():raise SystemExit('One-shot guard exists. No additional inference allowed.')
    settings=Settings();_,factory=database(settings.database_url.get_secret_value())
    result={'event_id':EVENT,'inference_requests':0,'synthetic':True}
    with factory.begin() as db:
        e=db.get(Event,EVENT);assert e and e.memory_data_class=='synthetic'
        actor=e.creator_id
        source=db.scalar(select(ExecutionRevision).where(ExecutionRevision.event_id==EVENT,ExecutionRevision.kind=='recovery.outcome'))
        assert source and source.content['record']['data_class']=='synthetic'
        request=ExtractionRequest(extractor='open_weight',purpose='blocker_recovery' if STRUCTURED_V2 else 'event_review',source_refs=[SourceRef(source_kind='execution',source_id=source.id,source_revision=source.sequence,source_digest=source.digest)])
        run=enqueue(db,actor,EVENT,request,live=True);result['run_id']=run['run_id'];result['source_id']=source.id
        task=db.scalar(select(JobTask).where(JobTask.run_id==run['run_id']).with_for_update())
        assert task.status=='queued' and task.attempt_count==0 and task.max_attempts==1
        task.status='running';task.attempt_count=1;task.fencing_token+=1;task.lease_owner='approved-one-shot';task.lease_until=now()+timedelta(seconds=300)
        db.get(MemoryRun,run['run_id']).status='running'
        lease=Lease(task.id,run['run_id'],task.fencing_token,'approved-one-shot')
    class OneShot(httpx.BaseTransport):
        def __init__(self):self.inner=httpx.HTTPTransport(retries=0)
        def handle_request(self,request):
            # Exclusive creation survives process crashes and blocks accidental reruns.
            with GUARD.open('x') as f:json.dump({'run_id':run['run_id'],'attempted_at':now().isoformat()},f)
            result['inference_requests']+=1
            start=time.perf_counter()
            try:
                response=self.inner.handle_request(request);response.read()
                result['http_status']=response.status_code
                try:result['provider_response']=response.json()
                except ValueError:result['provider_error_excerpt']=response.text[:1000]
                return response
            finally:result['http_elapsed_seconds']=round(time.perf_counter()-start,3)
        def close(self):self.inner.close()
    with httpx.Client(transport=OneShot(),follow_redirects=False) as client:
        adapter=ModalHTTPExtractor(settings.modal_memory_endpoint,settings.modal_memory_proxy_key.get_secret_value(),settings.modal_memory_proxy_secret.get_secret_value(),client,allow_synthetic_test=True)
        result['worker_success']=process_lease(factory,lease,adapter)
    with factory() as db:
        run_record=db.get(MemoryRun,run['run_id']);result['run_status']=run_record.status;result['failure_code']=run_record.failure_code
        result['candidates']=[]
        for mid in run_record.output_entry_ids:
            entry=db.get(MemoryEntry,mid)
            result['candidates'].append({'id':mid,'lifecycle':entry.lifecycle,'eligible':eligible(db,actor,entry),'source_links':len(list(db.scalars(select(MemorySource).where(MemorySource.memory_entry_id==mid))))})
            assert entry.lifecycle=='candidate' and not eligible(db,actor,entry)
            # Roll back attempted publication; required provenance guard must reject it.
            with factory.begin() as check:
                try:review(check,actor,EVENT,mid,ReviewRequest(decision='publish',expected_revision=entry.revision,reviewed_digest=entry.digest),'modal-synthetic-publish-denial',str(entry.version))
                except DomainError as exc:
                    assert exc.code=='synthetic_memory';result['synthetic_publication_blocked']=True
                else:raise AssertionError('Synthetic lesson publication was permitted')
        assert db.get(Event,EVENT).memory_data_class=='synthetic'
    OUT.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='provider_response'},indent=2))
if __name__=='__main__':main()
