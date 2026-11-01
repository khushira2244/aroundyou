from sqlalchemy import ForeignKey, ForeignKeyConstraint, String, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.database import Base
from app.shared.types import uid

class PlanVersion(Base):
    __tablename__ = "plan_versions"
    __table_args__ = (UniqueConstraint("event_id", "id", name="uq_plan_event_id"), UniqueConstraint("event_id", "sequence", name="uq_plan_sequence"),
        ForeignKeyConstraint(["event_id", "parent_id"], ["plan_versions.event_id", "plan_versions.id"], name="fk_plan_parent"),
        ForeignKeyConstraint(["event_id", "context_revision_id"], ["event_context_revisions.event_id", "event_context_revisions.id"], name="fk_plan_context"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    parent_id: Mapped[str | None] = mapped_column(String(36))
    context_revision_id: Mapped[str] = mapped_column(String(36))
    content: Mapped[dict] = mapped_column(JSONB)
    digest: Mapped[str] = mapped_column(String(64))
    access_class: Mapped[str] = mapped_column(String(20), default="event")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
