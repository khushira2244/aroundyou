from datetime import datetime
from sqlalchemy import String,Integer,ForeignKey,UniqueConstraint,DateTime,Numeric,Index,text
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.shared.database import Base
from app.shared.types import uid,now

class Application(Base):
    __tablename__='applications'
    __table_args__=(UniqueConstraint('event_id','account_id',name='uq_application_account_event'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    account_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    plan_id:Mapped[str]=mapped_column(ForeignKey('plan_versions.id'))
    version:Mapped[int]=mapped_column(Integer,default=1)
    sequence:Mapped[int]=mapped_column(Integer,default=0)
    status:Mapped[str]=mapped_column(String(30),default='application_draft')
    content:Mapped[dict]=mapped_column(JSONB,default=dict)

class ApplicationRevision(Base):
    __tablename__='application_revisions'
    __table_args__=(UniqueConstraint('application_id','sequence',name='uq_application_sequence'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'))
    application_id:Mapped[str]=mapped_column(ForeignKey('applications.id'))
    sequence:Mapped[int]=mapped_column(Integer)
    content:Mapped[dict]=mapped_column(JSONB)
    digest:Mapped[str]=mapped_column(String(64))
    created_by:Mapped[str]=mapped_column(ForeignKey('users.id'))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class Assignment(Base):
    __tablename__='assignments'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    application_id:Mapped[str]=mapped_column(ForeignKey('applications.id'))
    account_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    version:Mapped[int]=mapped_column(Integer,default=1)
    status:Mapped[str]=mapped_column(String(40),default='assignment_offered')
    current_terms_id:Mapped[str|None]=mapped_column(ForeignKey('assignment_terms.id',use_alter=True,name='fk_assignment_terms'))

class AssignmentTerms(Base):
    __tablename__='assignment_terms'
    __table_args__=(UniqueConstraint('assignment_id','sequence',name='uq_assignment_term_sequence'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'))
    assignment_id:Mapped[str]=mapped_column(ForeignKey('assignments.id'))
    plan_id:Mapped[str]=mapped_column(ForeignKey('plan_versions.id'))
    sequence:Mapped[int]=mapped_column(Integer)
    content:Mapped[dict]=mapped_column(JSONB)
    digest:Mapped[str]=mapped_column(String(64))
    created_by:Mapped[str]=mapped_column(ForeignKey('users.id'))
    expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))

class AssignmentConsent(Base):
    __tablename__='assignment_consents'
    __table_args__=(UniqueConstraint('terms_id','account_id',name='uq_terms_account_consent'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'))
    terms_id:Mapped[str]=mapped_column(ForeignKey('assignment_terms.id'))
    account_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    decision:Mapped[str]=mapped_column(String(20))
    digest:Mapped[str]=mapped_column(String(64))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class OperationalSource(Base):
    __tablename__='operational_sources'
    __table_args__=(UniqueConstraint('event_id','aggregate_id','sequence',name='uq_operational_source_sequence'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    aggregate_id:Mapped[str]=mapped_column(String(36))
    sequence:Mapped[int]=mapped_column(Integer)
    kind:Mapped[str]=mapped_column(String(40))
    content:Mapped[dict]=mapped_column(JSONB)
    digest:Mapped[str]=mapped_column(String(64))
    created_by:Mapped[str]=mapped_column(ForeignKey('users.id'))
