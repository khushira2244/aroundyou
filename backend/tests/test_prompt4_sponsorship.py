from tests.test_group3 import scenario

def test_published_opportunity_revision_partial_reports_verified_portal_and_correction(scenario):
    s=scenario.build(resource=True);subject,account=s.person('sponsor')
    h=s.headers(subject)
    profile={'name':'Test Community Sponsor','type':'Business','description':'Integration test only','contact_name':'Representative','email':'sponsor@example.test','city':'Hazaribagh','country':'India','focus':['Education'],'capabilities':['materials'],'coverage':['Hazaribagh']}
    r=s.client.post('/v1/organizations/draft',json={'profile':profile},headers=h);assert r.status_code==200,r.text
    org=r.json()['data']['organization_id']
    r=s.client.post('/v1/organizations/'+org+'/registration/complete',json={},headers=s.headers(subject,key='register'));assert r.status_code==200,r.text
    def portal():return s.client.get('/v1/me/sponsor-portal',headers=h).json()['data']
    assert any(e['id']==s.id for e in portal()['opportunities'])
    offer=s.call('/support-offers/draft',{'organization_id':org,'resource_id':s.resource,'support_type':'materials','description':'Integration-test workbook offer','quantity':10,'unit':'books','submit':True},subject)['offer']
    s.call('/sponsor-offers/'+offer['id']+'/revision-requests',{'body':'Clarify delivery reference before review'})
    assert portal()['offers'][0]['revision_request']['body']=='Clarify delivery reference before review'
    s.call('/sponsor-offers/'+offer['id']+'/accept',{})
    assert portal()['stats']['accepted']==1 and portal()['stats']['verified_contributions']==0
    data={'quantity':4,'reference':'test-partial-delivery','evidence_reference':'Synthetic integration test; no actual goods claimed'}
    report=s.call('/sponsor-offers/'+offer['id']+'/fulfillments',data,subject)
    s.call('/sponsor-offers/'+offer['id']+'/fulfillments',data,subject,expected=409)
    assert portal()['fulfillments'][0]['status']=='reported_unverified'
    receipt=s.call('/resource-receipts',{'offer_id':offer['id'],'fulfillment_id':report['fulfillment_id'],'resource_id':s.resource,'quantity':4,'unit':'books','reference':'test-receipt','evidence_reference':'Synthetic integration verification only'})
    p=portal();assert p['fulfillments'][0]['status']=='verified' and p['stats']['verified_contributions']==1 and p['stats']['completed']==0
    assert p['offers'][0]['fulfillment_status']=='partially_fulfilled' and p['offers'][0]['verified']==4
    assert p['supported_events'][0]['has_verified_support'] is True
    assert s.client.get('/v1/events/'+s.id+'/resources',headers=s.headers()).json()['data']['resources'][0]['on_hand']==4
    second=s.call('/sponsor-offers/'+offer['id']+'/fulfillments',{'quantity':6,'reference':'test-final-delivery','evidence_reference':'Synthetic test delivery only'},subject)
    s.call('/resource-receipts',{'offer_id':offer['id'],'fulfillment_id':second['fulfillment_id'],'resource_id':s.resource,'quantity':6,'unit':'books','reference':'test-final-receipt','evidence_reference':'Synthetic test receipt only'})
    assert portal()['stats']['completed']==1 and portal()['offers'][0]['verified']==10
    s.call('/resource-receipts/'+receipt['receipt_id']+'/corrections',{'reason':'Correct synthetic test receipt'})
    assert portal()['fulfillments'][0]['status']=='reported_unverified' and portal()['stats']['completed']==0 and portal()['offers'][0]['verified']==6
    outsider,_=s.person('outsider')
    assert s.client.get('/v1/organizations/'+org+'/sponsor-portal',headers=s.headers(outsider)).status_code==404
    s.call('/sponsor-offers/'+offer['id']+'/revision-requests',{'body':'Unauthorized'},outsider,expected=404)
