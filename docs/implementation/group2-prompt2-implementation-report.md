# AroundYou Group 2, Prompt 2 — audit and implementation report

Date: 1 November 2026. Scope: Group 2 context building, advisory governance and integration readiness. No Group 3 work, deployment, live Meta/Muse Spark call or Modal inference was performed.

## 1. What already existed

Inspected the approved architecture, API catalogue, minimum data model, Group 1/2 implementation reports, actual FastAPI models/services/routes/tests, React creation/governance screens, AroundYouService/HTTP adapter and demo service behavior. The previous 75-backend/63-frontend/146-demo results were treated as historical evidence, not assumed current verification.

Group 2 already had original context revisions, a mutable reviewed interpretation, asynchronous typed AI proposal/run boundaries, source-version checks, manual planning, immutable plan/publication records, advisory tickets, private document metadata and reminder preferences. The HTTP adapter preserved the demo boundary. No live Muse Spark transport existed.

## 2. Gaps found

- Exact accepted interpretations and structured clarification rounds were not captured in immutable context content. The UI appended clarification text to the original explanation instead of separately recording answers.
- Provider context omitted the structured event brief and organizer-confirmed interpretation. Governance lacked applicability/provenance/uncertainty fields and checked staleness too narrowly.
- The governance HTTP UI generated a pending proposal but had no assessment review controls. Tickets had no editable internal follow-up lifecycle; the document checklist assumed cleanup work.
- Provider timeouts were only a request hint. Memory was checked around inference, but not consistently when a human later accepted a proposal or viewed previously reviewed governance.
- Pending context proposals could not be recovered in the creation screen after reload.

## 3. Changes made

Context revisions now carry immutable snapshots containing the organizer brief, structured question/answer rounds and exact confirmed interpretation. Complete original explanation text remains separate and unchanged; corrections append revisions. New rounds and material brief edits invalidate derived confirmations and old context memory eligibility. Acknowledgement-only form edits retain the confirmed meaning. Assumptions have a separate field from reported facts, interpreted scope/instructions, unknowns and questions. Earlier snapshots and rejected proposals remain retained.

Provider requests now include organizer-reported category, scale, dates, location, activities/resources, confirmed meaning, clarification history, confirmed plan and separately labeled unconfirmed planning/reported setup where available. Emergency contacts are omitted from setup input. Historical memory remains separate and cited. Per-workflow instructions require relevant questions, explicit unknowns and no invented local rules or authority.

Governance proposals carry classification, rationale, supporting event facts, uncertainty, next action and an internal-ticket suggestion. Supporting facts must occur in the supplied event payload. Conditional recommendation, AI advisory suggestion, unknown/needs-clarification and not-applicable are supported. Verified external requirements and rule citations are deliberately rejected until a trusted evidence-verification integration exists; a model-supplied URL is not verification. Material-input fingerprints prevent old advice staying current after brief, plan/work or relevant setup changes.

Human acceptance now rechecks memory eligibility for context, governance and model-generated planning proposals. Previously accepted governance is shown as stale if cited memory is retracted or loses eligibility. Source changes and conflicting versions still fail closed. A bounded worker deadline records provider_timeout/retry without persisting late output. The daemon doing the call has no database session or mutation tools. A real transport must also enforce network timeout/cancellation; a hung third-party call cannot be forcibly cancelled by this Python boundary.

Tickets support open, in_review, waiting_for_documents and closed, with bounded append-only application history of follow-up notes and audit records. Every state explicitly retains permission_status=not_verified and external_submission=false. Closing/reopening is internal housekeeping. There are no authority accounts, government requests, certificates, outgoing messages or simulated legal approvals.

## 4. Exact files

See the absolute [created/modified file manifest](../../outputs/backend-group2-prompt2/files-changed.txt). It includes source, migration, tests, README, this report, saved prompt/checkpoint and generated verification evidence. No backend/.env values, demo source/fixtures, CSS or assets were changed in this prompt. Reviewed demo source hashes remain identical.

