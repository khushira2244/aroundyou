from typing import Literal
from math import isfinite
from pydantic import Field, model_validator
from app.memory.schemas import StrictModel

class Quantity(StrictModel):
    value: float | None = Field(default=None,ge=0,allow_inf_nan=False)
    unit: str = Field(min_length=1,max_length=60)
    confidence: str = Field(default="unknown",max_length=60)
    known_subtotal: float | None = Field(default=None,ge=0,allow_inf_nan=False)
class Schedule(StrictModel):
    start_day: int = Field(default=1,ge=1,le=3660)
    end_day: int = Field(default=1,ge=1,le=3660)
    start_minute: int = Field(default=540,ge=0,lt=1440)
    end_minute: int = Field(default=660,ge=0,le=1440)
    timezone: str = "Asia/Kolkata"
    @model_validator(mode="after")
    def valid(self):
        from zoneinfo import ZoneInfo
        try:ZoneInfo(self.timezone)
        except Exception:raise ValueError("Invalid timezone")
        if self.finish<=self.start:raise ValueError("Schedule finish must follow start")
        return self
    @property
    def start(self):return (self.start_day-1)*1440+self.start_minute
    @property
    def finish(self):return (self.end_day-1)*1440+self.end_minute
class Stage(StrictModel):
    id: str = Field(min_length=1,max_length=60)
    title: str = Field(min_length=1,max_length=200)
    purpose: str = Field(default="",max_length=2000)
    intended_outcomes: list[str] = Field(default_factory=list,max_length=30)
    relative_start: int = Field(default=1,ge=1,le=3660)
    relative_end: int = Field(default=1,ge=1,le=3660)
    dependency_ids: list[str] = Field(default_factory=list,max_length=100)
    volume: Quantity = Field(default_factory=lambda:Quantity(unit="work_blocks"))
    effort: Quantity = Field(default_factory=lambda:Quantity(unit="person_hours"))
    duration: Quantity = Field(default_factory=lambda:Quantity(unit="days"))
    staffing_assumptions: list[str] = Field(default_factory=list,max_length=30)
    resource_constraints: list[str] = Field(default_factory=list,max_length=30)
    risks: list[str] = Field(default_factory=list,max_length=30)
    assumptions: list[str] = Field(default_factory=list,max_length=30)
    governance_prerequisites: list[str] = Field(default_factory=list,max_length=30)
class WorkGroup(StrictModel):
    id: str = Field(min_length=1,max_length=60)
    stage_id: str
    title: str = Field(min_length=1,max_length=200)
class Zone(StrictModel):
    id: str = Field(min_length=1,max_length=60)
    label: str = Field(min_length=1,max_length=200)
    in_scope: bool = True
class Resource(StrictModel):
    id: str = Field(min_length=1,max_length=60)
    title: str = Field(min_length=1,max_length=200)
    kind: Literal["consumable","equipment","service","facility","funding"]
    quantity: float | None = Field(default=None,ge=0,allow_inf_nan=False)
    unit: str = Field(min_length=1,max_length=60)
    work_ids: list[str] = Field(default_factory=list,max_length=500)
class Work(StrictModel):
    id: str = Field(min_length=1,max_length=60)
    stage_id: str
    title: str = Field(min_length=1,max_length=200)
    work_group_id: str = ""
    scope: str = Field(default="",max_length=2000)
    outcome: str = Field(default="",max_length=2000)
    dependency_ids: list[str] = Field(default_factory=list,max_length=500)
    zone_ids: list[str] = Field(default_factory=list,max_length=100)
    volume: Quantity = Field(default_factory=lambda:Quantity(unit="items"))
    effort: Quantity = Field(default_factory=lambda:Quantity(unit="person_hours"))
    duration: Quantity = Field(default_factory=lambda:Quantity(unit="hours"))
    schedule: Schedule = Field(default_factory=Schedule)
    skills: list[str] = Field(default_factory=list,max_length=30)
    resource_requirement_ids: list[str] = Field(default_factory=list,max_length=100)
    role_requirement_ids: list[str] = Field(default_factory=list,max_length=100)
    exclusion_constraints: list[str] = Field(default_factory=list,max_length=30)
    conditions: list[str] = Field(default_factory=list,max_length=30)
    evidence_requirements: list[str] = Field(default_factory=list,max_length=30)
    revision: int = Field(default=1,ge=1)
class ActorRequirement(StrictModel):
    id: str
    title: str = Field(min_length=1,max_length=200)
    stage_ids: list[str]
    work_ids: list[str]
    source_work_ids: list[str]
    required_capabilities: list[str] = Field(default_factory=list,max_length=30)
    proposed_headcount: int | None = Field(default=None,ge=0,le=10000)
    headcount_basis: str = Field(default="Unknown; human capacity review required",max_length=1000)
    schedule_intervals: list[Schedule] = Field(default_factory=list,max_length=500)
    effort_person_hours: float | None = Field(default=None,ge=0,allow_inf_nan=False)
    capacity_assumptions: list[str] = Field(default_factory=list,max_length=30)
    safety_considerations: list[str] = Field(default_factory=list,max_length=30)
    responsibilities: list[str] = Field(default_factory=list,max_length=30)
    coordination_needs: list[str] = Field(default_factory=list,max_length=30)
    resource_responsibilities: list[str] = Field(default_factory=list,max_length=30)
