from datetime import date,time
from zoneinfo import ZoneInfo
from typing import Literal
from pydantic import Field,model_validator,ConfigDict
from app.memory.schemas import StrictModel
class Coordinates(StrictModel):
    lat: float = Field(ge=-90,le=90,allow_inf_nan=False)
    lng: float = Field(ge=-180,le=180,allow_inf_nan=False)
class CreationForm(StrictModel):
    model_config=ConfigDict(extra="forbid",str_strip_whitespace=False)
    title: str = Field(default="",max_length=200)
    category: str = Field(default="",max_length=80)
    purpose: str = Field(default="",max_length=1000)
    goal: str = Field(default="",max_length=4000)
    format: Literal['in_person','hybrid','online'] = 'in_person'
    startDate: str = ''
    endDate: str = ''
    startTime: str = ''
    endTime: str = ''
    timezone: str = 'Asia/Kolkata'
    venue: str = Field(default='',max_length=300)
    area: str = Field(default='',max_length=500)
    city: str = Field(default='',max_length=100)
    state: str = Field(default='',max_length=100)
    country: str = Field(default='',max_length=100)
    reach: str = Field(default='',max_length=80)
    coordinates: Coordinates | None = None
    locationSource: str | None = Field(default=None,max_length=200)
    workScope: str = Field(default='',max_length=4000)
    executionIntent: str = Field(default='',max_length=12000)
    intentSource: Literal['written','reviewed_demo_transcript','reviewed_transcript'] = 'written'
    expectedAttendees: str = Field(default='',max_length=8)
    expectedVolunteers: str = Field(default='',max_length=8)
    targetGroups: list[str] = Field(default_factory=list,max_length=30)
    knownResources: str = Field(default='',max_length=4000)
    constraints: str = Field(default='',max_length=4000)
    outcomes: str = Field(default='',max_length=4000)
    theme: str = Field(default='',max_length=100)
    onlineDetails: str = Field(default='',max_length=2000)
    confirmAccuracy: bool = False
    confirmPlanning: bool = False
    confirmContinue: bool = False
    @model_validator(mode='after')
    def validate_partial(self):
        try:ZoneInfo(self.timezone)
        except Exception:raise ValueError('Invalid timezone')
        for x in (self.startDate,self.endDate):
            if x:date.fromisoformat(x)
        for x in (self.startTime,self.endTime):
            if x:time.fromisoformat(x)
        if self.startDate and self.endDate and self.endDate<self.startDate:raise ValueError('Invalid date range')
        if self.startDate==self.endDate and self.startTime and self.endTime and self.startTime>=self.endTime:raise ValueError('Invalid time range')
        for x in (self.expectedAttendees,self.expectedVolunteers):
            if x and (not x.isdigit() or int(x)>1000000):raise ValueError('Invalid participation estimate')
        return self
    def complete(self):
        required=[self.title,self.category,self.purpose,self.goal,self.startDate,self.endDate,self.startTime,self.endTime,self.workScope,self.outcomes,self.executionIntent]
        if self.format!='online':required.extend([self.city,self.country,self.area])
        else:required.append(self.onlineDetails)
        if not self.targetGroups:raise ValueError("At least one target group required")
        if not all(x.strip() for x in required) or not (self.confirmAccuracy and self.confirmPlanning and self.confirmContinue):raise ValueError('Complete four-step brief and acknowledgements required')
class Interpretation(StrictModel):
    assumptions: list[str] = Field(default_factory=list,max_length=40)
    reported_facts: list[str] = Field(default_factory=list,max_length=40)
    scope: list[str] = Field(default_factory=list,max_length=40)
    exclusions: list[str] = Field(default_factory=list,max_length=40)
    instructions: list[str] = Field(default_factory=list,max_length=40)
    constraints: list[str] = Field(default_factory=list,max_length=40)
    unknowns: list[str] = Field(default_factory=list,max_length=40)
    clarifications: list[str] = Field(default_factory=list,max_length=40)
