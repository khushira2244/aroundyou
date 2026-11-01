from typing import Literal
from decimal import Decimal
from datetime import datetime
from pydantic import Field,field_validator,ConfigDict
from app.memory.schemas import StrictModel
from app.planning.schemas import Schedule
class Usage(StrictModel):
    id:str|None=None
    resource_id:str
    quantity:Decimal=Field(gt=0,max_digits=16,decimal_places=4)
    unit:str=Field(min_length=1,max_length=60)
    kind:Literal['consumable','equipment','reusable','service','facility']
class Measurement(StrictModel):
    metric:str=Field(min_length=1,max_length=100)
    value:float=Field(ge=0,allow_inf_nan=False)
    unit:str=Field(min_length=1,max_length=60)
class ReportDraft(StrictModel):
    model_config=ConfigDict(extra="forbid",str_strip_whitespace=False)
    work_id:str
    report_id:str|None=None
    report_revision:int|None=None
    body:str=Field(default='',max_length=8000)
    remaining_work:str=Field(default='',max_length=4000)
    progress_percent:float|None=Field(default=None,ge=0,le=100,allow_inf_nan=False)
    claim:Literal['progress','completion']='progress'
    resource_usage:list[Usage]=Field(default_factory=list,max_length=50)
    measurements:list[Measurement]=Field(default_factory=list,max_length=30)
class ReportCommand(StrictModel):
    report_revision:int=Field(ge=1)
class Review(ReportCommand):
    outcome:Literal['unknown','successful','failed','mixed','inconclusive']='inconclusive'
    decision:Literal['accept','reject','request_correction','clarify']
    note:str=Field(min_length=1,max_length=4000)
    verified_percent:float|None=Field(default=None,ge=0,le=100,allow_inf_nan=False)
    evidence_versions:dict[str,int]=Field(default_factory=dict,max_length=30)
class WorkCommand(StrictModel):
    reason:str=Field(default='',max_length=2000)
    preconditions_confirmed:bool=False
class Grant(StrictModel):
    account_id:str
    stage_id:str
    confirm:bool
    active:bool=True
class EvidenceDraft(StrictModel):
    model_config=ConfigDict(extra="forbid",str_strip_whitespace=False)
    report_id:str
    report_revision:int=Field(ge=1)
    kind:Literal['image','video','audio','document','text']
    name:str=Field(min_length=1,max_length=200)
    mime:str=Field(min_length=1,max_length=100)
    size:int=Field(ge=0,le=52428800)
    text:str=Field(default='',max_length=8000)
    @field_validator('name')
    @classmethod
    def safe_name(cls,v):
        if any(c in v for c in '/\\\x00') or v in ('.','..'):raise ValueError('Filename must be a display basename')
        return v
class EvidenceReview(StrictModel):
    expected_revision:int=Field(ge=1)
    decision:Literal['accept_for_review','quarantine','retract','review_transcript']
    note:str=Field(min_length=1,max_length=2000)
    transcript:str|None=Field(default=None,max_length=8000)
class Attendance(StrictModel):
    assignment_id:str
    action:Literal['claim','verify','correct']
    note:str=Field(min_length=1,max_length=2000)
    expected_revision:int=Field(default=0,ge=0)
    present:bool=True
class UsageCommand(StrictModel):
    report_id:str
    usage_id:str
    reservation_id:str
    quantity:Decimal=Field(gt=0,max_digits=16,decimal_places=4)
    reference:str=Field(min_length=1,max_length=200)
    confirm:bool
class Issue(StrictModel):
    work_id:str
    resource_ids:list[str]=Field(default_factory=list,max_length=30)
    category:Literal['resource_missing','delay','access','safety','equipment_damage','equipment_loss','other']='other'
    description:str=Field(min_length=1,max_length=4000)
    severity:Literal['delayed','impossible','unsafe']='delayed'
    occurred_at:str=Field(default='',max_length=60)
    effect:str=Field(default='',max_length=2000)
    evidence_ids:list[str]=Field(default_factory=list,max_length=20)
class IssueReview(StrictModel):
    expected_revision:int=Field(ge=1)
    state:Literal['acknowledged','investigating','resolved','closed']
    condition_cleared:bool=False
    note:str=Field(min_length=1,max_length=2000)
class Coordination(StrictModel):
    kind:Literal['announcement','note','discussion','meeting','decision','action']
    title:str=Field(min_length=1,max_length=200)
    body:str=Field(default='',max_length=8000)
    audience:Literal['public','participants','internal']='participants'
    stage_ids:list[str]=Field(default_factory=list,max_length=30)
    work_ids:list[str]=Field(default_factory=list,max_length=50)
    invited_account_ids:list[str]=Field(default_factory=list,max_length=100)
    schedule:Schedule|None=None
    agenda:list[str]=Field(default_factory=list,max_length=30)
    parent_id:str|None=None
    status:Literal['draft','published','scheduled','decided','open','completed']='draft'
class CoordinationUpdate(StrictModel):
    expected_revision:int=Field(ge=1)
    action:Literal['publish','confirm','rsvp','approve_action','complete_action','cancel']
    response:Literal['going','maybe','not_going']='going'
    note:str=Field(default='',max_length=2000)
