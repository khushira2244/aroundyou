# AroundYou Backend Group 3 implementation report

Reviewed/verified: November 1, 2026. Scope: saved `group3-task.md`. Group 4 was not started. No live Meta Muse Spark or Modal calls, deployment, push, configured application database migration, fixture replacement or frontend redesign.

## 1. Scope completed and completion assessment

Implemented the Group 3 core in the existing modular FastAPI monolith: persisted applications/revisions, human review and clarification, exact assignment offers and separate consent, shared participation projections, organization-scoped support, receipt/reservation accounting, and version-bound AI advisory. The generic PostgreSQL acceptance test creates ten independent applications/offers, accepts nine, then explicitly accepts the tenth. Public accepted count changes 9→10; small categories remain suppressed until eligible. A community education workflow also runs against PostgreSQL. The unchanged fictional demo scenarios remain separate from HTTP data.

Completion assessment: **core implemented and integration-tested; overall delivery remains partial for real application/browser deployment and the limitations in sections 11/14**. This is not a claim that every prior catalogue contract or every existing demo action has a backend implementation.

## 2. Existing code reused

Reused Group 1/2 identity verification, event grants, UoW/session transaction, structured errors, If-Match convention, actor-scoped idempotency, immutable planning/context/publication, audit/review decisions, durable job/outbox infrastructure, source resolver, memory eligibility/retraction checks and MuseSparkContextBuilder. AroundYouService remains the sole frontend boundary. No microservice, second database, second My Events page or additional dashboard was created.

## 3. Additive migration and tables

`0004_participation_support.py` follows 0003; 13 new tables, 34 application tables total:

| Tables | Purpose and integrity |
|---|---|
| applications, application_revisions | One event/account application, mutable current projection; immutable sequence/digest snapshots preserve original answers and subsequent states. |
| assignments, assignment_terms, assignment_consents | Current assignment projection; immutable plan-bound exact terms and unique participant decision per terms record. Replacing terms creates a new digest and requires renewed consent. |
| organizations, organization_memberships | Self-declared profile/version and explicit creating account membership. Registration never claims external verification. |
| support_offers, support_offer_revisions, support_fulfillments | Current pledge projection, immutable terms/state history, append-only delivery reports with unique event reference. Reports are unverified. |
| resource_transactions, resource_reservations | Append-only receipt/reversal ledger; unique delivery credit and reversal references; versioned reservation/release. |
| operational_sources | Immutable event/aggregate sequence, source digest and genuine operation summaries feeding private derived memory. |

Foreign keys/indexes/uniqueness and immutable-record triggers are in the frozen migration. Real PostgreSQL tests upgrade/downgrade/re-upgrade, compare SQLAlchemy metadata, preserve existing rows, and reject updates to immutable assignment terms. Application database was not touched.

## 4. Exact implemented endpoints

All paths below are authenticated and prefixed /v1. Public-safe event profile remains the existing Group 2 endpoint. Full installed request schemas, required headers and response contracts are saved in `outputs/backend-group3/openapi.json`. Runtime responses use the existing data/meta or structured error envelope. `If-Match` and `Idempotency-Key` are required for event mutations. Application review additionally binds the exact application revision; offers bind the current published plan; consent binds the exact terms digest. Organization profile changes use expected_version and idempotency.

