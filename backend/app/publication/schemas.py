from typing import Literal
from datetime import date,time
from pydantic import Field,model_validator
from app.memory.schemas import StrictModel
class Participation(StrictModel):
    visibility: Literal['public','community_only','invite_only']='public'
    approval_required: bool=True
    allow_groups: bool=False
    show_open_roles: bool=True
    registration_open: bool=False
class Location(StrictModel):
    access_instructions: str=Field(default='',max_length=2000)
    facilities: str=Field(default='',max_length=2000)
    emergency_contact: str=Field(default='',max_length=300)
    zones: list[str]=Field(default_factory=list,max_length=100)
class Communications(StrictModel):
    welcome_message: str=Field(default='',max_length=2000)
    participant_instructions: str=Field(default='',max_length=4000)
    contact_email: str=Field(default='',max_length=300)
    contact_phone: str=Field(default='',max_length=100)
    updates_channel: str=Field(default='',max_length=500)
    public_contact: bool=False
class Tag(StrictModel):
    id: str=Field(min_length=1,max_length=60)
    label: str=Field(min_length=1,max_length=100)
    active: bool=True
class Question(StrictModel):
    id: str=Field(min_length=1,max_length=60)
    text: str=Field(min_length=1,max_length=500)
    answer_type: Literal['short_answer','single_choice','multiple_choice']='short_answer'
    options: list[str]=Field(default_factory=list,max_length=30)
    active: bool=True
    optional: bool=True
    @model_validator(mode='after')
    def valid(self):
        if not self.optional:raise ValueError('Demographic/custom questions remain optional')
        if self.answer_type!='short_answer' and (not self.options or len(set(self.options))!=len(self.options)):raise ValueError('Unique options required')
        return self
class InsightFields(StrictModel):
    age_range: bool=False
    neighborhood: bool=False
    experience_level: bool=False
    participation_interest: bool=False
class ParticipantConfiguration(StrictModel):
    collect_insights: bool=False
    public_aggregates: bool=False
    fields: InsightFields=Field(default_factory=InsightFields)
    custom_tags: list[Tag]=Field(default_factory=list,max_length=100)
    questions: list[Question]=Field(default_factory=list,max_length=30)
    @model_validator(mode='after')
    def valid(self):
        if len({t.id for t in self.custom_tags})!=len(self.custom_tags) or len({q.id for q in self.questions})!=len(self.questions):raise ValueError('Duplicate configuration IDs')
        if self.public_aggregates and not self.collect_insights:raise ValueError('Enable collection before public aggregates')
        return self
class Invite(StrictModel):
    label: str=Field(min_length=1,max_length=200)
    kind: Literal['individual','group','organization']='individual'
    email: str=Field(default='',max_length=300)
    phone: str=Field(default='',max_length=100)
    role_id: str|None=None
class Partner(StrictModel):
    label: str=Field(min_length=1,max_length=200)
    support_type: str=Field(min_length=1,max_length=100)
    details: str=Field(default='',max_length=2000)
class ResourceClaims(StrictModel):
    claims: dict[str,float|None]=Field(default_factory=dict,max_length=200)
    @model_validator(mode='after')
    def valid(self):
        import math
        if any(v is not None and (not math.isfinite(v) or v<0) for v in self.claims.values()):raise ValueError('Nonnegative finite reports only')
        return self
class SponsorReview(StrictModel):
    public_offer_ids: list[str]=Field(default_factory=list,max_length=100)
class PublishPreferences(StrictModel):
    mode: Literal['now','scheduled']='now'
    date: str=''
    time: str=''
    @model_validator(mode='after')
    def valid(self):
        if self.mode=='scheduled':
            date.fromisoformat(self.date);time.fromisoformat(self.time)
        return self
