from app.memory.schemas import Candidate, Assertion, Applicability

def project(sources):
    # Faithful original-source projection: no generated lesson or inferred success.
    return [Candidate(kind="decision" if s.ref.source_kind in ("operational","execution") else s.ref.source_kind,title=f"{s.ref.source_kind.title()} source revision {s.ref.source_revision}",assertions=[Assertion(assertion_id="source",text=s.text[:4000],claim_kind="decision" if s.ref.source_kind in ("operational","execution") else s.ref.source_kind,evidence_stage=s.evidence_stage,outcome=s.outcome,evaluation_criteria=s.criteria,source_refs=[s.ref],uncertainty_reasons=["Bounded excerpt; original source retained"] if len(s.text)>4000 else [])],applicability=Applicability.model_validate(s.applicability)) for s in sources]
