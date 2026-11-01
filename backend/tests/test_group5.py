import pytest
from tests.test_group3 import scenario
from app.recovery.impact import affected_scope
from app.api.errors import DomainError

def test_graph_preserves_complete_and_unrelated_branches():
    p={'stages':[{'id':'s','dependency_ids':[]}],'work':[{'id':i,'stage_id':'s','dependency_ids':d} for i,d in [('W16',[]),('W17',['W16']),('done',['W17']),('other',[])]]}
    m=affected_scope(p,['W16'],['done'])
    assert m['affected_work_ids']==['W16','W17','done']
    assert [r['classification'] for r in m['work']]==['directly_blocked','downstream_affected','verified_complete','unaffected']
    p['work'][0]['dependency_ids']=['W17']
    with pytest.raises(DomainError,match='dependency_cycle'):affected_scope(p,['W16'])

def test_stage_dependencies_and_invalid_references():
    p={'stages':[{'id':'a'},{'id':'b','dependency_ids':['a']}],'work':[{'id':'venue','stage_id':'a'},{'id':'class','stage_id':'b'}]}
    assert affected_scope(p,['venue'])['affected_work_ids']==['class','venue']
    p['work'][1]['dependency_ids']=['absent']
    with pytest.raises(DomainError):affected_scope(p,['venue'])

def test_configuration_answers_consent_and_authorization(scenario):
    s=scenario.build();subject,aid=s.person(9)
    config={'expected_revision':0,'public_aggregates':True,'questions':[{'id':'age','label':'Age range','dimension':'age_range','choices':['18-24','25-34']},{'id':'club','label':'Club','dimension':'tags','choices':['Reader','Tutor']}]}
    out=s.call('/insight-configuration',config,method='PUT');assert out['revision']==1
    s.call('/insight-configuration',config,method='PUT',expected=409)
    s.call('/insight-configuration',{**config,'expected_revision':1},subject,method='PUT',expected=404)
    answer={'configuration_revision':1,'answers':{'age':'25-34','club':'Reader'},'consent':True}
    assert s.call('/insight-responses/me',answer,subject,method='PUT')['answers']==answer['answers']
    s.call('/insight-responses/me',{**answer,'answers':{'age':'impossible'}},subject,method='PUT',expected=422)
    url='/v1/events/'+s.id+'/dynamic-insights'
    result=s.client.get(url,headers=s.headers(subject));assert result.status_code==200
    assert result.json()['data']['status']=='suppressed' and '25-34' not in result.text
    assert s.client.get(url+'?filters=age:25-34',headers=s.headers(subject)).json()['data']=={'status':'suppressed','breakdowns':[]}
    assert s.call('/insight-responses/me/consent',{},subject,method='DELETE')['consent'] is False
    s.call('/insight-configuration',{**config,'expected_revision':1},method='PUT')
    s.call('/insight-responses/me',answer,subject,method='PUT',expected=409)


def test_five_accepted_responses_threshold_revocation_and_lineage(scenario):
    s=scenario.build(10);people=[]
    config={'expected_revision':0,'public_aggregates':True,'questions':[{'id':k,'label':k,'dimension':d,'choices':['A','B']} for k,d in [('age','age_range'),('town','neighborhood'),('skill','experience_level'),('interest','participation_interest'),('tag','tags')]]}
    s.call('/insight-configuration',config,method='PUT')
    url='/v1/events/'+s.id+'/dynamic-insights'
    for i in range(5):
        subject,aid=s.person(i);people.append(subject)
        app=s.apply(subject);s.approve(app);offer=s.offer(app)
        s.call('/insight-responses/me',{'configuration_revision':1,'answers':{q['id']:'A' for q in config['questions']},'consent':True},subject,method='PUT')
        if i==4:assert s.client.get(url,headers=s.headers()).json()['data']['status']=='suppressed'
        s.call('/assignments/'+offer['id']+'/accept',{'terms_key':offer['terms_key']},subject)
    result=s.client.get(url,headers=s.headers(people[0])).json()['data']
    assert len(result['breakdowns'])==5 and all(x['buckets']==[{'label':'A','count':5}] for x in result['breakdowns'])
    s.call('/insight-responses/me/consent',{},people[0],method='DELETE')
    result=s.client.get(url,headers=s.headers()).json()['data']
    assert all(x['status']=='suppressed' and not x['buckets'] for x in result['breakdowns'])
    s.call('/insight-configuration',{**config,'expected_revision':1,'questions':[{**q,'choices':['Renamed']} for q in config['questions']]},method='PUT')
    assert s.client.get(url,headers=s.headers()).json()['data']['status']=='suppressed'


def test_impact_requires_explicit_confirmation_not_acknowledgment(scenario):
    s=scenario.build()
    issue=s.call('/issues',{'work_id':s.work,'category':'other','description':'Workshop venue unavailable; reported venue closure','severity':'impossible'})['blocker']
    request={'issue_ids':[issue['id']],'expected_plan_id':s.plan}
    s.call('/recovery/impact',request,expected=409)
    confirmed=s.call('/recovery/issues/'+issue['id']+'/confirm',{'expected_revision':issue['revision'],'reason':'Organizer checked venue closure directly'})
    impact=s.call('/recovery/impact',request)
    assert impact['scope']['direct_work_ids']==[s.work] and impact['activation_available'] is False
    s.call('/issues/'+issue['id']+'/review',{'expected_revision':confirmed['revision'],'state':'acknowledged','condition_cleared':False,'note':'Recheck required'})
    s.call('/recovery/impact',request,expected=409)
