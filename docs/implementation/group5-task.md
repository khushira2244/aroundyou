# CODEX — AroundYou Backend Group 5
## Intelligent Blocker Recovery, Selective Replanning, Event Memory and Dynamic Participant Insights

### Objective

Implement the final bounded backend group of AroundYou, building on the real Group 1–4 implementation.

This is an implementation task, not just an architecture audit.

Group 4's reported final baseline:
- 128 backend tests passed against isolated PostgreSQL 16.11.
- 72 frontend tests passed.
- 146 existing demo tests passed.
- TypeScript checks and production build passed.
- Migration 0005 completed, bringing the system to 43 application tables.
- Execution, evidence, human verification, attendance, resource usage, coordination, issues and Event Memory lineage were implemented.

Read the actual repository, approved architecture, API catalogue and database model, all prior implementation reports, Group 4 source code, existing recovery frontend/contracts, existing Participant Insights modal/settings/application screens and demo scenarios before editing.

Use the existing FastAPI modular monolith, PostgreSQL, SQLAlchemy/UoW, versioning, human approvals, outbox/jobs, authenticated access and source-linked memory.

Do not rebuild working Group 1–4 features.

**Group 5 has two explicit workstreams:**
1. Intelligent Blocker Recovery and Selective Replanning.
2. Organizer-configured Dynamic Participant Insights.

Complete both while preserving existing frontend design and demo fixtures.

---

# PART A — Intelligent Blocker Recovery

## A1. Consume genuine Group 4 operational state

Use the existing authoritative records:

- Published plan versions, stages, work and dependencies.
- Current accepted assignment terms and participant consent.
- Verified work progress and incomplete work.
- Source-linked reports and evidence.
- Reported issues and independently reviewed blocking conditions.
- Resource reservations, receipts, consumption, equipment custody and shortages.
- Governance advice/tickets, clearly distinguished from verified rules.
- Relevant decisions and operational source history.

Do not construct a recovery case solely from a fictional UI state.

An issue marked acknowledged or internally closed is not necessarily cleared.

An AI-detected possible issue is a proposal for investigation, not automatically a verified blocker.

## A2. Deterministic affected-dependency analysis

Implement a deterministic graph-based impact engine.

Given one or more confirmed blockers:

1. Identify directly affected work.
2. Traverse downstream work and stage dependencies.
3. Include relevant resource, assignment, timing and capacity constraints.
4. Separate affected work from unaffected work.
5. Identify already completed/verified work that must remain preserved.
6. Explain what is blocked, why and by which evidence/source.
7. Detect stale plan versions, invalid references and dependency cycles.
8. Return an auditable affected-scope manifest.

Classify work where appropriate:
- Directly blocked.
- Downstream affected.
- At risk or conditionally affected.
- Unaffected.
- Already verified complete.

Do not treat every downstream item as automatically cancelled.

Do not modify completed work or unrelated branches merely because a blocker was reported.

The deterministic impact calculation must work without AI.

## A3. Event Memory retrieval for recovery

Use the existing Event Memory retrieval service.

Retrieve relevant historical knowledge using:

- Event type and purpose.
- Work/dependency pattern.
- Resource limitations.
- Location/time/scale conditions when supported.
- Prior blocker types.
- Prior attempted recoveries.
- Source-supported successful and failed outcomes.
- Applicable scope and source authorization.

Preserve the distinction between:

**Current event facts** and **historical memory-derived lessons**.

A historical success does not prove that a proposed alternative is currently available.

Retrieve failed attempts and their conditions as well as successful patterns.

Source citations, applicability, memory versions, privacy and current eligibility must be preserved.

Cross-event private memory sharing remains disabled.

Do not enable vector search or a second database unless necessary and expressly justified.

Do not make Modal inference calls in this group.

## A4. Meta Muse Spark-ready recovery reasoning

Extend the existing provider-neutral AI architecture to support recovery reasoning.

Supply the model with:

- Confirmed current blocker and evidence.
- Original and confirmed event context.
- Current published plan and affected-scope manifest.
- Current participant and resource constraints.
- Relevant governance limitations.
- Applicable source-linked Event Memory.
- Organizer-specified preferences and constraints.

Expected typed proposal output:

- Explanation of the blocker.
- Affected work and dependencies.
- Possible alternative strategies.
- Each alternative's assumptions.
- Required people, skills and resources.
- Schedule and work changes.
- Advantages and disadvantages.
- Risks and uncertainties.
- Source citations.
- Conditions that must be satisfied before activation.
- Explicit unknowns and questions for the organizer.

Examples of alternatives may include:
- Rescheduling dependent work.
- Reassigning eligible work to available participants.
- Splitting work when feasible.
- Requesting missing resources.
- Changing sequence without breaking dependencies.
- Postponing a blocked stage.
- Continuing unaffected branches.
- Placing the affected work on hold when no safe alternative exists.

