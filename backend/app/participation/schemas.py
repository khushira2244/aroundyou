from typing import Literal
from pydantic import Field,ConfigDict
from app.memory.schemas import StrictModel
from app.planning.schemas import Schedule
class Insights(StrictModel):
    consent:bool=False
    fields:dict[str,str]=Field(default_factory=dict,max_length=4)
    tag_ids:list[str]=Field(default_factory=list,max_length=50)
class Answers(StrictModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=False)
    skills:str=Field(default='',max_length=4000)
    motivation:str=Field(default='',max_length=4000)
    volunteer_experience:str=Field(default='',max_length=4000)
    coordination_experience:str=Field(default='',max_length=4000)
    community_experience:str=Field(default='',max_length=4000)
    contribution:str=Field(default='',max_length=4000)
    preferred_responsibility:str=Field(default='',max_length=2000)
    leadership_interest:Literal['unspecified','interested','open_to_discussion','not_interested']='unspecified'
    work_preferences:list[str]=Field(default_factory=list,max_length=30)
    limitations:str=Field(default='',max_length=4000)
    custom_answers:dict[str,str|list[str]]=Field(default_factory=dict,max_length=30)
    participant_insights:Insights=Field(default_factory=Insights)
class ApplicationDraft(StrictModel):
    application_id:str|None=None
    step:int|None=Field(default=None,ge=1,le=4)
    role_ids:list[str]|None=Field(default=None,max_length=50)
    work_ids:list[str]|None=Field(default=None,max_length=100)
    intervals:list[Schedule]|None=Field(default=None,max_length=100)
    answers:Answers|None=None
class Submit(StrictModel):
    acknowledged:bool
class Review(StrictModel):
    approved_role_ids:list[str]=Field(max_length=50)
    reviewed_revision:int=Field(ge=1)
    note:str=Field(default='',max_length=2000)
class Offer(StrictModel):
    role_id:str
    work_ids:list[str]=Field(min_length=1,max_length=50)
    schedule:Schedule
    expected_plan_id:str
    conditions:list[str]=Field(default_factory=list,max_length=30)
    expires_in_hours:int=Field(default=168,ge=1,le=720)
    replaces_assignment_id:str|None=None
class Consent(StrictModel):
    terms_key:str=Field(min_length=64,max_length=64)
    confirmed:bool=True
class Clarification(StrictModel):
    question:str=Field(min_length=1,max_length=2000)
class ClarificationAnswer(StrictModel):
    answer:str=Field(min_length=1,max_length=4000)
class CapabilityReview(StrictModel):
    role_id:str
    note:str=Field(min_length=1,max_length=2000)
    confirm:bool
class Empty(StrictModel):pass
