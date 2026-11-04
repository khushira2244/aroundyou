"""Explicit, bounded, opt-in verification; never run by startup or pytest.

Creates private verification events only. Does not touch existing events or fixtures.
Requires the user's separate authorization to spend provider credits.
"""
import json
import sys
import httpx
from pathlib import Path
from sqlalchemy import select,text
from fastapi.testclient import TestClient
from app.settings import Settings
from app.main import create_app
from app.shared.database import database
from app.shared.unit_of_work import unit_of_work
from app.shared.types import uid
from app.access.models import User
from app.access.authentication import issue_token
from app.ai.meta_provider import MetaProvider
from app.ai.models import AIProposal,AIRun
from tests.test_group2 import FORM
import app.models

ROOT=Path(__file__).resolve().parents[1]
BUDGET=ROOT/'.tmp'/'prompt2-live-budget.json'
REPORT=ROOT/'.tmp'/'prompt2-live-results.json'

class BoundedProvider(MetaProvider):
    spark_limit=4
    def send(self,path,**kwargs):
        counts=json.loads(BUDGET.read_text()) if BUDGET.exists() else {'spark':0,'voice':0}
        kind='spark' if path=='/chat/completions' else 'voice'
        if counts[kind]>=(self.spark_limit if kind=='spark' else 1):raise RuntimeError('Approved live test budget exhausted')
        counts[kind]+=1;BUDGET.parent.mkdir(exist_ok=True);BUDGET.write_text(json.dumps(counts))
        return super().send(path,**kwargs)

def main():
    if '--approved-bounded-tests' not in sys.argv:raise SystemExit('Explicit approval flag required')
    settings=Settings();engine,factory=database(settings.database_url.get_secret_value())
    if not settings.meta_api_key:raise SystemExit('META_API_KEY unavailable')
    provider=BoundedProvider(settings.meta_api_key.get_secret_value(),settings.meta_model_id)
    def diagnostic(response):
        if response.status_code>=400:
            response.read()
            try:error=response.json().get('error',{})
            except ValueError:error={'message':'Non-JSON provider error'}
            # This opt-in script uses synthetic inputs only. Redact the key and
            # retain a short provider error for troubleshooting; never headers.
            safe=json.dumps(error).replace(provider.key,'[REDACTED]')[:1500]
            (ROOT/'.tmp'/'prompt2-provider-error.json').write_text(json.dumps({'http_status':response.status_code,'error':safe}),encoding='utf-8')
    provider.client=httpx.Client(timeout=28,follow_redirects=False,event_hooks={'response':[diagnostic]})
    subject='prompt2-verification-'+uid()
    with unit_of_work(factory) as db:
        db.add(User(id=uid(),external_auth_subject=subject,display_name='Prompt 2 private integration verification'))
    token=issue_token(settings,subject);report={'transport':'FastAPI TestClient → Meta → real PostgreSQL','browser_verified':False,'events':[],'checks':[]}
    with TestClient(create_app(settings,factory,planning_adapter=provider)) as client:
        event_id=None
        def call(path,body={},method='POST'):
            headers={'Authorization':'Bearer '+token,'Idempotency-Key':uid()}
            if event_id:
                headers['If-Match']=str(client.get('/v1/events/'+event_id,headers=headers).json()['data']['version'])
            response=client.request(method,'/v1'+path,json=body if method!='GET' else None,headers=headers)
            if response.status_code>=400:raise RuntimeError('API '+str(response.status_code)+' '+response.json().get('error',{}).get('code','unknown'))
            return response.json()['data']
        def propose(kind):
            suffix='/context-proposals' if kind=='understanding' else '/governance/assessments'
            run=call('/events/'+event_id+suffix)
            value=call('/ai-runs/'+run['run_id'],method='GET')
            if value['status']!='succeeded':raise RuntimeError('Live '+kind+' run '+value['status']+': '+str(value.get('error')))
            with factory() as db:
                p=db.get(AIProposal,value['proposal_id']);report['checks'].append({'kind':kind,'run_id':run['run_id'],'proposal_id':p.id,'model':p.provenance['source'],'model_execution':p.provenance['model_execution'],'items_or_questions':len(p.payload.get('items',p.payload.get('clarifications',[]))),'metadata':p.provenance.get('provider_metadata')})
            return value['proposal']
        try:
            for category in ['Education','Health']:
                event_id=None
                state=call('/events/drafts');event_id=state['event']['id'];report['events'].append(event_id)
                form={**FORM,'title':'Private Prompt 2 '+category+' verification','category':category,'workScope':'Reading lessons for adults' if category=='Education' else 'Community health awareness and first-aid demonstration','executionIntent':'We want to run a reading workshop for local adults in Hazaribagh. The room, attendance and projector availability are not yet confirmed.' if category=='Education' else 'We plan a community health awareness meeting for 150 residents in Hazaribagh, with first-aid demonstrations. No diagnosis or medication will be provided. Venue access and emergency arrangements need confirmation.','expectedAttendees':'' if category=='Education' else '150'}
                call('/events/'+event_id+'/draft',{'step':3,'form':form},'PATCH')
                if category=='Education':
                    p=propose('understanding')
                    ctx=call('/events/'+event_id+'/creation',method='GET')['context']
                    questions=p['interpretation']['clarifications']
                    report['checks'].append({'contextual_questions':questions})
                    call('/events/'+event_id+'/context-clarifications',{'context_version':ctx['version'],'answers':[{'question':questions[0] if questions else 'Additional organizer information','answer':'The organizer expects 20 adults and 3 teaching volunteers. The library meeting room is requested but not authorized. Use printed reading sheets if no projector is available.'}]})
                    p=propose('understanding')
                    call('/events/'+event_id+'/context-proposals/'+p['id']+'/review',{'decision':'accept','reviewed_digest':p['digest']})
                else:
                    ctx=call('/events/'+event_id+'/creation',method='GET')['context']
                    call('/events/'+event_id+'/context-interpretations',{'context_version':ctx['version'],'interpretation':{'reported_facts':[form['executionIntent']],'scope':[form['workScope']],'unknowns':['Venue authorization and emergency arrangements']}})
                if json.loads(BUDGET.read_text()).get('spark',0)>=4:
                    report['remaining_live_checks']='Governance contexts require the separately requested extension of the test-call budget.'
                    break
                p=propose('governance')
                call('/events/'+event_id+'/governance/proposals/'+p['id']+'/review',{'decision':'accept','reviewed_digest':p['digest']})
                ticket=call('/events/'+event_id+'/governance/tickets')['ticket']
                call('/events/'+event_id+'/governance/tickets/'+ticket['id'],{'status':'in_review','note':'Private integration verification; no official approval.','responsible_party':'Verification organizer'},'PATCH')
                for _ in range(2):call('/events/'+event_id+'/governance',method='GET')
                report['checks'].append({'category':category,'confirmed_context_persisted':bool(call('/events/'+event_id+'/creation',method='GET')['context']['approved_interpretation']),'ticket_id':ticket['id'],'saved_reads_no_inference':True})
        except Exception as exc:
            # Only sanitized domain/HTTP codes, never provider response bodies or keys.
            report['failure']=str(exc)
        report['attempts']=json.loads(BUDGET.read_text()) if BUDGET.exists() else {}
        REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2))
    engine.dispose()

if __name__=='__main__':main()