AI must never fabricate a vehicle, resource, permission, accepted assignment or completed work.

Use strict schemas, bounded execution, retries, timeouts, source version binding and human review.

Do not let the provider call tools that directly mutate authoritative operational tables.

**No live Meta Muse Spark or Modal inference in Group 5.**

Tests may use clearly labeled non-live adapters.

## A5. Deterministic alternative validation

Validate every proposed recovery option independently of the AI.

Check:

- Dependency validity and acyclic structure.
- Actual resource quantities and reservations.
- Exact units and resource compatibility.
- Participant availability and schedule conflicts.
- Required capabilities and eligibility.
- Existing accepted assignment commitments.
- Work capacity.
- Time and location constraints.
- Governance conditions where verified.
- Current plan/source versions.
- Impact on previously verified work.
- Conflicting or duplicate recovery activations.

Return structured validation results:

- Feasible under current verified constraints.
- Conditionally feasible with unresolved requirements.
- Invalid or unsupported.
- Requires human clarification.
- Requires participant reconfirmation.

Do not convert an unknown condition into a verified positive condition.

A conditionally feasible alternative must not silently activate as though all conditions were satisfied.

## A6. Human recovery review and decision

Implement the existing recovery screens' workflow through real persistence.

Organizer can:

- Open a blocker investigation.
- View affected work and evidence.
- Review alternatives and trade-offs.
- Request clarification.
- Correct a proposal.
- Reject an option.
- Select an option.
- Place affected work on hold.
- Record a decision and rationale.
- Retry after changed circumstances.

Review must bind the exact proposal digest and current plan/source versions.

Store proposed, rejected, conditionally approved and approved decisions without equating approval with activation.

Organizer approval does not automatically override participant consent or resource constraints.

## A7. Exact participant reconfirmation

When a selected recovery alternative materially changes any accepted assignment:

1. Determine the affected participants.
2. Generate exact revised role/work/schedule/location/condition terms.
3. Preserve the existing accepted terms and history.
4. Require the participant to explicitly accept or decline changed terms.
5. Track outstanding reconfirmations.
6. Avoid counting pending reconfirmations as accepted revised commitments.
7. Handle declines, withdrawals and expired offers safely.
8. Ensure old authorization is not extended to materially changed work.

Unchanged, unaffected assignments should remain valid.

A participant who declines revised terms must not be silently reassigned.

## A8. Atomic activation or safe deferral

Implement a version-safe recovery activation boundary.

Before activation:

- Recheck issue and dependency state.
- Recheck affected scope.
- Recheck source and memory eligibility.
- Recheck resource availability and reservations.
- Recheck participant reconfirmations.
- Recheck deterministic feasibility.
- Recheck the current authoritative plan version.

If all required conditions are satisfied, atomically activate a new plan version using the existing plan/versioning architecture.

Preserve previous plan versions and all completed historical work.

If approval or reconfirmation is incomplete, keep the recovery pending/held.

If a dependency becomes invalid during review, reject or defer activation with a clear reason.

No partial authoritative plan activation after a failed transaction.

Ensure retries are idempotent and concurrent recovery attempts cannot overwrite one another.

## A9. Canary Hill recovery acceptance scenario

Use the existing fictional Canary Hill scenario as a test model, not a hardcoded rule.

Scenario:

- Municipal pickup vehicle for work W16 is unavailable.
- Dependent work W17 and relevant downstream stage activities are affected.
- Unaffected and verified work remain preserved.
- The recovery engine computes the actual dependency impact.
- Event Memory retrieval returns only authorized and applicable source-linked knowledge.
- AI may propose alternatives through a non-live test adapter.
- No alternative vehicle or permit is fabricated.
- Organizer reviews alternatives.
- Changed assignments require explicit participant reconfirmation.
- Missing resources or consent prevent activation.
- A valid, fully confirmed alternative may activate a new plan version.
- Failed or deferred alternatives remain recorded for later investigation.

Also run a separate non-cleanup scenario, such as a workshop with an unavailable venue or equipment dependency.

## A10. Recovery outcomes and Event Memory

Persist source-linked recovery attempts and decisions.

Distinguish:

- Proposed alternative.
- Organizer-approved alternative.
- Attempted recovery.
- Activated revised plan.
- Verified operational outcome.
- Failed or inconclusive outcome.

Do not label an activated plan as a successful real-world recovery until later evidence actually supports that conclusion.

Preserve failed alternatives and reasons when supported by genuine decision/evidence records.

Support correction, supersession and eligibility invalidation.

No fabricated generalizable lessons or cross-event memory sharing.

---

# PART B — Dynamic Participant Insights

This feature was explicitly approved for Group 5.

The existing React Participant Insights UI is ALREADY IMPLEMENTED by the user and Codex.

It contains six tabs:

