from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class SourceRef(StrictModel):
    source_kind: Literal["context", "plan", "decision", "operational", "execution"]
    source_id: str = Field(min_length=1, max_length=36)
    source_revision: int = Field(ge=1)
    source_digest: str = Field(pattern=r"^[a-f0-9]{64}$")

class Applicability(StrictModel):
    category: str | None = Field(default=None, max_length=80)
    tags: list[str] = Field(default_factory=list, max_length=20)
    goal: str | None = Field(default=None, max_length=500)
    work_pattern: str | None = Field(default=None, max_length=200)
    conditions: list[str] = Field(default_factory=list, max_length=20)
    exclusions: list[str] = Field(default_factory=list, max_length=20)
    unknowns: list[str] = Field(default_factory=list, max_length=20)
    @field_validator("tags", "conditions", "exclusions", "unknowns")
    @classmethod
    def bounded_items(cls, values):
        if any(not x or len(x)>300 for x in values):
            raise ValueError("Items require 1..300 characters")
        return values

class ExtractionRequest(StrictModel):
    source_refs: list[SourceRef] = Field(min_length=1, max_length=20)
    extractor: Literal["deterministic", "open_weight"] = "deterministic"
    schema_version: Literal["memory-v1"] = "memory-v1"
    purpose: Literal["planning", "blocker_recovery", "event_review"] = "planning"
    @model_validator(mode="after")
    def unique_sources(self):
        if len({(x.source_kind,x.source_id) for x in self.source_refs}) != len(self.source_refs):
            raise ValueError("Duplicate sources")
        return self

class Assertion(StrictModel):
    assertion_id: str = Field(min_length=1, max_length=60)
    text: str = Field(min_length=1, max_length=4000)
    claim_kind: Literal["context", "plan", "decision", "lesson"]
    evidence_stage: Literal["proposed", "attempted", "verified"] = "proposed"
    outcome: Literal["unknown", "successful", "failed", "mixed", "inconclusive"] = "unknown"
    evaluation_criteria: str | None = Field(default=None, max_length=2000)
    source_refs: list[SourceRef] = Field(min_length=1, max_length=20)
    uncertainty_reasons: list[str] = Field(default_factory=list, max_length=20)
    confidence_basis: Literal["source_record", "reviewed_synthesis", "model_estimate"] = "source_record"
    model_confidence: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)

class Candidate(StrictModel):
    kind: Literal["context", "plan", "decision", "lesson"]
    title: str = Field(min_length=1, max_length=200)
    assertions: list[Assertion] = Field(min_length=1, max_length=20)
    applicability: Applicability
    @model_validator(mode="after")
    def unique_assertions(self):
        if len({x.assertion_id for x in self.assertions})!=len(self.assertions):
            raise ValueError("Duplicate assertion IDs")
        return self

class ReviewRequest(StrictModel):
    decision: Literal["publish", "reject"]
    reviewed_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_revision: int = Field(ge=1)
    note: str = Field(default="", max_length=2000)

class CorrectionRequest(StrictModel):
    reason: str = Field(min_length=1, max_length=2000)
    correcting_source_refs: list[SourceRef] = Field(min_length=1, max_length=20)
    reviewed_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_revision: int = Field(ge=1)

class RetractionRequest(StrictModel):
    reason: str = Field(min_length=1, max_length=2000)
    reviewed_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_revision: int = Field(ge=1)