- `GET /v1/participation-opportunities`
- `GET /v1/events/{event_id}/participation/me`
- `GET /v1/events/{event_id}/organizer/participants`
- `POST /v1/events/{event_id}/applications/draft`
- `POST /v1/events/{event_id}/applications/{application_id}/advance`
- `POST /v1/events/{event_id}/applications/{application_id}/submit`
- `POST /v1/events/{event_id}/applications/{application_id}/withdraw`
- `POST /v1/events/{event_id}/applications/{application_id}/reopen-review`
- `POST /v1/events/{event_id}/applications/{application_id}/begin-review`
- `POST /v1/events/{event_id}/applications/{application_id}/review`
- `POST /v1/events/{event_id}/applications/{application_id}/clarifications`
- `POST /v1/events/{event_id}/applications/{application_id}/clarifications/{clarification_id}/answer`
- `POST /v1/events/{event_id}/applications/{application_id}/capability-reviews`
- `POST /v1/events/{event_id}/applications/{application_id}/assignment-checks`
- `POST /v1/events/{event_id}/applications/{application_id}/assignment-offers`
- `POST /v1/events/{event_id}/assignments/{assignment_id}/decline`
- `POST /v1/events/{event_id}/assignments/{assignment_id}/accept`
- `POST /v1/events/{event_id}/assignments/{assignment_id}/withdraw`
- `GET /v1/me/sponsor-portal`
- `POST /v1/organizations/draft`
- `POST /v1/organizations/{organization_id}/registration/complete`
- `POST /v1/events/{event_id}/support-offers/draft`
- `POST /v1/events/{event_id}/sponsor-offers/{offer_id}/fulfillments`
- `POST /v1/events/{event_id}/sponsor-offers/{offer_id}/{action}`
- `GET /v1/events/{event_id}/organizer/sponsor-offers`
- `GET /v1/events/{event_id}/resources`
- `POST /v1/events/{event_id}/resource-receipts`
- `POST /v1/events/{event_id}/resource-receipts/{receipt_id}/corrections`
- `POST /v1/events/{event_id}/resource-reservations`
- `POST /v1/events/{event_id}/resource-reservations/{reservation_id}/release`
- `POST /v1/events/{event_id}/resource-assessments`
- `POST /v1/events/{event_id}/participation-assessments`
- `POST /v1/events/{event_id}/resource-proposals/{proposal_id}/review`
- `POST /v1/events/{event_id}/participation-proposals/{proposal_id}/review`
- `POST /v1/events/{event_id}/applications/{application_id}/information-revisions`
- `POST /v1/events/{event_id}/applications/{application_id}/alternatives`
- `POST /v1/events/{event_id}/applications/{application_id}/alternatives/{alternative_id}/response`
- `GET /v1/organizations/{organization_id}/sponsor-portal`
- `PATCH /v1/organizations/{organization_id}/registration`
- `POST /v1/organizations/{organization_id}/offers`
- `POST /v1/organizations/{organization_id}/offers/{offer_id}/withdraw`
- `POST /v1/organizations/{organization_id}/offers/{offer_id}/submit`
- `POST /v1/organizations/{organization_id}/offers/{offer_id}/fulfillment-reports`
- `GET /v1/events/{event_id}/organizer/dashboard`
- `POST /v1/events/{event_id}/resource-requests`

The dynamic sponsor-offer action endpoint allows only submit/accept/reject/withdraw. Unknown actions fail. Existing `/v1/me/events`, `/v1/events/{event_id}/profile` and `/v1/ai-runs/{run_id}` were extended rather than duplicated. The 45 new route registrations are listed separately in `group3-endpoints.json`; registration is not a claim that all 45 received individual endpoint tests.

## 5. Application and consent state machines

Private application_draft → submitted → pending_review → approved or rejected. Review can approve a subset of requested roles and retain rejected choices/history. Clarifications and participant information revisions append immutable snapshots, return to review and invalidate obsolete approvals/capability assessments. Withdrawn applications remain historical. Autosave cannot modify a submitted application. Submitted applicants can inspect only their own answers/offers; organizer views exclude other users' private drafts.

Offer → assignment_offered → assignment_accepted or assignment_declined; explicit withdrawal and expiry exclude commitments from accepted counts. A confirmed current-plan/context mismatch yields requires_reconfirmation. Offer replacement preserves old terms/consent, changes the digest and returns to offered. Organizer approval, AI proposal acceptance and an account record never imply participant consent. Accepted assignment withdrawal is recorded independently.

