from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import uuid
import pytest
from sqlalchemy import select,func,text
from sqlalchemy.exc import DBAPIError
from tests.test_group2 import Flow,FORM
from app.access.models import User
from app.events.models import Event
from app.participation.models import Application,ApplicationRevision,Assignment,AssignmentConsent,OperationalSource
from app.resources.models import ResourceTransaction
from app.sponsorship.models import SupportOfferRevision
from app.shared.unit_of_work import unit_of_work
from app.shared.types import uid
from app.ai.service import work_ai_once
from app.ai.models import AIRun

class Scenario:
    def __init__(self,client,headers,factory):self.client=client;self.headers=headers;self.factory=factory;self.flow=Flow(client,headers);self.people=[]
    @property
    def id(self):return self.flow.id
    def person(self,n):
        subject='participant-'+str(n)+'-'+uuid.uuid4().hex;id=uid()
        with unit_of_work(self.factory) as db:db.add(User(id=id,external_auth_subject=subject,display_name='Participant '+str(n)))
        self.people.append((subject,id));return subject,id
    def call(self,path,body=None,subject='owner-subject',method='POST',expected=200,key=None,version=None):
        url='/v1/events/'+self.id+path
        if version is None:
            read=self.client.get('/v1/events/'+self.id+('/participation/me' if subject!='owner-subject' else ''),headers=self.headers(subject));assert read.status_code==200,read.text
            version=read.json()['meta']['version'] if subject!='owner-subject' else read.json()['data']['version']
        r=self.client.request(method,url,json=body or {},headers=self.headers(subject,key=key or uuid.uuid4().hex,version=str(version)))
        assert r.status_code==expected,r.text
        return r.json().get('data')
    def build(self,capacity=3,category='Education',resource=False,skills=None):
        f=self.flow;f.new('Canary Hill demonstration' if category=='Environment' else 'Community reading workshop')
        if category=='Environment':f.call('/draft',{'step':4,'form':{**FORM,'category':category,'executionIntent':'Assess six included zones; exclude maintained front park. No completed cleanup claimed.','title':'Canary Hill demonstration'}},method='PATCH')
        f.create();f.call('/planning/draft',{})
        stage=f.call('/planning/items/stages',{'title':'Community activity','relative_start':1,'relative_end':3},expected=201)['id'];f.confirm('stage')
        self.work=f.call('/planning/items/work',{'stage_id':stage,'title':'Assessment' if category=='Environment' else 'Reading session','effort':{'value':2,'unit':'person_hours'},'schedule':{'start_day':1,'end_day':1,'start_minute':540,'end_minute':660,'timezone':'Asia/Kolkata'},'skills':skills or []},expected=201)['id']
        if resource:
            self.resource=f.call('/planning/items/resources',{'title':'Workbooks','kind':'consumable','quantity':10,'unit':'books','work_ids':[self.work]},expected=201)['id']
            f.call('/planning/items/work/'+self.work,{'resource_requirement_ids':[self.resource]},method='PATCH')
        f.confirm('work');self.role=f.call('/planning/actor-derivations',{})['requirements'][0]['id'];f.call('/planning/actor-requirements/'+self.role,{'headcount':capacity,'capabilities':skills or []},method='PATCH');f.confirm('actor');f.call('/setup/draft',{})
        f.call('/setup/sections/participation',{'data':{'visibility':'public','approval_required':True,'allow_groups':False,'show_open_roles':True,'registration_open':True}},method='PATCH')
        f.call('/setup/participant-configuration',{'collect_insights':True,'public_aggregates':True,'fields':{'age_range':True,'neighborhood':True,'experience_level':False,'participation_interest':False}},method='PUT')
        setup=f.get('/setup').json()['data'];fid=f.call('/finalizations',{'confirm_review':True,'expected_setup_version':setup['configuration']['revision'],'expected_plan_id':setup['plan_id']})['finalization_id'];f.call('/publications',{'finalization_id':fid});self.plan=setup['plan_id'];return self
    def apply(self,subject,roles=None,age='25-34'):
        config=self.client.get('/v1/events/'+self.id+'/participation/me',headers=self.headers(subject)).json()['data']['configuration']
        fields={k:v for k,v in {'age_range':age,'neighborhood':'Town center'}.items() if config['fields'].get(k)}
        data=self.call('/applications/draft',{'role_ids':roles or [self.role],'intervals':[{'start_day':1,'end_day':1,'start_minute':540,'end_minute':720,'timezone':'Asia/Kolkata'}],'answers':{'skills':'Self-reported reading experience','participant_insights':{'consent':config['collect_insights'],'fields':fields}}},subject)
        app=data['application']['id'];self.call('/applications/'+app+'/submit',{'acknowledged':True},subject);return app
    def approve(self,appid,roles=None):
        self.call('/applications/'+appid+'/begin-review',{})
        row=next(x for x in self.client.get('/v1/events/'+self.id+'/organizer/participants',headers=self.headers()).json()['data']['applications'] if x['id']==appid)
        return self.call('/applications/'+appid+'/review',{'approved_role_ids':roles or [self.role],'reviewed_revision':row['revision']})
    def offer(self,appid,**extra):return self.call('/applications/'+appid+'/assignment-offers',{'role_id':self.role,'work_ids':[self.work],'schedule':{'start_day':1,'end_day':1,'start_minute':540,'end_minute':660,'timezone':'Asia/Kolkata'},'expected_plan_id':self.plan,**extra})['assignment']

