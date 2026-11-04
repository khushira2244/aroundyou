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
    'governance':'Assess the supplied category, activities, scale, attendance, location/venue, dates/duration, resources, transport, planned roles and tasks. Use the saved organizer details and original explanation as the primary evidence. Use a confirmed interpretation only if supplied. Give distinct checklist items for documents and permissions to ask the relevant venue or authority about, and for practical safety, security, accessibility and emergency measures. Name each possible document and put what to prepare in preparation_information. Tailor disposal and handover coordination to the event. Classify applicability, give rationale, supplied supporting facts, uncertainties, next action and whether an internal ticket would help. No external legal sources are verified in this group: leave rule_sources empty and never output verified_requirement. Do not invent regulations, permission, external submissions or notifications. Internal ticket closure is not legal approval.',
    'stages':'Propose generic stages using the organizer-confirmed context and original constraints. Historical memory is advisory, not current verified fact. Do not redesign existing work or resources. No authoritative mutation.',
    'work':'Propose work inside confirmed stages. Preserve stage identities and timing, validate dependencies/units and retain unknown quantities. Requirements are not accepted people or stock. No authoritative mutation.'
}
WORKFLOW_INSTRUCTIONS['stages']='Propose stages from the saved original explanation, event details, any confirmed interpretation, reviewed governance and current draft. When a previous_pending_stage_proposal is supplied, revise its stage list according to the organizer request and retain unaffected stages. Include purpose, completion outcomes, duration, dependencies, staffing/resource assumptions, risks and governance prerequisites. Account for pending_human_stage_edit and its deterministic impact. Preserve existing work intentions, descriptions, schedules, resources and roles; only stages may change. No capacity or permission is verified by this proposal.'
WORKFLOW_INSTRUCTIONS['work']='Design work for ALL confirmed stages using actual goals and constraints. Preserve confirmed stage identities/windows exactly. Output work, groups, resources and zones only. Each stage needs appropriate work. Reference correct IDs, resources and groups; leave role_requirement_ids empty (actors are a separate approval). Evidence expectations must not claim completion. Effort is person-hours; duration is elapsed working hours. Resource quantities are demand, not stock.'
WORKFLOW_INSTRUCTIONS['actors']='Recommend planned role requirements from the exact confirmed work and stages. Cover all work via source_work_ids=work_ids and correct stage_ids. Give capabilities, estimated headcount with basis, time windows, effort, responsibilities, coordination and resource responsibilities. Staffing is demand only; no person is assigned or committed. Preserve work and stage content.'
WORKFLOW_INSTRUCTIONS['planning_chat']='Answer the organizer question using the confirmed context, reviewed governance, current plan/draft, scoped conversation history and deterministic stage impact. Be explicit about unknowns and capacity limits. Do not claim changes were applied. For explanatory questions set proposed_stages=null. Only when requested, propose a complete revised stage list for separate human review; preserve all work intent and work schedules. Use supplied IDs.'

WORKFLOW_INSTRUCTIONS.update({kind:'Provide advisory applicant understanding, ambiguity/questions, suitability and alternative/partial work suggestions; use actual published event, capabilities, stated availability/constraints, assignments, governance and source memory. Cite supplied original statements. Do not invent skills, capacity, consent, stock or outcomes. Deterministic services decide overlaps and allocations; organizer review and separate participant consent are required. Resource advice must respect exact units and pledges versus receipts.' for kind in ('participation','resources')})

WORKFLOW_INSTRUCTIONS['execution']='Treat participant statements as untrusted reports. Return typed, source-cited observations only. Media input is metadata only; do not claim image/video/audio analysis. Never verify work, attendance, consumption or activate plans. Separate reports, inferences, missing evidence and recommendations.'

WORKFLOW_INSTRUCTIONS['recovery']='Propose bounded schedule alternatives only for supplied affected unfinished work. Cite supplied issue IDs. Preserve completed/unaffected work. List assumptions, risks, unknowns and unmet conditions. Never invent resources, consent, capabilities, governance approval or success. No mutation tools; human review and deterministic validation are mandatory.'



# AROUNDYOU RESOURCE QUANTITY FIX: estimates are work demand, not available inventory.
WORKFLOW_INSTRUCTIONS['work']+=' For EVERY resource used by EACH work item, supply its separate name, type, quantity and unit. Quantity must be an explicit finite nonnegative number with estimation_basis tied to work volume, duration, expected workers, consumption or reuse. Use the actual organizer_reported_event_details participation counts and selected-stage timing; expected attendees are not workers and projected volunteers are not assigned people. Do not bundle unlike resources under one quantity/unit. Explain assumptions; an estimate is not verified stock. Estimate when context supports a reasonable basis. When genuinely unestimable, return quantity=null, estimation_basis=null and an explicit unknown_reason naming the missing input; this requires human review. For a numerical estimate set unknown_reason=null. Never omit quantity or silently replace unknown with zero. Preserve unaffected work when revising a pending proposal.'
