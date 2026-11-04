"""One explicit SAM-only probe. Never calls Spark; persisted budget prevents reruns."""
import sys,json,hashlib,base64,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PIL import Image
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.settings import Settings
from app.main import create_app
from app.shared.database import database
from app.shared.unit_of_work import unit_of_work
from app.shared.types import uid
from app.shared.audit import audit
from app.access.models import User
from app.access.authentication import issue_token
from app.events.models import Event
from app.participation.models import Assignment,AssignmentTerms
from app.execution.models import EvidenceAsset,WorkReport
from app.ai.models import AIRun
from app.ai.meta_provider import MetaProvider
from app.execution.media import segment
from tests.test_group3 import Scenario
from tests.test_prompt56_media import attach
folder=ROOT/'.tmp/sam-garbage';folder.mkdir(parents=True,exist_ok=True)
concept=sys.argv[1] if len(sys.argv)>1 else 'garbage bag'
assert concept in ('garbage bag','plastic cup')
budget=folder/'budget.json';calls=json.loads(budget.read_text()) if budget.exists() else []
assert len(calls)<2 and concept not in calls,'No automatic paid retries'
source=Path('C:/Users/Khushboo/AppData/Local/Temp/codex-clipboard-3570826a-1513-4656-8ccc-df2dd2cc685c.png');raw=source.read_bytes();sha=hashlib.sha256(raw).hexdigest()
with Image.open(source) as im:dimensions=list(im.size)
settings=Settings(meta_ai_enabled=False);engine,factory=database(settings.database_url.get_secret_value());eid=json.loads((ROOT/'.tmp/prompt56-http-results.json').read_text())['event_id']
with factory() as db:
    e=db.get(Event,eid);owner=db.get(User,e.creator_id).external_auth_subject;a=db.scalar(select(Assignment).where(Assignment.event_id==eid,Assignment.status=='assignment_accepted'));person=db.get(User,a.account_id).external_auth_subject;pid=a.account_id;wid=db.get(AssignmentTerms,a.current_terms_id).content['work_ids'][0]
def headers(subject='owner-subject',key='sam-test',version='1'):return {'Authorization':'Bearer '+issue_token(settings,owner if subject=='owner-subject' else subject),'Idempotency-Key':key,'If-Match':str(version)}
app=create_app(settings,factory)
with TestClient(app) as client:
    s=Scenario(client,headers,factory);s.flow.id=eid;s.subject=person;s.work=wid
    r=s.call('/reports/draft',{'work_id':wid,'body':'Independent SAM verification of user-provided garbage photograph. Not evidence of this synthetic education activity. No completion claimed.','claim':'progress','progress_percent':0},person)['report']
    asset,revision=attach(s,r,raw,'image','image/png','user-garbage-segmentation.png')
    aid=asset['id'];rid=uid()
    with unit_of_work(factory) as db:
        row=db.get(EvidenceAsset,aid);report=db.get(WorkReport,r['id']);assert app.state.evidence_storage.get(row.content['storage_key'])==raw
        db.add(AIRun(id=rid,event_id=eid,requester_id=pid,kind='sam_verification',status='running',source_versions={'asset_id':aid,'asset_revision':row.version,'sha256':sha,'report_id':report.id,'report_revision':report.version,'plan_id':report.plan_id},context_manifest={},request_message=concept,model_profile='sam-3.1'));audit(db,pid,eid,'sam.verification.request',rid)
    result={'run_id':rid,'evidence_id':aid,'report_id':r['id'],'event_id':eid,'concept':concept,'input_dimensions':dimensions,'input_sha256':sha,'input_bytes':len(raw),'spark_calls':0}
    class Capture(httpx.Client):
        def post(self,url,**kwargs):
            assert url.endswith('/responses')
            payload=kwargs['json'];actual=base64.b64decode(payload['input'][0]['content'][1]['image_url'].split(',',1)[1]);assert actual==raw
            calls.append(concept);budget.write_text(json.dumps(calls))
            response=super().post(url,**kwargs);result['http_status']=response.status_code
            try:value=response.json()
            except ValueError:value={'non_json_response':response.text[:2000]}
            (folder/(str(len(calls))+'-raw.json')).write_text(json.dumps(value))
            result['response_keys']=list(value);result['response_model']=value.get('model');result['raw_structure']=[{'type':x.get('type'),'keys':list(x),'content':[{'type':c.get('type'),'keys':list(c)} for c in x.get('content',[])]} for x in value.get('output',[])]
            wire=json.dumps(value);result['raw_box_tokens']=wire.count('<|box;');result['raw_mask_tokens']=wire.count('<|mask;');result['raw_object_records']=len(re.findall(r'\d+<\|box;',wire));result['top_level_output_text_present']='output_text' in value
            return response
    try:
        with Capture() as transport:
            provider=MetaProvider(settings.meta_api_key.get_secret_value(),settings.meta_model_id,client=transport);seg,_=segment(provider,raw,'image/png',concept)
        result['normalized_boxes']=len(seg['boxes']);result['segmentation']=seg;result['status']='succeeded'
    except Exception as exc:result['status']='failed';result['error']=getattr(exc,'code',type(exc).__name__)
    with unit_of_work(factory) as db:
        run=db.get(AIRun,rid);run.status=result['status'];run.context_manifest={'result':result};run.failure_code=result.get('error');audit(db,pid,eid,'sam.verification.saved',rid)
    (folder/(str(len(calls))+'-result.json')).write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='segmentation'},indent=2))
engine.dispose()