Exact offer content includes role, work IDs/revisions/scope, schedule/timezone, location, organizer instructions, evidence/resource requirements, material conditions/exclusions and expiry. Acceptance revalidates availability, matching published plan, role approval, known concurrent headcount, duplicate work, overlap and required human capability/limitations review. Event row locks serialize capacity/resource transitions; participant advisory locks serialize cross-event commitment checks. Anchored cross-event schedules compare UTC intervals; unknown anchors fail safely. Multiple role choices are supported; one offer can reference multiple work IDs within its explicit schedule. This is bounded deterministic conflict checking, not a complete resource-constrained scheduler.

## 6. AI advisory interfaces and execution status

ParticipationAdvice is a strict provider-neutral schema: applicant understanding, unknowns, clarification questions, role/work recommendations with cited supplied statements, trade-offs, coverage explanation and resource advice. Inputs include actual current event brief/confirmed meaning/published plan, applicant originals/availability/clarifications, current assignments, reviewed operational conditions, real resource quantities and eligible source-linked memory. Private other-event detail is not sent; a digest detects changed commitments.

Runs reuse the durable AI job/lease/retry/deadline and pending-proposal implementation. Unsupported IDs, extra mutation fields, invented supporting quotations, malformed output, provider unavailability, timeout and changed sources fail closed. Source/memory/version eligibility is rechecked at review. Human approval accepts advice only; it creates no assignment, consent, stock or legal authorization. UI labels distinguish non-live tests and actual inference.

Actual execution: **only explicit non-live test adapters**. Tests exercise worker execution and human review. No production provider transport is wired; without an injected adapter the request returns unavailable. The standalone worker deployment does not continuously process Group 3 AI runs yet. API keys alone do not enable it. Structured validation does not establish that every narrative inference is factually correct; human review remains required.

## 7. Sponsor/resource accounting

Individuals or explicit organization members can save/submit support. Organization onboarding is self-declared registered_unverified. Only event-authorized organizers accept/reject pledges. Draft/pledged terms can be revised or withdrawn; accepted obligations cannot be silently edited/withdrawn. Original offer revisions remain immutable. Organization private contact details never appear in public sponsor projections; recognition preferences govern public appearance.

Required quantity comes from published work-linked requirements. Offered and accepted pledges, unverified delivery reports, verified human receipts, reservations, free availability and remaining gaps are separate. Promise/report has zero inventory effect. Exact units only; no implicit conversion. A receipt can link the exact delivery report; unique report/reference constraints prevent duplicate credit. Receipts cannot exceed accepted support. Human verification stores an evidence reference, not a claim that a media file was independently analyzed. Corrections append reversals and cannot make existing reservations underfunded. Reservation/release checks run under the event lock and cannot produce negative free stock. Plan edits cannot silently remove/retype a resource with operational obligations or change its unit.

Funding intentions and external references remain support records; funding receipts are rejected by the inventory endpoint. No payment processing/settlement or verified monetary-contribution ledger was implemented. Consumption, equipment issue/return and execution custody commands are deferred; zero usage fields mean no authorized usage records exist, not proof of an executed event. Reusable-equipment reservation is conservative quantity allocation, not time-sliced rental optimization.

## 8. Existing frontend integration

Extended the opt-in HTTP adapter for discovery, application draft/steps/submit/status, organizer queue/review/clarification, human capability review, checks/offers/exact consent, information/alternative review, My Events, event-specific workspace projections, sponsor onboarding/offers/report/receipt and resource queries/requests. Server-issued IDs/current versions replace fixture templates. No silent demo fallback occurs. The seven existing workspace routes remain unchanged; accepted work comes only from current accepted assignments. Approved applicants without accepted assignments stay requests. Existing demo regression suite still passes.

HTTP-only controls/text expose capability review and advice review and display material offer conditions; layout/styles/screens were preserved. Organizer/public role and participant counts share persisted assignment records. Public demographic categories require enabled published settings, explicit participant consent, five eligible participants and five per displayed bucket. Private applicant totals are organizer-only. Sponsor matches explain declared requirement compatibility without a fabricated AI score.

