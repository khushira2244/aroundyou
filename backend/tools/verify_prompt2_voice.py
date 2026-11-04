"""One explicitly approved real transcription of a local synthesized test recording."""
import json
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.settings import Settings
from app.main import create_app
from app.shared.database import database
from app.access.models import User
from app.access.authentication import issue_token
from app.events.models import Event
from app.ai.models import AIRun
from app.shared.types import uid
from tools.verify_prompt2_live import BoundedProvider,ROOT,REPORT
import app.models

if '--approved-bounded-tests' not in sys.argv:raise SystemExit('Explicit approved test flag required')
saved=json.loads(REPORT.read_text());event_id=saved['events'][-1]
settings=Settings();engine,factory=database(settings.database_url.get_secret_value())
with factory() as db:
    user=db.get(User,db.get(Event,event_id).creator_id);token=issue_token(settings,user.external_auth_subject)
provider=BoundedProvider(settings.meta_api_key.get_secret_value(),settings.meta_model_id)
with TestClient(create_app(settings,factory,planning_adapter=provider)) as client:
    path='/v1/events/'+event_id+'/voice-transcriptions'
    with (ROOT/'.tmp'/'prompt2-spoken-test.wav').open('rb') as audio:
        response=client.post(path,headers={'Authorization':'Bearer '+token,'Idempotency-Key':uid()},files={'audio':('synthetic-test-speech.wav',audio,'audio/wav')})
    result={'input':'Locally synthesized test speech, not browser microphone','http_status':response.status_code,'data':response.json()}
    (ROOT/'.tmp'/'prompt2-voice-results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
engine.dispose()
