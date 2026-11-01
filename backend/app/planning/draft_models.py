from sqlalchemy import ForeignKey,String,Integer,Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped,mapped_column
from app.shared.database import Base
from app.shared.types import uid
class PlanningDraft(Base):
    __tablename__='planning_drafts'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id: Mapped[str]=mapped_column(ForeignKey('events.id'),unique=True)
    context_revision_id: Mapped[str]=mapped_column(ForeignKey('event_context_revisions.id'))
    content: Mapped[dict]=mapped_column(JSONB,default=dict)
    version: Mapped[int]=mapped_column(Integer,default=1)
    stage_revision: Mapped[int]=mapped_column(Integer,default=1)
    work_revision: Mapped[int]=mapped_column(Integer,default=1)
    stage_confirmed: Mapped[bool]=mapped_column(Boolean,default=False)
    work_confirmed: Mapped[bool]=mapped_column(Boolean,default=False)
    actors_confirmed: Mapped[bool]=mapped_column(Boolean,default=False)
    derived_from: Mapped[dict|None]=mapped_column(JSONB)
