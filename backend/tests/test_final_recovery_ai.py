from copy import deepcopy
import pytest
from app.api.errors import DomainError
from app.recovery.advisory import context,validate_output
from app.events.models import Event
from app.planning.models import PlanVersion
from tests.test_prompt7_workspace import confirmed

def test_recovery_patch_validation_and_no_feasible_answer(scenario):
 s=scenario.build(resource=True);issue=confirmed(s)
 with s.factory() as db:
  e=db.get(Event,s.id);p=db.get(PlanVersion,e.active_plan_id).content;c={'plan':p,'participation_and_resources':context(db,e.creator_id,e,issue['id'])}
  assert validate_output({'alternatives':[],'questions':['What capacity is actually available?']},c)['alternatives']==[]
  opt={'title':'Manual scoped adjustment','rationale':'Review local conditions','schedules':{},'patches':{'work:'+s.work:{'scope':'Human reviewed adjusted operational scope'}},'assumptions':[],'risks':[],'unknowns':['Inventory not verified'],'conditions':[],'cited_issue_ids':[issue['id']]}
  assert validate_output({'alternatives':[opt],'questions':[]},c)['alternatives'][0]['conditions']
  for patch in ({'work:other':{'scope':'Invalid unrelated change'}},{'work:'+s.work:{'account_id':'invented'}},{'resource:'+p['resources'][0]['id']:{'quantity':-1}}):
   bad=deepcopy(opt);bad['patches']=patch
   with pytest.raises((ValueError,DomainError)):validate_output({'alternatives':[bad],'questions':[]},c)
from tests.test_group3 import scenario
