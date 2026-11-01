# CODEX — AroundYou Backend Group 3: Participation, Assignments, Resources & Sponsorship

## Objective

Implement **Group 3** of AroundYou's backend, building on the completed and verified Groups 1 and 2.

This is an implementation task, not another architecture-only review.

Group 2 Prompt 2 completed with:
- 89 PostgreSQL backend tests passing.
- 66 frontend tests passing.
- 146 existing demo tests passing.
- TypeScript and production build passing.
- Migration 0003 completed.
- Source-linked Event Memory, immutable context revisions, human proposal reviews and advisory governance tickets implemented.

Group 3 has not started.

**Read the existing code, approved API catalogue, database model, frontend contracts, Group 1 report, Group 2 report and Group 2 Prompt 2 implementation report before coding.**

Preserve the existing architecture: one FastAPI modular monolith, PostgreSQL, SQLAlchemy/UoW, Alembic, authenticated access, audit, idempotency, source-linked Event Memory and the AroundYouService frontend boundary.

AroundYou supports many types of community initiatives. Canary Hill is a demonstration scenario, not a hardcoded product template.

---

## 1. Participant Application and Joining

Implement the complete existing Join Event flow.

A participant should be able to:

- Discover an eligible published event.
- Read its current public-safe roles and work requirements.
- Select one or more roles or work items.
- Provide skills, experience, availability, preferences and constraints.
- Answer event-specific application questions.
- Save and resume an application if supported by the reviewed frontend contract.
- Submit an application for organizer review.
- View application status and any clarification requests.

Preserve original applicant responses and subsequent revisions.

Validate event visibility, application eligibility, required fields, event-specific participation conditions and submission idempotency.

Do not count an application as an accepted commitment.

## 2. AI Participation Intelligence

Implement a typed, provider-neutral AI advisory workflow compatible with later Meta Muse Spark integration.

The AI must receive **the actual event context**, not merely a list of skills.

Relevant inputs:

- Confirmed event purpose and context.
- Current published plan version.
- Stage and work requirements.
- Required capabilities and skills.
- Applicant-provided information.
- Availability and location constraints.
- Existing authoritative assignments.
- Relevant governance conditions.
- Resource/work dependencies where applicable.
- Eligible, source-linked Event Memory.

### AI responsibilities

A. **Applicant understanding:** interpret experience, skills and stated constraints; identify ambiguity and propose clarifying questions.

B. **Suitability analysis:** explain which work or roles match an applicant, where capabilities are missing, and which information is insufficient.

C. **Assignment recommendations:** suggest suitable work, alternative roles or partial participation, with reasons and trade-offs.

D. **Scheduling/capacity reasoning:** explain potential workload and coverage issues; use deterministic checks for actual overlaps, maximum capacity and timing restrictions.

E. **Resource advisory:** examine whether offers match requirements, identify unfulfilled needs and explain constraints.

F. **Participation insights:** explain capability gaps, unfilled roles and resource shortages based on authorized, current data.

The AI must not invent skills, accepted assignments, availability, resource inventory, attendance or outcomes.

### Implementation rules

- Implement typed requests and validated response schemas.
- Bind recommendations to exact event, plan, application and resource versions.
- Use the existing source-aware context builder and memory retrieval ports.
- Preserve authoritative facts separately from inferred suggestions.
- Support clarification/review/rejection without modifying original answers.
- Require organizer action before creating assignment offers.
- Never automatically accept an assignment for a participant.
- Treat unavailable/malformed/stale model output as advisory failure, not implicit approval.
- Apply bounded execution, retries and error handling consistently with existing AI infrastructure.

**Do not call Muse Spark or Modal live in Group 3.** Tests must use explicitly identified non-live adapters. Do not present test fixtures as real inference.

Do not introduce unnecessary multi-agent orchestration or a separate AI microservice. Reuse the existing architecture.

## 3. Organizer Application Review