## 5. Context APIs actually implemented

All writes require authenticated event permission, private-source access, Idempotency-Key and the current event If-Match version. Responses retain data/meta envelopes. The exact installed schemas are in [OpenAPI](../../outputs/backend-group2-prompt2/openapi.json).

| Method/path (prefix /v1/events/{event_id}) | Contract and effect |
|---|---|
| GET /creation | Current brief/context, immutable input/snapshot history, clarification rounds, confirmed interpretation and pending/stale interpretation proposals. Private owner projection. |
| POST /context-revisions | {text, source: written or reviewed_transcript}; preserve original input and append a source revision. |
| POST /context-clarifications | {context_version, proposal_id?, answers:[{question,answer}]}; append a bounded round without overwriting the explanation. Optional proposal linkage validates the current proposal/questions. Maximum 20 rounds. |
| PATCH /context-details | Complete CreationForm; revise a created event's material brief, rebind context and invalidate derived confirmations. Earlier published snapshot remains intact. |
| POST /context-interpretations | {context_version, interpretation}; manually confirm exact validated meaning when AI is unavailable. Appends an immutable context snapshot and review decision. |
| POST /context-proposals | {message?}; 202 durable receipt only with an explicitly injected provider; otherwise 503. No fabricated AI fallback. |
| GET /context-proposals/{proposal_id} | Exact event-bound proposal metadata/digest for review. |
| POST /context-proposals/{proposal_id}/review | {decision:accept/reject, reviewed_digest, corrected_interpretation?}; current-version acceptance, with memory revalidation and original retention. |

GET /v1/ai-runs/{run_id} provides authorized run status. Stage/work proposal routes continue using the same provider boundary and deterministic review services. Neither enqueue nor model completion confirms authoritative context or a plan automatically.

## 6. Governance APIs actually implemented

Same event authorization/version/idempotency rules apply to writes.

| Method/path (same event prefix) | Contract and effect |
|---|---|
| POST /governance/assessments | {message?}; durable pending advisory run with current facts and cited eligible memory. Unconfigured provider returns 503. |
| GET /governance | Current reviewed items, pending/stale proposals, internal ticket, document references and preferences. Private event scope. |
| POST /governance/proposals/{proposal_id}/review | {decision, reviewed_digest}; human advisory review, never legal approval or plan mutation. |
| POST /governance/tickets | {}; idempotent internal ticket creation. |
| PATCH /governance/tickets/{ticket_id} | {status:open/in_review/waiting_for_documents/closed, note}; versioned internal follow-up/history. |
| POST /governance/tickets/{ticket_id}/documents | {name,document_type,document_reference?,size?,mime?}; private reference/metadata only, not byte upload or verified evidence. |
| PATCH /governance/tickets/{ticket_id}/reminders | {email_updates,remind_documents}; preferences only, no sender or notification claim. |

## 7. Database and memory

Additive migration 0003_context_snapshots adds JSONB snapshot to existing event_context_revisions. Existing immutability triggers protect it; hashes include new snapshot content when present. There are still 21 tables. Legacy rows receive empty snapshots: missing historical accepted content is not invented or backfilled. Upgrade/downgrade and metadata matching run on isolated databases; previous rows remain preserved.

Context snapshot sources reuse Group 1 outbox/extraction infrastructure. Full originals and exact accepted content remain in immutable source records; bounded derived excerpts retain source IDs/revisions/digests. Tests exercise source eligibility, current confirmed input, original immutability and retracted memory. Governance recommendations/ticket closure are not promoted into verified outcome memory. Ticket records themselves do not add a new memory source kind. Cross-event sharing remains disabled.

## 8. Frontend HTTP integration

