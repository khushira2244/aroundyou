from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.database import Base
from app.shared.types import uid, now

class MemoryRun(Base):
    __tablename__ = "memory_runs"
    __table_args__ = (UniqueConstraint("event_id", "id", name="uq_run_event_id"), UniqueConstraint("event_id", "dedup_key", name="uq_memory_run_dedup"), CheckConstraint("status IN ('queued','running','succeeded','failed','cancelled','stale')", name="ck_memory_run_status"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(20), default="extraction")
    query_digest: Mapped[str | None] = mapped_column(String(64))
    selection_manifest: Mapped[list] = mapped_column(JSONB, default=list)
    purpose: Mapped[str] = mapped_column(String(30))
    extractor: Mapped[str] = mapped_column(String(30))
    schema_version: Mapped[str] = mapped_column(String(20))
    policy_version: Mapped[str] = mapped_column(String(20), default="event-only-v1")
    dedup_key: Mapped[str] = mapped_column(String(64))
    source_manifest: Mapped[list] = mapped_column(JSONB)
    source_manifest_digest: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    output_entry_ids: Mapped[list] = mapped_column(JSONB, default=list)
    failure_code: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class MemoryEntry(Base):
    __tablename__ = "memory_entries"
    __table_args__ = (UniqueConstraint("event_id", "id", name="uq_memory_event_id"), UniqueConstraint("logical_memory_id", "revision", name="uq_memory_revision"),
        ForeignKeyConstraint(["event_id", "supersedes_id"], ["memory_entries.event_id", "memory_entries.id"], name="fk_memory_predecessor"),
        ForeignKeyConstraint(["event_id", "run_id"], ["memory_runs.event_id", "memory_runs.id"], name="fk_memory_run_scope"),
        ForeignKeyConstraint(["event_id", "review_decision_id"], ["review_decisions.event_id", "review_decisions.id"], name="fk_memory_review_scope"),
        CheckConstraint("revision > 0 AND version > 0", name="ck_memory_version"),
        CheckConstraint("lifecycle IN ('candidate','published','superseded','retracted')", name="ck_memory_lifecycle"),
        CheckConstraint("visibility = 'event'", name="ck_memory_event_only"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    logical_memory_id: Mapped[str] = mapped_column(String(36), index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    version: Mapped[int] = mapped_column(Integer, default=1)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    assertions: Mapped[list] = mapped_column(JSONB)
    applicability: Mapped[dict] = mapped_column(JSONB)
    origin: Mapped[str] = mapped_column(String(30))
    schema_version: Mapped[str] = mapped_column(String(20))
    extractor_version: Mapped[str] = mapped_column(String(80))
    model_profile: Mapped[str | None] = mapped_column(String(120))
    run_id: Mapped[str | None] = mapped_column(String(36))
    lifecycle: Mapped[str] = mapped_column(String(20))
    visibility: Mapped[str] = mapped_column(String(20), default="event")
    review_decision_id: Mapped[str | None] = mapped_column(String(36))
    supersedes_id: Mapped[str | None] = mapped_column(String(36))
    correction_reason: Mapped[str | None] = mapped_column(String(2000))
    digest: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class MemorySource(Base):
    __tablename__ = "memory_sources"
    __table_args__ = (ForeignKeyConstraint(["event_id", "memory_entry_id"], ["memory_entries.event_id", "memory_entries.id"], name="fk_memory_source_scope"),
        UniqueConstraint("memory_entry_id", "assertion_id", "source_kind", "source_id", name="uq_memory_source_assertion"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    memory_entry_id: Mapped[str] = mapped_column(String(36), index=True)
    assertion_id: Mapped[str] = mapped_column(String(60))
    source_kind: Mapped[str] = mapped_column(String(30))
    source_id: Mapped[str] = mapped_column(String(36))
    source_revision: Mapped[int] = mapped_column(Integer)
    source_digest: Mapped[str] = mapped_column(String(64))
    source_state_at_capture: Mapped[str] = mapped_column(String(20))
    access_class: Mapped[str] = mapped_column(String(20))
    relation: Mapped[str] = mapped_column(String(20), default="supports")
