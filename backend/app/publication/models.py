from datetime import datetime
from sqlalchemy import ForeignKey,ForeignKeyConstraint,String,Integer,UniqueConstraint,DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped,mapped_column
from app.shared.database import Base
from app.shared.types import uid,now
class SetupRevision(Base):
    __tablename__='event_setup_revisions'
    __table_args__=(UniqueConstraint('event_id','sequence',name='uq_setup_sequence'),UniqueConstraint('event_id','id',name='uq_setup_event'))
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id: Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    sequence: Mapped[int]=mapped_column(Integer)
    source_plan_id: Mapped[str]=mapped_column(ForeignKey('plan_versions.id'))
    configuration: Mapped[dict]=mapped_column(JSONB)
    digest: Mapped[str]=mapped_column(String(64))
    created_by: Mapped[str]=mapped_column(ForeignKey('users.id'))
class Finalization(Base):
    __tablename__='event_finalizations'
    __table_args__=(UniqueConstraint('event_id','id',name='uq_finalization_event'),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id: Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    setup_revision_id: Mapped[str]=mapped_column(ForeignKey('event_setup_revisions.id'))
    plan_id: Mapped[str]=mapped_column(ForeignKey('plan_versions.id'))
    reviewed_digest: Mapped[str]=mapped_column(String(64))
    approved_by: Mapped[str]=mapped_column(ForeignKey('users.id'))
class Publication(Base):
    __tablename__='publications'
    __table_args__=(UniqueConstraint('event_id','sequence',name='uq_publication_sequence'),UniqueConstraint('event_id','id',name='uq_publication_event'))
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id: Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    sequence: Mapped[int]=mapped_column(Integer)
    finalization_id: Mapped[str]=mapped_column(ForeignKey('event_finalizations.id'))
    plan_id: Mapped[str]=mapped_column(ForeignKey('plan_versions.id'))
    setup_revision_id: Mapped[str]=mapped_column(ForeignKey('event_setup_revisions.id'))
    snapshot: Mapped[dict]=mapped_column(JSONB)
    digest: Mapped[str]=mapped_column(String(64))
    visibility: Mapped[str]=mapped_column(String(30))
    published_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    approved_by: Mapped[str]=mapped_column(ForeignKey('users.id'))
class PublishedRole(Base):
    __tablename__='published_roles'
    __table_args__=(UniqueConstraint('publication_id','requirement_id',name='uq_published_requirement'),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id: Mapped[str]=mapped_column(ForeignKey('events.id'))
    publication_id: Mapped[str]=mapped_column(ForeignKey('publications.id'))
    plan_id: Mapped[str]=mapped_column(ForeignKey('plan_versions.id'))
    requirement_id: Mapped[str]=mapped_column(String(60))