Implement authenticated, work-linked application review.

Organizer actions should include:

- View applicants for their event.
- Inspect responses and evidence relevant to the application.
- Review AI recommendations if available.
- Ask for clarification.
- Approve selected work choices.
- Reject other choices independently.
- Create precise assignment offers.
- Edit or withdraw pending offers.
- Record review explanations and history.

Partial acceptance must be supported where the frontend contract allows it.

An organizer's approval creates an **offer**, not automatically an active commitment.

Every review must be version-bound and auditable.

## 4. Assignment Acceptance and Consent

Implement the complete offer lifecycle:

Application → Organizer review → Offer → Participant acceptance/decline → Authoritative assignment.

An offer must contain the exact role, work, schedule, location and material conditions the participant is accepting.

Validate:

- Current work/plan version.
- Participant identity.
- Eligibility.
- Availability.
- Schedule overlap.
- Work capacity.
- Duplicate assignment.
- Changed material terms.
- Expired or withdrawn offers.

A materially changed offer requires explicit renewed acceptance.

Declined, expired or withdrawn offers must not count as accepted commitments.

No automatic consent through AI recommendations or organizer approval.

## 5. My Events, Participant Workspace and Organizer Views

Wire server-side read projections into the existing frontend contracts for Group 3 where feasible.

The same persisted source records should determine:

- Organizing events.
- Participating events.
- Pending applications and offers.
- Accepted roles.
- Personal work schedule.
- Assigned responsibilities.
- Organizer applicant queues.
- Role coverage and capability gaps.
- Actor Tree participation.
- Safe public participation counts.
- Relevant participation-map information.

Preserve the existing distinction between joining, an offer and accepted participation.

Do not create a second My Events page or second organizer dashboard.

Respect field-level permissions and private information.

For public-safe demographic or participant insight aggregates, preserve the existing suppression/privacy rules, including the current demo's minimum group threshold where applicable.

## 6. Sponsorship and Support

Implement the reviewed sponsor/support workflow, including organization-scoped permissions when relevant.

Support:

- Individual and organizational support intentions.
- Resource/material/equipment/service offers.
- Sponsor application or onboarding requests.
- Organizer review.
- Accepted commitments.
- Fulfillment records.
- Verified delivery/receipt.
- Sponsor withdrawal or revision where allowed.
- Public-safe sponsor profile projections.

Keep actual sponsorship evidence separate from promises.

Do not fabricate organization membership, fulfilled donations, payment settlement or completed deliveries.

If external payment processing is not part of the approved contract, preserve payment references/intents without claiming money has been received.

## 7. Resource Requirements and Accounting

Build real resource coordination linked to event plans and work items.

Track separately:

- Required quantity.
- Offered quantity.
- Organizer-accepted pledged quantity.
- Verified received quantity.
- Available quantity.
- Reserved quantity.
- Consumed quantity, when supported by actual authorized records.
- Shortages and remaining needs.

Support units, resource categories, evidence references, ownership or custody where needed, and work associations.

Implement deterministic concurrency and allocation checks.

Prevent:

- Double reservation.
- Negative available quantity.
- Unsupported unit conversion.
- Treating pledges as inventory.
- Treating delivery as work completion.
- Invented fulfillment or stock.
- Cross-event resource access without permission.

If physical usage and execution evidence belong in Group 4, create only the safe reservation/receipt boundary now and explicitly defer consumption commands.

## 8. Group 3 Governance and Event Memory Integration

Reuse Group 2 governance and Event Memory.

Governance remains **advisory plus internal ticket tracking only**. There are no external authority accounts or automatic approval submissions.

Participant and resource checks should use applicable reviewed event requirements, not fabricate legal restrictions.

Preserve the distinctions between:
- Organizer condition.
- Verified operational constraint.
- AI recommendation.
- Unknown external requirement.

Record appropriate authoritative changes with outbox/audit events.