The existing context screen supports question answers/history, corrections, explicit acceptance/rejection, manual completion and refresh/reload recovery of pending interpretations. The existing governance screen displays/reviews pending advice, uses event-specific supporting items and edits ticket status/follow-up. No new dashboard, screen redesign or mixed demo/server event state was added. AroundYouService remains the boundary. Demo behavior remains separate.

HTTP adapter calls persist clarification/manual-review/ticket commands. Post-creation full brief revision is API-supported; an expanded dedicated editor was not added. Browser-driven real-server end-to-end flow and screenshots were not performed. Component/transport tests use explicit test services, while backend APIs are exercised against real PostgreSQL.

## 9. Actual model execution

Zero live Meta/Muse Spark calls. Zero Modal calls. No credits consumed by this work. The provider-neutral typed port, source context builder, strict proposal validation, durable execution/retry function and human-review boundaries are implemented. Tests use explicitly non-live adapters only. There is no deployed Muse Spark adapter or live AI worker daemon, and credentials alone do not make AI operational. Meta API credits and Modal compute are separate and were not used.

## 10. Verification

- Final isolated PostgreSQL run: **89 passed, 0 failed, 0 skipped** on PostgreSQL 16.11, runner exit 0. Includes all original Group 1/2 tests and 14 new parameterized context/governance cases.
- Final full frontend run: **66 passed, 0 failed**, raw JSON saved. New component tests exercise manual context completion and governance review; transport tests exercise clarification/manual review and ticket edits.
- Existing demo suite: **146 passed, 0 failed, 0 skipped**, including ten-participant and blocker-recovery scenarios.
- TypeScript checking and production build passed (`npm run build`: tsc -b and Vite).
- Python compileall passed.

Exact commands/results and earlier failures are recorded in [verification.json](../../outputs/backend-group2-prompt2/verification.json). Early frontend runs had timeouts under concurrent load, then one intermittent existing participant-intelligence assertion failure. That test passed separately and the final full run passed unchanged. The initial backend command passed its tests but failed test-cluster cleanup; slow crash recovery then caused two startup failures. Longer test-only startup/shutdown grace resolved those runner failures; final runs exited successfully. An initial focused frontend invocation used the wrong cwd and was corrected. These failed attempts are not represented as passes.

Non-failing warnings remain: upstream Starlette/httpx TestClient deprecation and the Vite large bundle warning. Screenshot comparison and real live-provider behavior remain unverified.

## 11. Configuration blocker

Safe inspection found SESSION_SECRET valid and DATABASE_URL loopback but still containing placeholder credentials. No environment value was printed or changed in this prompt. Supply **DATABASE_URL** for the intended existing/created local development database (real username/password/database), then explicitly apply Alembic there. No uncertain/configured application database was connected, reset or migrated. Isolated PostgreSQL is test infrastructure, not the running application DB.

For later live integration, META_API_KEY and META_MODEL_ID must be configured alongside an actual reviewed transport adapter/worker. Existing values were neither exposed nor used. Modal tokens/endpoint are not needed for this prompt.

## 12. Before live Muse Spark integration

Implement and review the real provider transport against official documentation, including actual model/schema capabilities, authentication, transport timeouts/cancellation, error mapping, budgets and rate limits. Connect an explicit durable worker process, configure the intended application database and development/production identity flow, then verify the real browser HTTP path. Any future live test needs separate authorization; this task did not grant it. Verified regulatory retrieval requires a genuine source verifier and policy before enabling verified_requirement/rule_sources.

## 13. Remaining Group 2 limits and stop

The bounded context/governance corrections are implemented and tested; real model quality, real provider execution, verified legal evidence, file byte storage, reminder delivery and live browser integration are not claimed complete. Existing production authentication, scheduled publication and advanced editing limits from the earlier Group 2 report remain. Manual authoring and internal ticket workflows work without a model. No operational participation, sponsorship fulfillment, execution evidence or blocker recovery commands from Group 3-5 were added. Stop after Group 2.
