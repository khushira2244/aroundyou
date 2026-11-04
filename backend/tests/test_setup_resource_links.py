from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from pydantic import ValidationError
from app.planning.schemas import PlanContent, Stage, Work, Resource
from app.planning.service import edit_resource_requirements
from app.resources import service


def content():
    return PlanContent(stages=[Stage(id='s1',title='Preparation')],work=[Work(id='w1',stage_id='s1',title='Safety briefing',resource_requirement_ids=['r1'])],resources=[Resource(id='r1',title='Gloves',kind='consumable',quantity=None,unit='pairs',work_ids=['w1'])]).model_dump()


def test_manual_resource_candidate_preserves_original_and_links():
    original=content();before=deepcopy(original)
    candidate=edit_resource_requirements(original,'w1',{'r1':20},[{'title':'First aid kit','kind':'equipment','quantity':1,'unit':'kits'}])
    assert original==before
    assert candidate['resources'][0]['quantity']==20
    new=candidate['resources'][1]
    assert new['work_ids']==['w1'] and new['id'] in candidate['work'][0]['resource_requirement_ids']
    assert candidate['stages']==original['stages']
    PlanContent.model_validate(candidate)


@pytest.mark.parametrize('quantity',[-1,float('nan')])
def test_invalid_manual_quantities_rejected(quantity):
    with pytest.raises(ValidationError):edit_resource_requirements(content(),'w1',{'r1':quantity},[])


def test_foreign_resource_rejected():
    with pytest.raises(Exception,match='foreign_resource'):edit_resource_requirements(content(),'w1',{'foreign':1},[])


def test_unpublished_resources_use_real_ledger_without_publication(monkeypatch):
    monkeypatch.setattr(service,'totals',lambda *args:(service.D(8),service.D(3),[]))
    monkeypatch.setattr('app.execution.ledger.amounts',lambda *args,**kwargs:(0,0,0))
    session=Mock();session.scalars.return_value=[]
    r=service.project_requirements(session,SimpleNamespace(id='event'),[{**content()['resources'][0],'quantity':20}])[0]
    assert r['required']==20 and r['available']==5 and r['reserved']==3 and r['gap']==12
    assert r['work_ids']==['w1'] and r['pledged']==0
