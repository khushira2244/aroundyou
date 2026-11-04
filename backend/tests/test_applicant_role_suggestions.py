from types import SimpleNamespace
from copy import deepcopy
import pytest
from app.participation import role_suggestions as rs
from app.participation.advisory import ParticipationAdvice
from app.api.errors import DomainError


class Session:
    def __init__(self): self.rows=[]
    def add(self,row): self.rows.append(row)
    def flush(self): pass


@pytest.fixture
def scope(monkeypatch):
    application=SimpleNamespace(id='application',account_id='participant',status='application_draft',plan_id='plan',sequence=4,content={'intervals':[{'start_day':1,'end_day':1,'start_minute':540,'end_minute':660,'timezone':'Asia/Kolkata'}],'role_ids':[],'answers':{'skills':'I can take photos','participant_insights':{'fields':{'age_range':'private age'}}}})
    role={'id':'photo','title':'Photo support','work_ids':['photo-work']}
    release=SimpleNamespace(id='release',plan_id='plan',snapshot={'plan':{'roles':[role],'work':[{'id':'photo-work'}]}})
    def own(db,event,application_id,actor):
        if actor!=application.account_id: raise DomainError('not_found','Record unavailable',404)
        return application
    monkeypatch.setattr(rs,'app_for',own)
    monkeypatch.setattr(rs,'published',lambda *args:release)
    monkeypatch.setattr(rs,'audit',lambda *args:None)
    return application


class Provider:
    live_provider=True
    model_profile='offline-test-stub'
    def __init__(self):
        self.calls=0
        self.output={**ParticipationAdvice().model_dump(),'recommendations':[{'role_id':'photo','work_ids':['photo-work'],'supporting_statements':['I can take photos'],'explanation':'Self-reported photography experience; organizer review required.','missing_information':[],'trade_offs':[]}]}
    def propose(self,request):
        self.calls+=1;self.request=request
        return deepcopy(self.output)


def test_private_draft_advice_is_pending_and_never_selects_or_submits(scope):
    db=Session();provider=Provider();before=deepcopy(scope.content)
    result=rs.suggest(db,'participant',SimpleNamespace(id='event'),'application',provider)
    assert result['status']=='available' and provider.calls==1
    assert scope.status=='application_draft' and scope.content==before
    assert 'private age' not in str(provider.request.authoritative_current)
    assert db.rows[-1].status=='pending' and db.rows[0].status=='succeeded'


@pytest.mark.parametrize('invalid',['role','work','quote','resources'])
def test_invalid_output_never_creates_proposal(scope,invalid):
    db=Session();provider=Provider()
    match=provider.output['recommendations'][0]
    if invalid=='role':match['role_id']='foreign-role'
    elif invalid=='work':match['work_ids']=['foreign-work']
    elif invalid=='quote':match['supporting_statements']=['Certified professional']
    else:provider.output['resource_advice']=[{'resource_id':'foreign','explanation':'invented','unknowns':[]}]
    assert rs.suggest(db,'participant',SimpleNamespace(id='event'),'application',provider)['status']=='failed'
    assert len(db.rows)==1 and db.rows[0].status=='failed'
    assert provider.calls==1


def test_other_participant_cannot_invoke_model(scope):
    provider=Provider()
    with pytest.raises(DomainError):rs.suggest(Session(),'outsider',SimpleNamespace(id='event'),'application',provider)
    assert provider.calls==0


def test_missing_availability_or_provider_does_not_invoke(scope):
    provider=Provider();scope.content['intervals']=[]
    with pytest.raises(DomainError):rs.suggest(Session(),'participant',SimpleNamespace(id='event'),'application',provider)
    assert provider.calls==0
    scope.content['intervals']=[{}]
    with pytest.raises(DomainError):rs.suggest(Session(),'participant',SimpleNamespace(id='event'),'application',None)