@pytest.fixture
def scenario(seeded,client,headers,factory):return Scenario(client,headers,factory)

def test_ten_real_applications_nine_then_ten_consent_and_public_privacy(scenario):
    s=scenario.build(10,'Environment');offers=[]
    for i in range(10):
        subject,id=s.person(i);appid=s.apply(subject,age='25-34' if i<5 else '35-44');s.approve(appid);offer=s.offer(appid);offers.append((subject,offer))
        if i<9:s.call('/assignments/'+offer['id']+'/accept',{'terms_key':offer['terms_key']},subject)
    profile=s.client.get('/v1/events/'+s.id+'/profile').json()['data'];assert profile['impact']['accepted_participants']==9;assert profile['insights']['breakdowns'][0]['status']=='suppressed'
    subject,offer=offers[-1];s.call('/assignments/'+offer['id']+'/accept',{'terms_key':offer['terms_key']},subject)
    profile=s.client.get('/v1/events/'+s.id+'/profile').json()['data'];assert profile['impact']['accepted_participants']==10;assert profile['insights']['breakdowns'][0]['status']=='available';assert profile['insights']['counts'] is None
    assert sum(b['count'] for b in profile['insights']['breakdowns'][0]['buckets'])==10
    own=s.client.get('/v1/me/events',headers=s.headers(subject)).json()['data']['items'];assert len(own[0]['accepted_assignments'])==1
    workspace=s.client.get('/v1/events/'+s.id+'/participation/me',headers=s.headers(subject)).json()['data'];assert workspace['accepted_work'][0]['id']==s.work and len(workspace['commitments'])==1
    assert profile['impact']['waste_collected_kg'] is None and not profile['photos']

def test_original_revisions_clarification_partial_review_and_private_draft(scenario):
    s=scenario.build();subject,id=s.person(1)
    draft=s.call('/applications/draft',{'role_ids':[s.role],'answers':{'skills':'  Exact original self report  '}},subject)['application']
    assert s.client.get('/v1/events/'+s.id+'/organizer/participants',headers=s.headers()).json()['data']['applications']==[]
    s.call('/applications/draft',{'application_id':draft['id'],'intervals':[{'start_day':1,'end_day':1,'start_minute':540,'end_minute':720,'timezone':'Asia/Kolkata'}]},subject)
    s.call('/applications/'+draft['id']+'/submit',{'acknowledged':True},subject)
    s.call('/applications/'+draft['id']+'/clarifications',{'question':'Which reading tasks do you prefer?'})
    app=s.client.get('/v1/events/'+s.id+'/participation/me',headers=s.headers(subject)).json()['data']['application'];q=app['intelligence']['clarifications'][0]
    s.call('/applications/'+app['id']+'/clarifications/'+q['id']+'/answer',{'answer':'Small-group reading practice'},subject)
    s.approve(app['id'])
    with s.factory() as db:
        revisions=list(db.scalars(select(ApplicationRevision).where(ApplicationRevision.application_id==app['id'])));assert len(revisions)>=6;assert revisions[0].content['content']['answers']['skills']=='  Exact original self report  '
    outsider=s.person(2)[0];assert s.client.get('/v1/events/'+s.id+'/participation/me?application_id='+app['id'],headers=s.headers(outsider)).status_code==404

def test_terms_changed_renewed_consent_decline_withdraw_and_idempotency(scenario):
    s=scenario.build();subject,id=s.person(1);appid=s.apply(subject);s.approve(appid);offer=s.offer(appid)
    s.call('/assignments/'+offer['id']+'/accept',{'terms_key':offer['terms_key']},subject,key='accept-once')
    version=s.client.get('/v1/events/'+s.id+'/participation/me',headers=s.headers(subject)).json()['meta']['version']
    replacement=s.offer(appid,replaces_assignment_id=offer['id'],conditions=['New meeting point must be reviewed'])
    s.call('/assignments/'+offer['id']+'/accept',{'terms_key':offer['terms_key']},subject,expected=409)
    assert replacement['status']=='assignment_offered' and replacement['terms_key']!=offer['terms_key']
    s.call('/assignments/'+offer['id']+'/decline',{'terms_key':replacement['terms_key']},subject)
    assert s.client.get('/v1/events/'+s.id+'/profile').json()['data']['impact']['accepted_participants']==0
    new=s.offer(appid);v=s.client.get('/v1/events/'+s.id+'/participation/me',headers=s.headers(subject)).json()['meta']['version'];body={'terms_key':new['terms_key']}
    a=s.call('/assignments/'+new['id']+'/accept',body,subject,key='idempotent',version=v);b=s.call('/assignments/'+new['id']+'/accept',body,subject,key='idempotent',version=v);assert a==b
    s.call('/assignments/'+new['id']+'/withdraw',{},subject)
    with s.factory() as db:assert db.scalar(select(func.count()).select_from(AssignmentConsent))==3

