from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.database import Base
from app.shared.types import uid, now

class ReviewDecision(Base):
    __tablename__ = "review_decisions"
    __table_args__ = (UniqueConstraint("event_id", "id", name="uq_review_event_id"), ForeignKeyConstraint(["event_id","supersedes_id"],["review_decisions.event_id","review_decisions.id"],name="fk_review_predecessor"), CheckConstraint("evidence_stage IN ('proposed','attempted','verified')", name="ck_review_stage"), CheckConstraint("outcome IN ('unknown','successful','failed','mixed','inconclusive')", name="ck_review_outcome"), CheckConstraint("outcome NOT IN ('successful','failed','mixed') OR (evidence_stage = 'verified' AND length(criteria) > 0)",name="ck_review_outcome_basis"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    supersedes_id: Mapped[str | None] = mapped_column(String(36), unique=True)
    subject_kind: Mapped[str] = mapped_column(String(30))
    subject_id: Mapped[str] = mapped_column(String(36))
    subject_digest: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(30))
    evidence_stage: Mapped[str] = mapped_column(String(20), default="proposed")
    outcome: Mapped[str] = mapped_column(String(20), default="unknown")
    criteria: Mapped[str] = mapped_column(String(2000), default="")
    note: Mapped[str] = mapped_column(String(4000), default="")
    reviewed_content: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("events.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    operation: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str] = mapped_column(String(36))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("actor_id", "scope", "operation", "key", name="uq_idempotency"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    scope: Mapped[str] = mapped_column(String(36))
    operation: Mapped[str] = mapped_column(String(80))
    key: Mapped[str] = mapped_column(String(128))
    payload_hash: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict] = mapped_column(JSONB)

class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    dedup_key: Mapped[str] = mapped_column(String(160), unique=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class JobTask(Base):
    __tablename__ = "job_tasks"
    __table_args__ = (CheckConstraint("attempt_count >= 0 AND max_attempts > 0 AND fencing_token >= 0", name="ck_job_bounds"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    outbox_id: Mapped[str | None] = mapped_column(ForeignKey("outbox_events.id"), unique=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("memory_runs.id"), unique=True)
    ai_run_id: Mapped[str | None] = mapped_column(ForeignKey("ai_runs.id"), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[str | None] = mapped_column(String(80))
    fencing_token: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(60))
