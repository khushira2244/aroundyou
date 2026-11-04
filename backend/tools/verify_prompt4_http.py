"""Explicit local HTTP integration check; no model calls, no database resets."""

import json,secrets,socket,threading,time,sys

from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx,uvicorn

from app.main import create_app

from app.settings import Settings

from app.shared.database import database

from tests.test_group2 import FORM

ROOT=Path(__file__).resolve().parents[1]



def main():

    settings=Settings(meta_ai_enabled=False);engine,factory=database(settings.database_url.get_secret_value())

    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]

    server=uvicorn.Server(uvicorn.Config(create_app(settings,factory),host='127.0.0.1',port=port,log_level='error',access_log=False))

    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()

    for _ in range(100):

        if server.started:break

        time.sleep(.1)

    report={'transport':'actual loopback HTTP','browser_verified':False,'ai_calls':0,'checks':[]};tag=secrets.token_hex(5)

    origin={'Origin':'http://127.0.0.1:5173'}

    clients=[httpx.Client(base_url=f'http://127.0.0.1:{port}/v1',headers=origin,timeout=30) for _ in range(3)]

    owner,sponsor,outsider=clients

    def checked(r):

        if r.status_code>=400:raise RuntimeError(str(r.status_code)+' '+r.json().get('error',{}).get('code','unknown'))

        return r.json()['data']

    try:

        for client,kind in [(owner,'personal'),(sponsor,'sponsor'),(outsider,'personal')]:

            email=tag+'-'+kind+('-other' if client is outsider else '')+'@example.test';password=secrets.token_urlsafe(24)

            checked(client.post('/auth/signup',json={'name':'Prompt 4 integration test '+kind,'email':email,'password':password,'kind':kind}))

            checked(client.post('/auth/logout'));checked(client.post('/auth/signin',json={'email':email,'password':password}))

        report['checks'].append('Real signup, logout and signin for organizer and sponsor')

        result=checked(owner.post('/events/drafts',json={},headers={'Idempotency-Key':secrets.token_hex(12)}));eid=result['event']['id'];base='/events/'+eid;report['event_id']=eid

        def post(client,path,body=None,method='POST'):

            version=checked(owner.get(base))['version']

            return checked(client.request(method,path,json=body or {},headers={'Idempotency-Key':secrets.token_hex(12),'If-Match':str(version)}))

        form={**FORM,'title':'Integration verification — community education '+tag,'purpose':'Synthetic local HTTP verification, not an actual scheduled initiative','goal':'Test publication and sponsor accounting; no actual contribution claimed','executionIntent':'Synthetic integration-test event. No actual gathering or delivery occurs.','coordinates':{'lat':23.99,'lng':85.36},'locationSource':'integration_test_approximate','venue':'Integration test locality — venue unverified'}

        post(owner,base+'/draft',{'step':4,'form':form},'PATCH');post(owner,base+'/confirm-creation',{'expected_draft_version':checked(owner.get(base))['version']})

        post(owner,base+'/planning/draft');sid=post(owner,base+'/planning/items/stages',{'title':'Integration test preparation','relative_start':1,'relative_end':1})['id']

        def confirm(kind):post(owner,base+'/planning/'+kind+'-confirmations',{'expected_draft_version':checked(owner.get(base+'/planning'))['draft_version']})

        confirm('stage');wid=post(owner,base+'/planning/items/work',{'stage_id':sid,'title':'Test education material setup','effort':{'value':2,'unit':'person_hours'}})['id']

        rid=post(owner,base+'/planning/items/resources',{'title':'Integration-test workbooks','kind':'consumable','quantity':10,'unit':'books','work_ids':[wid]})['id']

        post(owner,base+'/planning/items/work/'+wid,{'resource_requirement_ids':[rid]},'PATCH');confirm('work');post(owner,base+'/planning/actor-derivations');confirm('actor');post(owner,base+'/setup/draft')

        post(owner,base+'/setup/sections/location',{'data':{'access_instructions':'Synthetic test; not an actual venue','emergency_contact':'PRIVATE-TEST-NOT-PUBLIC'}},'PATCH')

        post(owner,base+'/setup/sections/participation',{'data':{'visibility':'public','approval_required':True,'show_open_roles':True,'allow_groups':False,'registration_open':True}},'PATCH')

        setup=checked(owner.get(base+'/setup'));final=post(owner,base+'/finalizations',{'confirm_review':True,'expected_setup_version':setup['configuration']['revision'],'expected_plan_id':setup['plan_id']})

        post(owner,base+'/publications',{'finalization_id':final['finalization_id']})

        public=checked(sponsor.get(base+'/profile'));assert public['event']['location']['coordinates']==form['coordinates'];assert 'PRIVATE-TEST-NOT-PUBLIC' not in json.dumps(public)

        assert any(e['id']==eid for e in checked(sponsor.get('/events?limit=100'))['items'])

        report['checks'].append('Setup persisted, explicit finalization/publication, public discovery/profile coordinates and privacy')

        org=checked(sponsor.post('/organizations/draft',json={'profile':{'name':'Integration Test Sponsor '+tag,'type':'Business','description':'Synthetic integration test only','contact_name':'Test representative','email':tag+'@example.test','city':'Hazaribagh','country':'India','focus':['Education'],'capabilities':['materials'],'coverage':['Hazaribagh']}},headers={'Idempotency-Key':secrets.token_hex(12)}))['organization_id']

        checked(sponsor.post('/organizations/'+org+'/registration/complete',json={},headers={'Idempotency-Key':secrets.token_hex(12)}))

        def portal():return checked(sponsor.get('/me/sponsor-portal'))

        assert any(e['id']==eid for e in portal()['opportunities'])

        offer=post(sponsor,'/organizations/'+org+'/offers',{'event_id':eid,'resource_id':rid,'support_type':'materials','quantity':10,'unit':'books','description':'Synthetic integration-test offer, no actual goods','submit':True})['offer']

        post(owner,base+'/sponsor-offers/'+offer['id']+'/revision-requests',{'body':'Test clarification: delivery report must state synthetic verification'})

        assert portal()['offers'][0]['revision_request']['body']

        post(owner,base+'/sponsor-offers/'+offer['id']+'/accept')

        assert portal()['stats']['accepted']==1 and portal()['stats']['verified_contributions']==0

        f=post(sponsor,'/organizations/'+org+'/offers/'+offer['id']+'/fulfillment-reports',{'quantity':4,'reference':'test-report-'+tag,'evidence_reference':'SYNTHETIC integration check; no actual goods received'})

        assert checked(owner.get(base+'/resources'))['resources'][0]['available']==0

        post(owner,base+'/resource-receipts',{'offer_id':offer['id'],'fulfillment_id':f['fulfillment_id'],'resource_id':rid,'quantity':4,'unit':'books','reference':'test-receipt-'+tag,'evidence_reference':'SYNTHETIC integration check; not a real delivery'})

        p=portal();assert p['stats']['verified_contributions']==1 and p['stats']['completed']==0 and p['offers'][0]['verified']==4 and p['offers'][0]['fulfillment_status']=='partially_fulfilled'

        assert p['supported_events'][0]['location']['coordinates']==form['coordinates'] and p['fulfillments'][0]['status']=='verified'

        assert checked(owner.get(base+'/resources'))['resources'][0]['available']==4

        assert portal()['offers']==p['offers']

        assert outsider.get('/organizations/'+org+'/sponsor-portal').status_code==404

        assert outsider.get(base+'/organizer/sponsor-offers').status_code==404

        report['checks'].append('Offer, organizer clarification/acceptance, separate partial report/receipt, sponsor map/history stats, persistence and outsider denial')

        report.update({'organization_id':org,'offer_id':offer['id'],'verified_test_quantity':4,'remaining_commitment':6,'result':'passed','synthetic_test_records':True})

    except Exception as exc:report.update({'result':'failed','failure':str(exc)})

    finally:

        for c in clients:c.close()

        server.should_exit=True;thread.join(timeout=10);sock.close();engine.dispose()

        (ROOT/'.tmp'/'prompt4-http-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))

if __name__=='__main__':main()