- Overview
- Age
- Neighbourhood
- Experience
- Interests
- Tags

**Do not recreate or redesign this modal.**

## B1. Organizer-configured participant fields

Inspect the existing Event Profile Settings and participant insight controls.

The organizer must be able to configure which participant information is requested for a particular event.

Supported dimensions:

- Age or age range.
- Neighbourhood.
- Experience.
- Interests.
- Tags.
- Additional bounded custom questions compatible with the existing product contracts.

Each field configuration should support, where appropriate:

- Stable question ID.
- Label and description.
- Response type.
- Defined choices/options.
- Required or optional status.
- Privacy/visibility setting.
- Whether it contributes to aggregate insights.
- Configuration version.
- Enable/disable status.

Prefer bounded structured options for aggregate Tags instead of unrestricted text categories.

Do not collect unnecessary personal details.

Age-range collection should be preferred over precise birth dates when exact dates are not needed.

## B2. Dynamic participant Join Event form

When a participant opens an event application:

1. Load the current event-specific field configuration.
2. Render enabled questions in the existing application flow.
3. Preserve required fields and validation.
4. Allow optional or privacy-sensitive questions to be skipped appropriately.
5. Save answers against stable question IDs.
6. Store the configuration version used at submission.
7. Preserve original submitted answers and subsequent revisions.
8. Do not use stale or disabled questions for new applications.
9. Do not fabricate answers for existing users.

A custom organizer-configured Tag or question must genuinely appear in the participant's form.

Do not modify unrelated Join Event layouts.

## B3. Separate consent for aggregate insights

Provide clear participant consent for use of eligible responses in aggregate participant insights.

Consent should be specific and revocable.

Participation/assignment acceptance must not implicitly grant demographic insight consent.

Withdrawal of insight consent must remove the response from future aggregate projections.

Do not expose individual demographic answers in public or other participants' views.

Ensure organizer access to raw responses follows the approved private-field policy; never assume public aggregate consent authorizes unrestricted individual disclosure.

## B4. PostgreSQL aggregation and privacy

Use real stored application answers and authoritative accepted assignments.

Do not count mere registrations as accepted participants.

Maintain separate overview metrics:

- Applications submitted.
- Human-approved applicants.
- Accepted participants.

These may overlap and must not be added together.

For demographic and custom-field aggregates:

- Include only eligible, consented accepted participants.
- Require at least five eligible participants in the aggregate population.
- Suppress any displayed bucket with fewer than five eligible participants.
- Check the threshold on combined filters, not only individual dimensions.
- Prevent simple complementary or differencing queries from disclosing small categories.
- Apply the same privacy rules to tabs, comparisons, filters and exports if exports exist.
- Enforce access and visibility settings on the server.
- Avoid returning raw private rows or suppressed counts in API metadata.

If a particular safe filtered breakdown cannot be produced, return a suppressed/unavailable state instead of leaking numbers.

Ensure that revocation or account/assignment changes update eligibility.

## B5. Organizer settings and configuration changes

Organizer can update permitted field configuration.

Validate:

- Choice changes.
- Removed or disabled questions.
- Stable identifiers.
- Existing response compatibility.
- Duplicate labels/IDs.
- Invalid data types.
- Organizer permission.
- Current expected configuration version.

Old responses must retain their original meaning and configuration lineage.

Do not silently reinterpret an old answer after renaming options or changing choices.

New submissions must use the current configuration.

Aggregation must count only explicitly compatible responses.

If the existing settings UI cannot fully support the agreed controls, make the smallest necessary UI and HTTP-adapter changes without redesign.

## B6. Existing Participant Insights modal

Wire the existing UI to real HTTP data.

Verify:

- Overview totals.
- Age breakdown.
- Neighbourhood breakdown.
- Experience breakdown.
- Interests breakdown.
- Custom Tags breakdown.
- Organizer-enabled dimensions only.
- Consent and privacy suppression.
- Correct empty states.
- No cross-event leakage.
- Correct behavior after assignment acceptance, withdrawal and consent revocation.

Do not substitute synthetic demo totals in HTTP mode.

Preserve the existing fixture-based demonstration separately.

## B7. Dynamic Insights end-to-end tests

Test at minimum:

1. Organizer enables Age and Neighbourhood.
2. The Join Event form shows exactly those configured fields.
3. Organizer adds a custom Tag with defined choices.
4. The Tag appears for the participant.
5. Participant saves and submits answers.
6. A separate consent decision is recorded.
7. Organizer approves and issues an exact assignment.
8. Participant explicitly accepts.
9. The Insights API updates from persisted data.
10. Small groups remain suppressed.
11. At the threshold, eligible buckets become visible.
12. Combined filters do not reveal suppressed categories.
13. Consent revocation removes an eligible contribution.
14. Disabled/changed questions preserve historical answer meaning.
15. Participant-only viewers cannot access raw private answers.
16. A second event cannot read the first event's insights.
17. Existing six-tab UI and demo behavior remain unchanged.