Add source-backed memory integration only where genuine persisted application, offer, consent or resource records support it.

Do not promote an AI suitability score, sponsor promise or organizer offer into verified work success.

Historical Event Memory can inform suggestions but cannot authorize participants, create inventory or override current facts.

Cross-event memory sharing remains disabled unless an already approved secure mechanism exists.

## 9. Database, APIs and Frontend Compatibility

Extend the existing PostgreSQL schema through additive Alembic migrations.

Reuse the Group 1/2 identity, access, UoW, idempotency, source revision and outbox services.

Follow existing API conventions and frontend DTOs.

Implement domain-owned endpoints for applications, review, offers, acceptance, participation queries, sponsorship, resource accounting and AI advisory runs.

Avoid inventing duplicate endpoints when an approved contract already exists.

Keep transitions transactional with exact expected-version checks and durable audit history.

Preserve frontend screens and styles.

Extend the opt-in HTTP adapter for verified Group 3 features. Do not silently mix demo and HTTP data for the same event.

### PostgreSQL configuration

The configured application DATABASE_URL previously contained placeholder credentials.

Do not print secrets, invent credentials, overwrite DATABASE_URL, or migrate an uncertain database.

Use the real isolated PostgreSQL test runner for implementation verification.

Clearly report which real-application database steps remain blocked.

## 10. Canary Hill Demonstration Acceptance Case

Preserve the existing fictional ten-applicant demo scenario and use it as a regression/acceptance model, not hardcoded business logic.

Required lifecycle:

1. Ten separate applications.
2. Organizer reviews ten applications.
3. Ten offers are issued where permitted.
4. Nine participants accept.
5. The tenth offer remains pending.
6. The tenth participant explicitly accepts.
7. Authoritative accepted-commitment count changes from nine to ten.
8. Organizer and participant views update consistently.
9. Public-safe insights follow existing privacy thresholds.

Do not create fictional cleanup completion, attendance, payment receipts or delivered resources.

Also test at least one non-cleanup event to prove that the backend is generic.

## 11. Verification Requirements

Add meaningful integration tests for:

- Application submission, revisions and authorization.
- Multiple selected work items.
- Partial organizer approval.
- Clarification requests.
- Offer acceptance/decline/withdrawal.
- Changed offer terms and renewed consent.
- Duplicate acceptance and idempotency.
- Concurrent assignment/capacity conflicts.
- Scheduling conflicts.
- Plan version changes after offers.
- AI recommendations that are stale, malformed or unavailable.
- Resource offers and organizer review.
- Promised versus verified received stock.
- Resource reservation concurrency.
- Sponsor permissions and private fields.
- My Events and role coverage consistency.
- Cross-event data isolation.
- Audit and source-linked memory behavior.
- No false governance approval or fabricated outcomes.
- Canary Hill ten-participant regression.
- At least one different event category.

Run the full backend suite against real isolated PostgreSQL.

Run the full frontend test suite, all existing demo tests, TypeScript checking and production build.

Record exact pass/fail/skip totals and document any incomplete verification.

Do not claim a visual browser walkthrough unless actually performed.

## 12. Final Deliverables

Provide a Group 3 implementation report containing:

1. Exact scope completed.
2. Existing code reused.
3. New migration and tables.
4. Exact implemented endpoints.
5. Application and consent state machines.
6. AI advisory interfaces and actual execution status.
7. Resource/sponsor accounting behavior.
8. My Events/organizer/frontend integration status.
9. Event Memory and governance integration.
10. Actual backend/frontend/demo test results.
11. Unresolved blockers.
12. Exact files created or modified.
13. Remaining Group 4 dependencies.
14. Features incomplete or explicitly deferred.

Save a complete file manifest and verification evidence under an appropriate `outputs/backend-group3/` directory.

**Stop after Group 3. Do not start Group 4 automatically. Do not make live Meta Muse Spark or Modal inference calls without explicit authorization.**