class Dependency(StrictModel):
    predecessor: str
    successor: str

def acyclic(ids,edges):
    incoming={x:0 for x in ids};children={x:[] for x in ids};seen_edges=set()
    for a,b in edges:
        if a not in ids or b not in ids or a==b or (a,b) in seen_edges:raise ValueError("Dangling/self/duplicate dependency")
        seen_edges.add((a,b));incoming[b]+=1;children[a].append(b)
    ready=[x for x,n in incoming.items() if n==0];count=0
    while ready:
        x=ready.pop();count+=1
        for target in children[x]:
            incoming[target]-=1
            if not incoming[target]:ready.append(target)
    if count!=len(ids):raise ValueError("Dependency cycle")

class PlanContent(StrictModel):
    stale_work_ids: list[str] = Field(default_factory=list,max_length=500)
    stages: list[Stage] = Field(default_factory=list,max_length=100)
    work: list[Work] = Field(default_factory=list,max_length=500)
    dependencies: list[Dependency] = Field(default_factory=list,max_length=2000)
    groups: list[WorkGroup] = Field(default_factory=list,max_length=200)
    resources: list[Resource] = Field(default_factory=list,max_length=200)
    roles: list[ActorRequirement] = Field(default_factory=list,max_length=500)
    zones: list[Zone] = Field(default_factory=list,max_length=100)
    @model_validator(mode="after")
    def graph(self):
        maps={name:{x.id:x for x in getattr(self,name)} for name in ['stages','work','groups','resources','roles','zones']}
        if any(len(maps[n])!=len(getattr(self,n)) for n in maps):raise ValueError("Duplicate IDs")
        stages,work=maps['stages'],maps['work']
        outside={w.id for w in self.work if w.stage_id in stages and not stages[w.stage_id].relative_start<=w.schedule.start_day<=w.schedule.end_day<=stages[w.stage_id].relative_end}
        if set(self.stale_work_ids)!=outside:raise ValueError('Stage/work conflicts require exact explicit stale-work markers')
        acyclic(stages,[(p,s.id) for s in self.stages for p in s.dependency_ids])
        edges={(d.predecessor,d.successor) for d in self.dependencies}
        if len(edges)!=len(self.dependencies):raise ValueError("Duplicate dependency")
        edges.update((p,w.id) for w in self.work for p in w.dependency_ids)
        acyclic(work,edges)
        for s in self.stages:
            if s.relative_end<s.relative_start:raise ValueError("Invalid stage window")
            if s.effort.unit not in ('person_hours','person-hours','person hours'):raise ValueError('Stage effort requires person-hours')
            if s.duration.value is not None and (s.duration.unit!='days' or s.duration.value!=s.relative_end-s.relative_start+1):raise ValueError('Stage duration/window mismatch')
            for p in s.dependency_ids:
                if stages[p].relative_end>=s.relative_start:raise ValueError("Incompatible finish-to-start stage timing")
        for g in self.groups:
            if g.stage_id not in stages:raise ValueError("Group stage does not exist")
        for w in self.work:
            if w.stage_id not in stages:raise ValueError("Work stage does not exist")
            s=stages[w.stage_id]
            if not s.relative_start<=w.schedule.start_day<=w.schedule.end_day<=s.relative_end and w.id not in self.stale_work_ids:raise ValueError("Work outside stage window")
            if w.work_group_id and (w.work_group_id not in maps['groups'] or maps['groups'][w.work_group_id].stage_id!=w.stage_id):raise ValueError("Incompatible work group")
            if any(z not in maps['zones'] or not maps['zones'][z].in_scope for z in w.zone_ids):raise ValueError("Unknown/excluded zone")
            if any(r not in maps['resources'] or w.id not in maps['resources'][r].work_ids for r in w.resource_requirement_ids):raise ValueError("Dangling/incompatible resource")
            if any(r not in maps['roles'] or w.id not in maps['roles'][r].work_ids for r in w.role_requirement_ids):raise ValueError("Dangling/incompatible role")
            if w.effort.unit not in ('person_hours','person-hours','person hours'):raise ValueError("Effort requires person-hours")
            if w.duration.value is not None and (w.duration.unit!='hours' or abs(w.duration.value-(w.schedule.finish-w.schedule.start)/60)>0.00001):raise ValueError("Duration/schedule mismatch")
        for a,b in edges:
            if work[a].schedule.finish>work[b].schedule.start:raise ValueError("Incompatible finish-to-start work timing")
        for r in self.resources:
            if any(w not in work for w in r.work_ids):raise ValueError("Dangling resource work reference")
        for r in self.roles:
            if not r.work_ids or any(w not in work for w in r.work_ids+r.source_work_ids) or any(s not in stages for s in r.stage_ids):raise ValueError("Dangling actor requirement")
            if set(r.source_work_ids)!=set(r.work_ids) or set(r.stage_ids)!={work[w].stage_id for w in r.work_ids}:raise ValueError("Actor source/stage coverage mismatch")
        for w in self.work:w.dependency_ids=sorted(a for a,b in edges if b==w.id)
        self.dependencies=[]
        return self
