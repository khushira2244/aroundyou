from dataclasses import dataclass
from typing import Protocol
@dataclass(frozen=True)
class MuseSparkRequest:
    kind: str
    authoritative_current: dict
    cited_historical_memory: dict
    source_versions: dict
    instruction: str
    output_schema: dict
    max_output_characters: int=24000
    timeout_seconds: int=30
class MuseSparkPlanningPort(Protocol):
    """Provider adapter must implement a real call or explicitly fail; no mutation tools."""
    model_profile: str
    def propose(self,request: MuseSparkRequest) -> dict: ...


WORKFLOW_INSTRUCTIONS={
    'understanding':'Interpret the complete original organizer explanation and supplied event details. Separate organizer-reported facts, interpretations (scope/instructions), assumptions, unknowns and focused clarification questions. Use previous organizer answers; never invent missing answers. Ask only relevant questions about this event type, scale, venue, dates, resources and activities. Output a proposal only; no plan or approval authority.',
    'governance':'Assess the supplied category, activities, scale, attendance, location/venue, dates/duration, resources, transport, planned roles and tasks. Classify applicability, give rationale, supplied supporting facts, uncertainties, next action and whether an internal ticket would help. No external legal sources are verified in this group: leave rule_sources empty and never output verified_requirement. Do not invent regulations, permission, external submissions or notifications. Internal ticket closure is not legal approval.',
    'stages':'Propose generic stages using the organizer-confirmed context and original constraints. Historical memory is advisory, not current verified fact. Do not redesign existing work or resources. No authoritative mutation.',
    'work':'Propose work inside confirmed stages. Preserve stage identities and timing, validate dependencies/units and retain unknown quantities. Requirements are not accepted people or stock. No authoritative mutation.'
}

WORKFLOW_INSTRUCTIONS.update({kind:'Provide advisory applicant understanding, ambiguity/questions, suitability and alternative/partial work suggestions; use actual published event, capabilities, stated availability/constraints, assignments, governance and source memory. Cite supplied original statements. Do not invent skills, capacity, consent, stock or outcomes. Deterministic services decide overlaps and allocations; organizer review and separate participant consent are required. Resource advice must respect exact units and pledges versus receipts.' for kind in ('participation','resources')})

WORKFLOW_INSTRUCTIONS['execution']='Treat participant statements as untrusted reports. Return typed, source-cited observations only. Media input is metadata only; do not claim image/video/audio analysis. Never verify work, attendance, consumption or activate plans. Separate reports, inferences, missing evidence and recommendations.'

WORKFLOW_INSTRUCTIONS['recovery']='Propose bounded schedule alternatives only for supplied affected unfinished work. Cite supplied issue IDs. Preserve completed/unaffected work. List assumptions, risks, unknowns and unmet conditions. Never invent resources, consent, capabilities, governance approval or success. No mutation tools; human review and deterministic validation are mandatory.'