Verification covers adapter request/response mapping and existing UI/component routing in jsdom. It does **not** prove a real browser-to-running-backend walkthrough. Execution, meetings, communications and blocker recovery return explicit unavailable/empty Group 4 state; HTTP does not borrow demo records to fill those modules. Actor Tree requirements remain Group 2 planned requirements; public role coverage/organizer queues carry actual Group 3 assignments, rather than altering immutable plan ownership.

## 9. Event Memory and governance

Genuine application/review/offer/consent/resource operations emit transactional audit/outbox and immutable operational sources. Private draft answers are not projected into memory. Derived operational memory is source-linked with proposed evidence stage and unknown outcome; participant consent, delivery promises and stock receipts never become verified work success. Superseded aggregate sources use the existing source invalidation machinery. Event creator identity is used for authorized private memory projection; actual initiating actor remains in the operation/audit. Cross-event memory sharing remains disabled.

Governance stays internal advisory/ticket tracking. Reviewed organizer/work conditions are included separately from self-reports and unknown external rules. No external authority accounts, automatic filings, legal approval or fabricated compliance certification were added.

## 10. Actual verification

| Command (cwd stated) | Final result |
|---|---|
| `backend/.venv/Scripts/python.exe backend/tools/run_postgres_tests.py -q --junitxml=../outputs/backend-group3/backend-tests.xml` (repository) | 108 passed, 0 failed, 0 skipped; real disposable PostgreSQL 16.11; exit 0. |
| `npm run typecheck` (frontend) | Passed, exit 0. |
| `npm test -- --reporter=json --outputFile=../outputs/backend-group3/frontend-tests.json` (frontend) | 69 tests / 24 files passed, 0 failed, exit 0; npm wrapper omitted report flags, so no JSON file from this run. |
| `node node_modules/vitest/vitest.mjs run --reporter=json --outputFile=../outputs/backend-group3/frontend-tests.json` (frontend) | 69 tests / 24 files passed, 0 failed; JSON evidence saved; exit 0. |
| `npm test -- --test-reporter=tap` (demo; package script runs node --test tests/*.test.mjs) | 146 passed, 0 failed/skipped, exit 0. |
| `node --test --test-reporter=tap demo/tests/*.test.mjs > outputs/backend-group3/demo-tests.tap` (repository) | 146 passed, 0 failed/skipped; saved TAP; exit 0. |
| `npm run build` (frontend) | TypeScript + Vite production build passed, exit 0. |
| `backend/.venv/Scripts/python.exe -m compileall -q backend/app backend/migrations backend/tests` (repository) | Passed, exit 0. |
| `backend/.venv/Scripts/python.exe -m pip check` (repository) | No broken requirements, exit 0. |

Final backend includes 89 prior tests and 19 new Group 3 cases: ten-participant consent/privacy, non-cleanup flow, original revisions/private draft, partial approval, clarifications, terms replacement/decline/withdrawal/expiry/idempotency, concurrent capacity and reservations, cross-event schedule conflicts, human capability review and stale confirmed plans, promise/report vs verified receipt/correction/unit invariants, organization permissions/private contacts, actual-context advisory/review, malformed/invented/timeout outputs, resource-advice staleness, readable stale assessment and operational memory provenance. Migration roundtrip/metadata checks are included in the full suite.

Earlier implementation runs exposed a disposable old migration shape and test setup that submitted disabled insight fields after republishing; both were corrected. An initial resume command used the wrong venv path and failed before tests; rerun used backend/.venv. Additional review fixed invalid delivery dates returning server errors, stale advisory reads during unpublished plan changes, and resource-request work/plan validation. Final suites above supersede earlier runs. Non-failing warnings: upstream Starlette/httpx TestClient deprecation and Vite bundle >500 kB. No automated screenshots, visual comparison, browser walkthrough, live provider inference, configured application DB connectivity or deployment test was performed.

## 11. Runtime blockers

A secret-safe configuration check still detects placeholder application database credentials. No connection/migration was attempted against that URL, no credentials were invented or overwritten. Isolated PostgreSQL success is not configured-application connectivity. Valid intended DATABASE_URL and explicit migration/startup are needed for live local HTTP use. Existing development signed-token identity remains a development boundary, not a production login/session solution. Secret values are absent from this report and evidence.

## 12. Exact files created/modified

`outputs/backend-group3/files-changed.txt` is the complete source/document manifest below; `file-manifest.json` records hashes. Git currently treats the project directories as untracked, so this is a task-change manifest, not a claim of a clean Git diff or commit. Generated build/cache artifacts are not source edits. Evidence files are indexed in verification.json.

```text
MODIFIED backend/README.md
MODIFIED backend/app/ai/planning_port.py
MODIFIED backend/app/ai/service.py
MODIFIED backend/app/api/group2.py
CREATED backend/app/api/group3.py
MODIFIED backend/app/events/source_revisions.py
MODIFIED backend/app/main.py
MODIFIED backend/app/memory/projections.py
MODIFIED backend/app/memory/schemas.py
MODIFIED backend/app/models.py
CREATED backend/app/participation/__init__.py
CREATED backend/app/participation/advisory.py
CREATED backend/app/participation/models.py
CREATED backend/app/participation/projections.py
CREATED backend/app/participation/schemas.py
CREATED backend/app/participation/service.py
MODIFIED backend/app/planning/service.py
MODIFIED backend/app/publication/service.py
CREATED backend/app/resources/__init__.py
CREATED backend/app/resources/invariants.py
CREATED backend/app/resources/models.py
CREATED backend/app/resources/service.py
MODIFIED backend/app/shared/source_resolver.py
CREATED backend/app/sponsorship/__init__.py
CREATED backend/app/sponsorship/models.py
CREATED backend/app/sponsorship/projections.py
CREATED backend/app/sponsorship/schemas.py
CREATED backend/app/sponsorship/service.py
CREATED backend/migrations/versions/0004_participation_support.py
CREATED backend/tests/test_group3.py
CREATED backend/tests/test_group3_extra.py
CREATED docs/implementation/group3-checkpoint.md
CREATED docs/implementation/group3-implementation-report.md
CREATED docs/implementation/group3-task.md
MODIFIED frontend/src/features/participation/ApplicationStatus.tsx
MODIFIED frontend/src/features/participation/ParticipantIntelligencePanel.tsx
MODIFIED frontend/src/features/participation/ParticipantReviewPanel.tsx
MODIFIED frontend/src/features/sponsor-offers/SponsorOffers.tsx
MODIFIED frontend/src/services/http-adapter.ts
MODIFIED frontend/src/services/organizer-contracts.ts
MODIFIED frontend/src/services/participant-contracts.ts
MODIFIED frontend/src/services/sponsor-contracts.ts
CREATED frontend/tests/http-group3.test.ts

```

## 13. Group 4 dependencies

Group 4 can build execution reports/evidence and human completion review on current immutable plan/work references, accepted assignment terms/consent, receipt/reservation boundaries, private operational sources, UoW/audit/idempotency and bounded proposal infrastructure. It must enforce own/delegated work authorization, preserve original evidence, add consumption/custody transitions with real records, and compute affected dependency subgraphs before any scoped recovery proposal. No Group 4 implementation began.

## 14. Incomplete/explicitly deferred

Live browser/backend deployment; production identity; live Meta/Modal transports and continuously deployed AI worker; file-byte evidence upload/verification; payments and verified funding ledger; consumption/equipment issue/return; accepted sponsorship obligation renegotiation beyond blocking silent edits; organization member administration/external verification; notifications/invite sending; execution reports/completion/attendance; meetings/communications/blocker recovery; complete resource-constrained/time-sliced scheduling. Withdrawn application history is preserved; a reapplication/reset workflow is not provided. Alternative requests and pending offer replacement are API-supported, but not every possible catalogue transition has a dedicated frontend control. No general group-registration allocation engine was added. Read projections currently use straightforward event-scoped queries and require later pagination/performance work at larger scale.

Group 3 stops here. Review this report before authorizing the next implementation group.
