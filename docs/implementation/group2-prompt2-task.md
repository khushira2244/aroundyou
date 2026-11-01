# CODEX — AroundYou Backend Group 2, Prompt 2

## Objective

Audit the actual Group 2 implementation, close any remaining bounded functional gaps in AI-assisted Event Context Building and Governance, and verify that both are ready for a later Meta Muse Spark integration.

This is a continuation of Group 2, NOT Group 3.

Group 1 and Group 2 were previously reported implemented. Group 2 verification reported 75 PostgreSQL backend tests, 63 frontend tests, 146 demo tests, and passing TypeScript/production build.

**Do not assume everything in the earlier implementation summary is complete. Inspect actual source code and tests first.**

Read:
- Approved backend contract and API catalogue
- Approved backend database model
- Group 1 implementation report
- Group 2 implementation report
- Existing React event creation and governance screens
- Existing AroundYouService contracts and demo behavior

Preserve all previously working code, screens, fixtures and invariants.

## 1. Audit AI-Assisted Event Context Building

Verify the actual flow:

Organizer's original explanation (text or reviewed transcript)
→ context interpretation request
→ structured proposal
→ clarification questions where needed
→ organizer answers/corrections
→ revised interpretation
→ explicit organizer confirmation
→ durable, versioned confirmed context.

Requirements:

- Preserve the complete original organizer explanation.
- Distinguish organizer-provided facts, AI interpretations, assumptions, unknowns and clarifications.
- Support multiple clarification rounds without overwriting originals.
- Questions should reflect the actual event type, scale, location, timing, resources and activities.
- Never invent answers to missing questions.
- Allow the organizer to correct, reject or manually complete context.
- Persist the exact accepted revision.
- Prevent stale AI proposals from replacing newer organizer input.
- Use confirmed context as an authoritative planning input.
- Ensure context revisions invalidate affected derived proposals and Event Memory eligibility appropriately.
- Keep all workflows generic across community event types.

Inspect whether the existing frontend can access and display the complete workflow through the opt-in HTTP adapter.

If anything is incomplete, implement and test the missing bounded components.

Do not use fake AI outputs in production mode. A deterministic fixture/fake model is allowed strictly within tests or explicitly labeled demo mode.

## 2. Audit AI-Assisted Governance

Governance must adapt to the event's circumstances, not rely on one static checklist.

Its assessment inputs should include, where available:

- Event category and activities
- Expected scale and attendance
- Geographic location and venue
- Event date, time and duration
- Public/private venue characteristics
- Equipment, transport and resource requirements
- Relevant participant roles and risk-sensitive tasks
- Event revisions that affect governance applicability

The assessment should produce structured advisory recommendations:

- What may require permission, review, documentation or preparation
- Why the recommendation is applicable
- Supporting event facts
- Applicable rule/evidence source, if actually verified
- Uncertainty and missing information
- Suggested next action
- Whether a governance ticket should be created

Never invent local regulations or claim legal authorization without verified evidence.

Differentiate:
- Verified requirement
- Conditional recommendation
- AI advisory suggestion
- Unknown / needs clarification
- Not applicable

## 3. Strict Governance Boundary — Tickets Only

AroundYou does NOT have an external administrator or government authority account for this hackathon implementation.

The permitted governance workflow ends at:

AI assessment
→ organizer review
→ internal governance ticket creation
→ optional document references
→ ticket status and follow-up.

Support appropriate internal statuses such as open, in review, waiting for documents, and closed, using the approved existing contract where possible.

Do NOT implement:
- Government portal integration
- External ticket submission
- Automatic permission requests
- Government/municipal approval simulation
- Fake uploaded certificates
- Fake approval or legal compliance status
- Fictional outgoing emails or notifications

A closed internal ticket must not imply that an external authority has approved the event.

Governance reassessment must be possible when event type, location, dates, scale or activities materially change.

Previously generated recommendations must not silently remain current when their underlying event facts change.

## 4. Meta Muse Spark Integration Readiness

Inspect the existing planning provider interface and context builder.

Prepare, or repair as needed, the typed provider boundary for:

- Event context interpretation and clarification
- Governance advisory analysis
- Stage planning proposals
- Work-design assistance

Verify request/response validation, source provenance, version binding, error states, timeouts and safe fallback behavior.

The provider must not directly mutate authoritative event data.

**Do not deploy or invoke Muse Spark in this prompt.**

Do not make live Meta API calls, conduct provider smoke tests, or consume AI credits.

If a real provider adapter is not implemented, report that clearly instead of claiming AI is operational.

Do not assume Muse Spark credits or Modal compute credits are interchangeable.

## 5. Event Memory

Verify Group 2 and Group 1 source integration.

- Preserve original context and accepted decisions.
- Persist source-linked derived memory candidates through the existing infrastructure.
- Prevent stale or retracted memory from influencing new assessments.
- Keep historical memory separate from current verified facts.
- Do not convert an AI recommendation or a governance ticket into verified external approval.
- Do not enable cross-event sharing without the approved authorization and sanitization workflow.

No live Modal inference.

## 6. Database and HTTP Integration

The previous report states that the configured application DATABASE_URL contains placeholder credentials.

Do not treat the isolated PostgreSQL test database as the running application database.

Inspect configuration safely without printing secrets.

Do not invent credentials, overwrite DATABASE_URL, reset databases or apply migrations to an uncertain target.

Report the exact configuration keys that the developer needs to supply, without revealing existing secrets.

Where possible, continue implementation and verification using isolated real PostgreSQL.

Check the opt-in frontend HTTP adapter, especially context clarification, governance assessment and ticket persistence.

Preserve demo mode separately. Never silently substitute demo responses for failed real HTTP requests.

## 7. Tests

Add or update tests for:

- Multiple context clarification rounds
- Organizer correction and final confirmation
- Context update during a pending AI proposal
- Governance varying by event type, scale, location and time
- Missing or uncertain legal information
- Ticket creation, edits and closure
- External approval never being inferred from internal ticket status
- Governance assessment becoming stale after event changes
- Authorization and private document references
- Idempotency and conflicting updates
- Source-linked Event Memory integrity
- Provider unavailable, malformed response and timeout behavior
- Group 1 and Group 2 regression tests
- Existing frontend tests and all 146 demo tests

Run TypeScript checking and production build if frontend code is modified.

Use actual PostgreSQL for integration tests.

## 8. Required Final Implementation Report

After completing the audit and permitted fixes, provide:

1. What was already implemented in Group 2 before this prompt.
2. What was incomplete or incorrect.
3. What you changed in this prompt.
4. Exact files created/modified.
5. Exact working context-interpretation and clarification APIs.
6. Exact working governance and ticket APIs.
7. Database tables and migration changes, if any.
8. Frontend HTTP integration status.
9. Actual model execution status versus interfaces/fakes.
10. PostgreSQL, frontend and demo test results.
11. Database configuration blockers.
12. Remaining work before live Muse Spark integration.
13. Remaining Group 2 gaps, if any.

Do not claim a feature was tested unless it was actually exercised.

**Stop after Group 2 completion and verification. Do not start Group 3. Do not use live Muse Spark or Modal inference without explicit authorization.**