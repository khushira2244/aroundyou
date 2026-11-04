from copy import deepcopy
import pytest
from pydantic import ValidationError
from app.planning.intelligence import StageResourceNeed,LinkedResource,validate_selected
from app.planning.schemas import PlanContent,Stage,Resource
from app.ai.planning_port import WORKFLOW_INSTRUCTIONS


def estimate(**patch):
    return {'title':'Protective gloves','kind':'consumable','quantity':20,'unit':'pairs','estimation_basis':'Planning assumption: 20 expected workers, one pair each for this work session.','unknown_reason':None,**patch}


@pytest.mark.parametrize('schema',[StageResourceNeed,LinkedResource])
def test_estimate_requires_explicit_basis(schema):
    data=estimate()
    if schema is LinkedResource:data['id']='r'
    r=schema.model_validate(data)
    assert r.quantity==20 and r.estimation_basis
    with pytest.raises(ValidationError):schema.model_validate({**data,'estimation_basis':None})


def test_justified_unknown_is_accepted_but_unexplained_null_is_not():
    assert StageResourceNeed.model_validate(estimate(quantity=None,estimation_basis=None,unknown_reason='Waste volume and bag capacity have not been assessed.')).quantity is None
    with pytest.raises(ValidationError):StageResourceNeed.model_validate(estimate(quantity=None,estimation_basis=None))


@pytest.mark.parametrize('bad',[-1,float('nan'),float('inf'),'twenty','20',True])
def test_invalid_numbers_are_not_coerced(bad):
    with pytest.raises(ValidationError):StageResourceNeed.model_validate(estimate(quantity=bad))


def test_omitted_quantity_is_rejected_and_zero_requires_basis():
    value=estimate();value.pop('quantity')
    with pytest.raises(ValidationError):StageResourceNeed.model_validate(value)
    assert StageResourceNeed.model_validate(estimate(quantity=0,estimation_basis='No additional pairs needed for this task; existing demand covers the same session.')).quantity==0


def test_legacy_saved_resources_and_plans_remain_readable():
    legacy=Resource(id='r',title='Gloves',kind='consumable',unit='pairs').model_dump()
    assert legacy['quantity'] is None
    plan=PlanContent(resources=[legacy]).model_dump()
    assert PlanContent.model_validate(plan).resources[0].quantity is None


def test_selected_output_preserves_numbers_links_and_review_reasons():
    base=PlanContent(stages=[Stage(id='s',title='Work')]).model_dump();original=deepcopy(base)
    result={'message':'Demand estimates for human review.','work':[{'title':'Collect litter','objective':'Collect visible litter','outcome':'Evidence for organizer review','schedule':{'start_day':1,'end_day':1,'start_minute':540,'end_minute':660,'timezone':'Asia/Kolkata'},'resources':[estimate(),estimate(title='Waste bags',quantity=None,estimation_basis=None,unknown_reason='Waste volume not assessed.')]}]}
    proposal=validate_selected('work',result,base,'s','offline-run')
    plan=PlanContent.model_validate(proposal['plan']);work=plan.work[0]
    assert plan.resources[0].quantity==20
    assert all(r.work_ids==[work.id] and r.id in work.resource_requirement_ids for r in plan.resources)
    assert any('Needs review' in note and 'Waste volume not assessed' in note for note in work.conditions)
    assert proposal['resource_quantity_reviews'][0]['estimation_basis']==result['work'][0]['resources'][0]['estimation_basis']
    assert proposal['resource_quantity_reviews'][1]['status']=='Needs review'
    assert base==original


def test_prompt_uses_actual_context_not_fixed_worker_counts():
    instruction=WORKFLOW_INSTRUCTIONS['work']
    assert 'estimation_basis' in instruction and 'unknown_reason' in instruction
    assert 'attendees are not workers' in instruction
    assert '20 expected' not in instruction
