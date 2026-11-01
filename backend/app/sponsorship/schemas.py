from typing import Literal
from decimal import Decimal
from pydantic import Field,field_validator
from app.memory.schemas import StrictModel
class Recognition(StrictModel):
    show_profile:bool=False
    show_logo:bool=False
    show_contributions:bool=False
    private_contact:bool=True
class OrganizationProfile(StrictModel):
    name:str=Field(default='',max_length=200)
    type:str=Field(default='',max_length=100)
    description:str=Field(default='',max_length=4000)
    website:str=Field(default='',max_length=500)
    logo:str=Field(default='',max_length=1000)
    cover:str=Field(default='',max_length=1000)
    contact_name:str=Field(default='',max_length=200)
    position:str=Field(default='',max_length=200)
    email:str=Field(default='',max_length=300)
    phone:str=Field(default='',max_length=100)
    city:str=Field(default='',max_length=100)
    country:str=Field(default='',max_length=100)
    focus:list[str]=Field(default_factory=list,max_length=30)
    capabilities:list[str]=Field(default_factory=list,max_length=20)
    coverage:list[str]=Field(default_factory=list,max_length=50)
    recognition:Recognition=Field(default_factory=Recognition)
class OrganizationDraft(StrictModel):
    expected_version:int=Field(default=0,ge=0)
    organization_id:str|None=None
    profile:OrganizationProfile
    step:int=Field(default=1,ge=1,le=3)
class SupportDraft(StrictModel):
    offer_id:str|None=None
    organization_id:str|None=None
    resource_id:str
    support_type:Literal['funding','materials','equipment','services','volunteer_support','expertise']
    description:str=Field(min_length=1,max_length=4000)
    quantity:Decimal=Field(gt=0,max_digits=16,decimal_places=4,allow_inf_nan=False)
    unit:str=Field(min_length=1,max_length=80)
    estimated_value:Decimal|None=Field(default=None,ge=0,max_digits=16,decimal_places=4)
    delivery_date:str=Field(default='',max_length=10)
    @field_validator('delivery_date')
    @classmethod
    def valid_delivery_date(cls,value):
        if value:
            from datetime import date
            date.fromisoformat(value)
        return value
    delivery_method:str=Field(default='',max_length=500)
    notes:str=Field(default='',max_length=2000)
    submit:bool=False
class Fulfillment(StrictModel):
    quantity:Decimal=Field(gt=0,max_digits=16,decimal_places=4)
    reference:str=Field(min_length=1,max_length=200)
    evidence_reference:str=Field(min_length=1,max_length=1000)
class Receipt(StrictModel):
    offer_id:str|None=None
    fulfillment_id:str|None=None
    resource_id:str
    quantity:Decimal=Field(gt=0,max_digits=16,decimal_places=4)
    unit:str=Field(min_length=1,max_length=80)
    reference:str=Field(min_length=1,max_length=200)
    evidence_reference:str=Field(min_length=1,max_length=1000)
class Reservation(StrictModel):
    resource_id:str
    work_id:str
    quantity:Decimal=Field(gt=0,max_digits=16,decimal_places=4)
    unit:str
    expected_plan_id:str
class Reason(StrictModel):
    reason:str=Field(min_length=1,max_length=2000)
