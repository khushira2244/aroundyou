from types import SimpleNamespace
import pytest
from app.api.group2 import discovery
from app.api.errors import DomainError

class Catalog:
    def __init__(self):
        self.events=[];self.releases={}
        for id,coordinates,visibility in [('near',{'lat':23.98,'lng':85.36},'public'),('far',{'lat':28.6,'lng':77.2},'public'),('unknown',None,'public'),('private',{'lat':23.98,'lng':85.36},'private')]:
            self.events.append(SimpleNamespace(id=id,current_publication_id=id))
            event=dict(id=id,title=id,category='Education',filter_group='Education',label='Example',demo=True,location={'label':'Declared locality','confidence':'unverified','coordinates':coordinates})
            self.releases[id]=SimpleNamespace(visibility=visibility,snapshot={'event':event})
    def scalars(self,_):return self.events
    def get(self,_,id):return self.releases[id]

def test_bounds_filter_uses_independent_points_and_keeps_unlocated_cards():
    result=discovery(category=None,q=None,limit=100,south=23.8,north=24.2,west=85.1,east=85.6,db=Catalog())
    assert [x['id'] for x in result['data']['items']]==['near','unknown']
    assert result['data']['items'][1]['location']['coordinates'] is None

def test_partial_or_inverted_bounds_rejected():
    for south,north,west,east in [(23,None,85,86),(24,23,85,86)]:
        with pytest.raises(DomainError):discovery(category=None,q=None,limit=100,south=south,north=north,west=west,east=east,db=Catalog())
