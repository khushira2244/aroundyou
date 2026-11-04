"""Reparse the saved genuine SAM response locally; absolutely no provider transport."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.execution.media import segment
from app.execution.models import EvidenceAsset
from app.ai.models import AIRun
from app.events.models import Event
from app.settings import Settings
from app.main import create_app
from app.shared.database import database
from app.shared.unit_of_work import unit_of_work
from app.shared.audit import audit
folder=ROOT/'.tmp/sam-garbage';path=folder/'1-result.json';saved=json.loads(path.read_text());response=json.loads((folder/'1-raw.json').read_text())
settings=Settings(meta_ai_enabled=False);engine,factory=database(settings.database_url.get_secret_value());app=create_app(settings,factory)
class SavedResponse:
    def send(self,path,**kwargs):
        assert path=='/responses'
        return response
with unit_of_work(factory) as db:
    run=db.get(AIRun,saved['run_id']);asset=db.get(EvidenceAsset,saved['evidence_id']);raw=app.state.evidence_storage.get(asset.content['storage_key'])
    assert hashlib.sha256(raw).hexdigest()==asset.content['sha256']==run.source_versions['sha256']==saved['input_sha256']
    assert asset.event_id==run.event_id==saved['event_id'] and asset.report_id==saved['report_id']
    segmentation,_=segment(SavedResponse(),raw,'image/png',saved['concept']);original=saved['segmentation'];saved['segmentation']=segmentation;saved['source_persistence_verified']=True;saved['reparsed_without_inference']=True
    run.context_manifest={'result':saved,'raw_provider_response':response,'previous_normalization':original};audit(db,run.requester_id,run.event_id,'sam.verification.reparsed',run.id)
    summary=[{**b,'pixel_bounds_inclusive':[round(b['x']*637),round(b['y']*424),round((b['x']+b['width'])*637)-1,round((b['y']+b['height'])*424)-1]} for b in segmentation['boxes']]
    print(json.dumps({'source_verified':True,'live_requests':len(json.loads((folder/'budget.json').read_text())),'boxes':summary},indent=2))
path.write_text(json.dumps(saved,indent=2));engine.dispose()
