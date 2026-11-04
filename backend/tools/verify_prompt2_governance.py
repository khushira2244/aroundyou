"""Exactly two additional calls; requires separate explicit user approval."""
import json
import sys
from fastapi.testclient import TestClient
from app.settings import Settings
from app.main import create_app
from app.shared.database import database
from app.access.models import User
from app.access.authentication import issue_token
from app.events.models import Event
from app.ai.models import AIProposal
from app.shared.types import uid
from tools.verify_prompt2_live import BoundedProvider,ROOT,REPORT
from tests.test_group2 import FORM
import app.models

if '--approved-two-governance-tests' not in sys.argv:raise SystemExit('Separate approval required')
class GovernanceTestProvider(BoundedProvider):spark_limit=6
saved=json.loads(REPORT.read_text());education_id=saved['events'][-1]
settings=Settings();engine,factory=database(settings.database_url.get_secret_value())
with factory() as db:
    user=db.get(User,db.get(Event,education_id).creator_id);token=issue_token(settings,user.external_auth_subject)
provider=GovernanceTestProvider(settings.meta_api_key.get_secret_value(),settings.meta_model_id)
report={'transport':'FastAPI TestClient → Meta → real PostgreSQL','browser_verified':False,'events':[]}
with TestClient(create_app(settings,factory,planning_adapter=provider)) as client:
    event_id=education_id
    def call(suffix,body={},method='POST',absolute=False):
        h={'Authorization':'Bearer '+token,'Idempotency-Key':uid()}
        if event_id:h['If-Match']=str(client.get('/v1/events/'+event_id,headers=h).json()['data']['version'])
        response=client.request(method,'/v1'+(suffix if absolute else '/events/'+event_id+suffix),json=body if method!='GET' else None,headers=h)
        if response.status_code>=400:raise RuntimeError('API '+str(response.status_code)+' '+response.json().get('error',{}).get('code','unknown'))
        return response.json()['data']
    try:
        for category in ('Education','Health'):
            if category=='Health':
                state=call('/events/drafts',absolute=True);event_id=state['event']['id']
                form={**FORM,'title':'Private Prompt 2 health awareness verification','category':'Health','purpose':'Explain basic first aid and emergency contacts','goal':'Residents learn emergency preparedness; no diagnosis or treatment','workScope':'First aid demonstrations and community health awareness','executionIntent':'We plan a health awareness meeting for 150 residents in Hazaribagh. Trained demonstrators will explain first aid. No diagnosis, medication or clinical treatment will be provided. Venue access, crowd safety and emergency arrangements need confirmation.','expectedAttendees':'150'}
                call('/draft',{'step':3,'form':form},'PATCH');ctx=call('/creation',method='GET')['context']
                call('/context-interpretations',{'context_version':ctx['version'],'interpretation':{'scope':[form['workScope']],'reported_facts':[form['executionIntent']],'unknowns':['Venue authorization and emergency arrangements']}})
            run=call('/governance/assessments');result=call('/ai-runs/'+run['run_id'],method='GET',absolute=True)
            if result['status']!='succeeded':raise RuntimeError('Live governance '+result['status']+': '+str(result.get('error')))
            p=call('/governance',method='GET')['proposals'][0]
            call('/governance/proposals/'+p['id']+'/review',{'decision':'accept','reviewed_digest':p['digest']})
            ticket=call('/governance/tickets')['ticket'];call('/governance/tickets/'+ticket['id'],{'status':'in_review','note':'Private verification only. No external approval.','responsible_party':'Verification organizer'},'PATCH')
            call('/governance/tickets/'+ticket['id']+'/documents',{'name':'Private verification venue notes','document_type':'venue','document_reference':'Organizer verification folder'})
            a=call('/governance',method='GET');b=call('/governance',method='GET');assert a['items']==b['items']
            with factory() as db:
                proposal=db.get(AIProposal,p['id']);metadata=proposal.provenance['provider_metadata']
            entry={'event_id':event_id,'category':category,'run_id':run['run_id'],'titles':[i['title'] for i in a['items']],'metadata':metadata,'ticket_id':ticket['id'],'saved_reads_no_inference':True,'permission_status':a['guidance']['permission_status']}
            if category=='Education':
                voice=json.loads((ROOT/'.tmp'/'prompt2-voice-results.json').read_text())['data']['data']
                reviewed=voice['transcript'].replace('Hazaribag.','Hazaribagh.')
                call('/context-revisions',{'text':reviewed,'source':'reviewed_transcript','transcript_run_id':voice['id']})
                entry['stale_after_reviewed_transcript_change']=call('/governance',method='GET')['guidance']['status']=='stale_reassessment_required'
            report['events'].append(entry)
    except Exception as exc:report['failure']=str(exc)
(ROOT/'.tmp'/'prompt2-governance-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2));engine.dispose()