def test_capacity_concurrent_acceptance_and_recheck(scenario):
    s=scenario.build(1);offers=[]
    for i in range(2):
        subject,id=s.person(i);a=s.apply(subject);s.approve(a);offers.append((subject,s.offer(a)))
    version=s.flow.get('').json()['data']['version']
    def accept(item):
        subject,offer=item;return s.client.post('/v1/events/'+s.id+'/assignments/'+offer['id']+'/accept',json={'terms_key':offer['terms_key']},headers=s.headers(subject,key=uuid.uuid4().hex,version=str(version))).status_code
    with ThreadPoolExecutor(2) as pool:assert sorted(pool.map(accept,offers))==[200,409]
    rejected=next((subject,o) for subject,o in offers if s.client.get('/v1/events/'+s.id+'/participation/me',headers=s.headers(subject)).json()['data']['assignments'][0]['status']=='assignment_offered')
    s.call('/assignments/'+rejected[1]['id']+'/accept',{'terms_key':rejected[1]['terms_key']},rejected[0],expected=409)

def test_plan_change_and_unavailable_capability_block_offers(scenario):
    s=scenario.build(skills=['Teaching']);subject,id=s.person(1);a=s.apply(subject);s.approve(a)
    s.call('/applications/'+a+'/assignment-offers',{'role_id':s.role,'work_ids':[s.work],'schedule':{'start_day':1,'end_day':1,'start_minute':540,'end_minute':660,'timezone':'Asia/Kolkata'},'expected_plan_id':s.plan},expected=409)
    s.call('/applications/'+a+'/capability-reviews',{'role_id':s.role,'confirm':True,'note':'Organizer inspected applicant supplied qualification reference'})
    offer=s.offer(a)
    s.flow.call('/planning/items/work/'+s.work,{'title':'Changed material work'},method='PATCH');s.flow.confirm('work')
    s.call('/assignments/'+offer['id']+'/accept',{'terms_key':offer['terms_key']},subject,expected=409)

def test_resource_promise_report_receipt_reserve_correction_and_isolation(scenario):
    s=scenario.build(resource=True);subject,id=s.person(1)
    offer=s.call('/support-offers/draft',{'resource_id':s.resource,'support_type':'materials','description':'Workbooks supplied','quantity':10,'unit':'books','submit':True},subject)['offer']
    s.call('/sponsor-offers/'+offer['id']+'/accept',{})
    assert s.client.get('/v1/events/'+s.id+'/resources',headers=s.headers()).json()['data']['resources'][0]['on_hand']==0
    report=s.call('/sponsor-offers/'+offer['id']+'/fulfillments',{'quantity':10,'reference':'report-1','evidence_reference':'Organizer can inspect the delivery note'},subject)
    assert s.client.get('/v1/events/'+s.id+'/resources',headers=s.headers()).json()['data']['resources'][0]['available']==0
    body={'offer_id':offer['id'],'fulfillment_id':report['fulfillment_id'],'resource_id':s.resource,'quantity':10,'unit':'books','reference':'receipt-1','evidence_reference':'Organizer inspected actual workbook handover'}
    receipt=s.call('/resource-receipts',body);s.call('/resource-receipts',body,expected=409)
    reservation=s.call('/resource-reservations',{'resource_id':s.resource,'work_id':s.work,'quantity':8,'unit':'books','expected_plan_id':s.plan})
    s.call('/resource-reservations',{'resource_id':s.resource,'work_id':s.work,'quantity':3,'unit':'books','expected_plan_id':s.plan},expected=409)
    s.call('/resource-receipts/'+receipt['receipt_id']+'/corrections',{'reason':'Receipt correction'},expected=409)
    s.call('/resource-reservations/'+reservation['reservation_id']+'/release',{})
    s.call('/resource-receipts/'+receipt['receipt_id']+'/corrections',{'reason':'Organizer corrected receipt record'})
    assert s.client.get('/v1/events/'+s.id+'/resources',headers=s.headers()).json()['data']['resources'][0]['available']==0
    assert s.client.get('/v1/events/'+s.id+'/resources',headers=s.headers(subject)).status_code==404