---

# PART C — Shared Engineering Requirements

## C1. Architecture and migrations

Continue using the existing modular monolith.

Keep recovery logic in its appropriate recovery/intelligence domain.

Keep dynamic insight configuration, answers and aggregation in the participation/insights domain, NOT in recovery tables.

Add only necessary migration(s) after 0005.

Preserve existing PostgreSQL integrity constraints, immutable originals, audit history, Unit of Work and source references.

Do not hardcode Canary Hill or particular event categories.

Do not use an in-memory database as a substitute for real PostgreSQL verification.

## C2. Frontend compatibility

Extend the existing AroundYouService and opt-in HTTP adapter.

Connect existing Group 5 recovery screens and the already-designed Participant Insights components.

Preserve:
- Existing routes and navigation.
- Existing Event Profile Settings layout.
- Existing Join Event screens.
- Existing Participant Insights modal.
- Organizer Dashboard.
- Participant Workspace.
- Demo mode and all synthetic fixtures.

Do not create duplicate screens or a second dashboard.

Do not silently fall back to synthetic demo data on HTTP errors.

The following changes are reserved for tomorrow's separate frontend integration scope and must NOT be mixed into Group 5:

- Public AroundYou landing-page redesign.
- Organizer-only My Events with All, Drafts, Organizing and Completed filters.
- General end-to-end frontend wiring and visual polish.

## C3. AI integration and credit controls

Reuse the existing provider-neutral typed ports, context builder, source eligibility, bounded jobs/retries/timeouts and human review.

Prepare the implementation for future Meta Muse Spark and Modal integration.

**Do not make any live Muse Spark, Meta or Modal inference calls.**

Do not deploy a GPU model or start a paid worker.

Do not assume Meta API credits are included in Modal's monthly compute allowance.

Maintain explicit non-live adapter behavior for tests.

When no production model adapter is present, real-model features must say unavailable, not fabricate model responses.

## C4. Application database and private evidence configuration

Previous reports show:

- The configured application DATABASE_URL still contains placeholder credentials.
- Group 4 private evidence storage requires EVIDENCE_DIRECTORY.
- Tests have used isolated PostgreSQL and private test storage.

Do not overwrite DATABASE_URL, print secrets, reset application databases or migrate an uncertain target.

Do not modify the current Modal CLI profile or Meta credentials.

Use isolated real PostgreSQL for tests.

Report the exact developer configuration still needed.

## C5. Testing and regression

Add meaningful tests covering:

- Affected-graph correctness and cycle handling.
- Verified versus reported blocker distinctions.
- Alternative proposal validation and rejected options.
- Resource availability and plan conflict.
- Human review and proposal version checks.
- Participant reconfirmation.
- Atomic activation and rollback.
- Concurrent recovery attempts and idempotency.
- Preservation of unaffected work and completed history.
- Recovery source lineage and stale memory retraction.
- Non-cleanup event recovery.
- Dynamic organizer question settings.
- Application answers and consent.
- Every insights category and custom Tags.
- Combined-filter privacy attacks.
- Insight eligibility after assignment changes.
- Group 1–4 regression tests.
- Existing 146 demo tests.

Run:
- Full backend PostgreSQL test suite.
- Full frontend tests.
- TypeScript check.
- Production build.
- Python compileall.
- Dependency check.

Report actual results and do not claim unperformed browser or provider tests.

## C6. Required final report

Save:

`docs/implementation/group5-implementation-report.md`

And verification/manifests under:

`outputs/backend-group5/`

Include:

1. Implemented recovery domain and API contracts.
2. Affected dependency analysis and deterministic validation.
3. Pending, rejected, approved, deferred and activated recovery transitions.
4. Human approval and assignment reconfirmation behavior.
5. Atomic activation and plan-version preservation.
6. Event Memory lineage and actual retrieval behavior.
7. AI interfaces versus actual provider execution.
8. Dynamic insight configuration and application-answer storage.
9. Consent/privacy aggregation behavior, including combined filters.
10. Existing frontend recovery and insights integration status.
11. Exact migration, tables and files changed.
12. Backend/frontend/demo test totals.
13. Unverified runtime/browser behavior.
14. Remaining application database, evidence storage, identity and provider integration blockers.
15. Outstanding work for tomorrow's final frontend integration.
16. Explicitly deferred functionality.

## Final stop condition

Finish and verify Group 5 only.

Do not start tomorrow's landing page or organizer-only My Events work.

Do not silently implement production deployment or paid provider integration.

Do not invoke live models.

Do not fabricate recovery success, official approvals, participant consent, verified work or demographic data.

**STOP after Group 5 and provide the exact implementation report, file manifest and verification evidence.**