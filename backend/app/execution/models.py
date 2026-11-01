from datetime import datetime
from sqlalchemy import String,Integer,ForeignKey,UniqueConstraint,DateTime,Numeric
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.shared.database import Base
from app.shared.types import uid,now
class WorkExecution(Base):
    __tablename__='work_executions'
    __table_args__=(UniqueConstraint('event_id','plan_id','work_id',name='uq_execution_work_plan'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    plan_id:Mapped[str]=mapped_column(ForeignKey('plan_versions.id'))
    work_id:Mapped[str]=mapped_column(String(60))
    version:Mapped[int]=mapped_column(Integer,default=0)
    content:Mapped[dict]=mapped_column(JSONB,default=dict)
class WorkReport(Base):
    __tablename__='work_reports'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    plan_id:Mapped[str]=mapped_column(ForeignKey('plan_versions.id'))
    assignment_id:Mapped[str]=mapped_column(ForeignKey('assignments.id'))
    terms_id:Mapped[str]=mapped_column(ForeignKey('assignment_terms.id'))
    account_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    work_id:Mapped[str]=mapped_column(String(60))
    version:Mapped[int]=mapped_column(Integer,default=0)
    content:Mapped[dict]=mapped_column(JSONB,default=dict)
class EvidenceAsset(Base):
    __tablename__='evidence_assets'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    report_id:Mapped[str]=mapped_column(ForeignKey('work_reports.id'))
    account_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    version:Mapped[int]=mapped_column(Integer,default=0)
    content:Mapped[dict]=mapped_column(JSONB,default=dict)
class ExecutionRevision(Base):
    __tablename__='execution_revisions'
    __table_args__=(UniqueConstraint('aggregate_id','sequence',name='uq_execution_revision_sequence'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    aggregate_id:Mapped[str]=mapped_column(String(36))
    sequence:Mapped[int]=mapped_column(Integer)
    kind:Mapped[str]=mapped_column(String(40))
    content:Mapped[dict]=mapped_column(JSONB)
    digest:Mapped[str]=mapped_column(String(64))
    actor_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class ExecutionReviewGrant(Base):
    __tablename__='execution_review_grants'
    __table_args__=(UniqueConstraint('event_id','account_id','stage_id',name='uq_execution_reviewer_stage'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'))
    account_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    stage_id:Mapped[str]=mapped_column(String(60))
    plan_id:Mapped[str]=mapped_column(ForeignKey('plan_versions.id'))
    active:Mapped[bool]=mapped_column(default=True)
class AttendanceRecord(Base):
    __tablename__='attendance_records'
    __table_args__=(UniqueConstraint('event_id','assignment_id',name='uq_attendance_assignment'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'))
    assignment_id:Mapped[str]=mapped_column(ForeignKey('assignments.id'))
    account_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    version:Mapped[int]=mapped_column(Integer,default=0)
    content:Mapped[dict]=mapped_column(JSONB,default=dict)
class ResourceOperation(Base):
    __tablename__='resource_operations'
    __table_args__=(UniqueConstraint('event_id','reference',name='uq_resource_operation_reference'),UniqueConstraint('reverses_id',name='uq_resource_operation_reversal'))
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    reservation_id:Mapped[str]=mapped_column(ForeignKey('resource_reservations.id'))
    report_id:Mapped[str]=mapped_column(ForeignKey('work_reports.id'))
    resource_id:Mapped[str]=mapped_column(String(60))
    report_revision:Mapped[int]=mapped_column(Integer)
    usage_id:Mapped[str]=mapped_column(String(60))
    kind:Mapped[str]=mapped_column(String(30))
    quantity:Mapped[float]=mapped_column(Numeric(16,4))
    reference:Mapped[str]=mapped_column(String(200))
    reverses_id:Mapped[str|None]=mapped_column(ForeignKey('resource_operations.id'))
    created_by:Mapped[str]=mapped_column(ForeignKey('users.id'))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class WorkIssue(Base):
    __tablename__='work_issues'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    plan_id:Mapped[str]=mapped_column(ForeignKey('plan_versions.id'))
    account_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    work_id:Mapped[str]=mapped_column(String(60))
    version:Mapped[int]=mapped_column(Integer,default=0)
    content:Mapped[dict]=mapped_column(JSONB,default=dict)
class CoordinationRecord(Base):
    __tablename__='coordination_records'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    account_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    kind:Mapped[str]=mapped_column(String(30))
    version:Mapped[int]=mapped_column(Integer,default=0)
    content:Mapped[dict]=mapped_column(JSONB,default=dict)
