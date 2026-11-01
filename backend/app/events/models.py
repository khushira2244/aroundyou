from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, String, Text, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.database import Base
from app.shared.types import uid

class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        ForeignKeyConstraint(["id", "active_context_revision_id"], ["event_context_revisions.event_id", "event_context_revisions.id"], name="fk_event_context", use_alter=True),
        ForeignKeyConstraint(["id", "active_plan_id"], ["plan_versions.event_id", "plan_versions.id"], name="fk_event_plan", use_alter=True),
        ForeignKeyConstraint(["id","current_setup_id"],["event_setup_revisions.event_id","event_setup_revisions.id"],name="fk_event_setup",use_alter=True),
        ForeignKeyConstraint(["id","current_finalization_id"],["event_finalizations.event_id","event_finalizations.id"],name="fk_event_finalization",use_alter=True),
        ForeignKeyConstraint(["id","current_publication_id"],["publications.event_id","publications.id"],name="fk_event_publication",use_alter=True),
        CheckConstraint("version > 0", name="ck_event_version"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    creator_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    lifecycle: Mapped[str] = mapped_column(String(30), default="created_unpublished")
    draft_step: Mapped[int] = mapped_column(Integer, default=1)
    draft_form: Mapped[dict] = mapped_column(JSONB, default=dict)
    interpretation: Mapped[dict | None] = mapped_column(JSONB)
    current_setup_id: Mapped[str | None] = mapped_column(String(36))
    current_finalization_id: Mapped[str | None] = mapped_column(String(36))
    current_publication_id: Mapped[str | None] = mapped_column(String(36))
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(80))
    version: Mapped[int] = mapped_column(Integer, default=1)
    active_context_revision_id: Mapped[str | None] = mapped_column(String(36))
    active_plan_id: Mapped[str | None] = mapped_column(String(36))

class ContextRevision(Base):
    __tablename__ = "event_context_revisions"
    __table_args__ = (UniqueConstraint("event_id", "id", name="uq_context_event_id"), UniqueConstraint("event_id", "sequence", name="uq_context_sequence"),
        ForeignKeyConstraint(["event_id", "supersedes_id"], ["event_context_revisions.event_id", "event_context_revisions.id"], name="fk_context_predecessor"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    original_text: Mapped[str] = mapped_column(Text)
    source_kind: Mapped[str] = mapped_column(String(30), default="written")
    access_class: Mapped[str] = mapped_column(String(20), default="private")
    content_hash: Mapped[str] = mapped_column(String(64))
    applicability: Mapped[dict] = mapped_column(JSONB, default=dict)
    snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    supersedes_id: Mapped[str | None] = mapped_column(String(36))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
