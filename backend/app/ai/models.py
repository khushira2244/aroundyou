from datetime import datetime
from sqlalchemy import ForeignKey,String,Integer,DateTime,CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped,mapped_column
from app.shared.database import Base
from app.shared.types import uid,now
class AIRun(Base):
    __tablename__='ai_runs'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id: Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    requester_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    kind: Mapped[str]=mapped_column(String(30))
    status: Mapped[str]=mapped_column(String(30),default='queued')
    source_versions: Mapped[dict]=mapped_column(JSONB)
    context_manifest: Mapped[dict]=mapped_column(JSONB)
    request_message: Mapped[str]=mapped_column(String(2000),default='')
    failure_code: Mapped[str|None]=mapped_column(String(80))
    proposal_id: Mapped[str|None]=mapped_column(String(36))
    model_profile: Mapped[str|None]=mapped_column(String(120))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class AIProposal(Base):
    __tablename__='ai_proposals'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id: Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    run_id: Mapped[str|None]=mapped_column(ForeignKey('ai_runs.id'))
    kind: Mapped[str]=mapped_column(String(30))
    status: Mapped[str]=mapped_column(String(30),default='pending')
    source_versions: Mapped[dict]=mapped_column(JSONB)
    payload: Mapped[dict]=mapped_column(JSONB)
    digest: Mapped[str]=mapped_column(String(64))
    provenance: Mapped[dict]=mapped_column(JSONB)
    review_decision_id: Mapped[str|None]=mapped_column(ForeignKey('review_decisions.id'))
