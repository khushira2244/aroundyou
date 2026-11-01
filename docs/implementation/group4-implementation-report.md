# AroundYou Backend Group 4 implementation report

Date: November 1, 2026. Approved scope: group4-task.md. Group 4 builds on Groups 1–3 in the same FastAPI/PostgreSQL monolith. No live inference, network integration, model deployment, application-database migration, Group 5 recovery or demo-fixture changes were performed.

## 1. Working features and transitions

Implemented a bounded execution core with plan-bound work records, immutable report revisions and accepted-assignment authorization. A current assignee may start/report only work in their exact current accepted terms. Changed, withdrawn and unaccepted offers confer no reporting authority. Previously saved originals remain available to their author; submitted historical reports retain immutable plan/assignment/terms references and can be examined by authorized reviewers without restoring future participant authority.

Work: not_started/ready → in_progress → submitted_for_review; uncleared issues or unverified dependencies surface blocked readiness. Participant claims and human verification are separate. Human verification records explicit cumulative percent; it does not automatically complete work. A verified completion claim with no remaining work, current source references and cleared dependencies may be separately approved as completed. Duplicate work completion conflicts. Reopening requires a reason, resets current verified progress and returns the accepted report for correction; original review history is retained. Stage completion is another explicit organizer action bound to exact work versions, not an automatic task-count shortcut.

Reports: draft → submitted → under_review → verified (internal accepted) / rejected / needs_correction / clarification_requested. Corrections append a new draft/submission; original statements, timestamps and review notes remain immutable in execution_revisions. Multiple reports per work item are supported. Drafts and original uploads stay private until submission. Current failed/retracted uploads can be removed from a successor report without erasing their original metadata/history. Read projections use the existing frontend status vocabulary, including the internal accepted→verified mapping.

Server start/submission/review/completion-recording times are separate from the immutable planned schedule and participant-reported occurrence text. These timestamps record authorized actions, not independent proof of physical presence or GPS location.

## 2. Migration and database tables

Additive frozen Alembic migration 0005_execution_evidence follows 0004; **nine new tables, 43 application tables total**. Existing migrations and demo fixtures are preserved.

| Table | Purpose / invariants |
|---|---|
| work_executions | One event/plan/work current operational projection, version, verified/reported percent, recorded transition times. |
| work_reports | Author/event/plan/work/assignment/immutable terms linkage; current workflow/content/version. |
| evidence_assets | Private report/author linkage; original content hash, size/type, opaque storage key, inspection/retraction/transcript state. |
| execution_revisions | Immutable aggregate sequence, actor/time, exact snapshot/digest, evidence stage/outcome/criteria; source lineage. |
| execution_review_grants | Explicit event/stage/plan reviewer grants. Accepted role labels never create grants automatically. |
| attendance_records | Separate self-reported and human-verified presence; corrections retain historical revisions. |
| resource_operations | Append-only consume/checkout/return/reversal operations, exact reservation/report revision/usage, unique event reference/reversal. |
| work_issues | Source-linked work/resource issue, severity/category, original statement/time, handling state and independently cleared condition. |
| coordination_records | Typed announcement/note/discussion/meeting/decision/action records; also bounded internal stage-completion and measurement confirmations. |

Uniqueness, foreign keys and immutable triggers cover execution revisions and resource operations. Migration roundtrip, upgrade preservation and metadata consistency are exercised by the backend suite. Command schemas reject unknown fields; clients cannot submit arbitrary authoritative JSON or actors. Operational plan snapshots and assignment terms remain immutable.

## 3. Exact APIs implemented

All routes use the existing /v1 envelope, bearer identity, event scope, transaction/UoW and sanitized errors. Event mutations require If-Match and Idempotency-Key; the shared event-lock path refreshes SQLAlchemy identities after waiting so cached pre-lock records cannot pass stale expected-version checks; report/evidence/coordination/attendance reviews additionally bind exact revisions. Private review replays recheck reviewer access after revocation. Inventory mutations require organizer authority, not a stage-review grant.

- `GET /v1/events/{event_id}/execution`
- `POST /v1/events/{event_id}/execution/work/{work_id}/reopen`
- `POST /v1/events/{event_id}/execution/work/{work_id}/complete`
- `POST /v1/events/{event_id}/execution/work/{work_id}/start`
- `POST /v1/events/{event_id}/reports/draft`
- `POST /v1/events/{event_id}/reports/{report_id}/submit`
- `POST /v1/events/{event_id}/reports/{report_id}/review`
- `GET /v1/events/{event_id}/reports/{report_id}/revisions`
- `POST /v1/events/{event_id}/execution/review-grants`
- `POST /v1/events/{event_id}/evidence/uploads`
- `PUT /v1/events/{event_id}/evidence/{asset_id}/content`
- `GET /v1/events/{event_id}/evidence/{asset_id}/content`
- `POST /v1/events/{event_id}/evidence/{asset_id}/inspection`
- `POST /v1/events/{event_id}/media/{asset_id}/transcription-runs`
- `POST /v1/events/{event_id}/attendance`
- `POST /v1/events/{event_id}/resource-usage/returns`
- `POST /v1/events/{event_id}/resource-usage/checkouts`
- `POST /v1/events/{event_id}/resource-usage/consumption`
- `POST /v1/events/{event_id}/resource-usage/{operation_id}/reversals`
- `POST /v1/events/{event_id}/issues`
- `POST /v1/events/{event_id}/issues/{issue_id}/review`
- `GET /v1/events/{event_id}/coordination`
- `POST /v1/events/{event_id}/coordination`
- `POST /v1/events/{event_id}/coordination/{record_id}/actions`
- `POST /v1/events/{event_id}/execution-assessments`
- `POST /v1/events/{event_id}/execution-proposals/{proposal_id}/review`
- `POST /v1/events/{event_id}/reports/{report_id}/review-start`
- `POST /v1/events/{event_id}/execution/stages/{stage_id}/complete`
- `POST /v1/events/{event_id}/reports/{report_id}/measurements`

The catalogue contains 29 route registrations. The transcription route is explicitly unavailable (503), not implemented transcription. OpenAPI in outputs/backend-group4/openapi.json gives exact schemas/headers; group4-endpoints.json indexes the new routes. Existing Group 3 participation/dashboard/public-profile reads are extended rather than duplicated. Existing AI-run polling returns typed execution advice. Not every new route has a separate test case; tests cover complete workflows and negative boundaries.

## 4. Evidence storage: actual bytes versus metadata

An injectable PrivateObjectStorage interface and LocalPrivateStorage implementation store **actual original bytes** in a dedicated configured private directory. Integration tests upload and download real byte payloads, compare bytes/hashes, reject invalid signatures and enforce event/author/reviewer access. Files use server-generated opaque basenames with exclusive creation, no user-supplied paths. Public/static/dist storage roots are rejected. Display filenames are validated; downloads are authenticated octet-stream attachments with no-store/nosniff headers. No public media directory or embedded private media appears in event profiles.

Upload requests are streamed into a bounded buffer (up to 50 MB video; 10 MB image/audio/document), then validated and written. This is a bounded local development adapter, not cloud streaming/presigned upload. JPEG/PNG/WebP, selected WAV/MP3/OGG/WebM audio, MP4/WebM video, PDF/plain-text documents and typed original text statements are supported. Unsupported types, mismatched signatures/sizes, unsafe filenames and unauthorized/cross-event references fail. Signature checking does not decode/scan the full file or prove its semantic authenticity. A failed/unavailable upload can be explicitly retracted from the current draft so a text-only submission remains possible; the original attachment history is retained.

Lifecycle: awaiting_upload → pending_inspection → accepted_for_review; quarantine/retraction remain distinct. An uploaded original can be submitted pending human inspection, but cannot support report verification until accepted for review. Inspection accepts relevance/type for review only, not work completion. Retraction preserves bytes/history, removes the source from the successor report, invalidates affected accepted report/work verification and excludes stale measured outputs. Rejected/quarantined content is not served as an ordinary attachment.

No machine transcription exists. The transcription endpoint returns provider_unavailable and never invents text. An authorized reviewer may explicitly record a human-supplied reviewed transcript against original accepted audio, labeled as manual reviewed input. That API is not automatically exposed as a recording/transcription UI.

Application EVIDENCE_DIRECTORY remains unset: file upload in the actual app is unavailable until private storage is configured. Test storage lives in isolated workspace .tmp directories. Local filesystem access relies on host permissions; cloud storage, antivirus, encryption/key management, orphan-object cleanup, retention erasure and multi-host deployment remain future work. A database rollback after an object write can leave an inaccessible orphan object; it does not publish it or fabricate a completed upload.

## 5. AI observation interfaces and actual execution

Reused MuseSparkContextBuilder, MuseSparkRequest, durable AI runs/jobs/leases/fencing/retry/deadline, pending proposals and human advice review. Execution input contains actual original report text, manually reviewed transcript where available, exact report/evidence revisions/hashes/status, immutable work/assignment scope, current assignment state, prior verified work and eligible source-linked event memory. Other people's private cross-event data is not supplied.

A strict EvidenceAdvice schema separates reported_fact, source_supported_observation, inference, uncertainty, missing_evidence and recommendation. Source-supported observations require an exact supplied text quote; evidence IDs must be authorized inputs. Extra authority fields and unsupported media_input values fail. The task explicitly declares **metadata_only**: original image/video/audio bytes are not sent to the model, and no visual/audio analysis is claimed. Possible blocker signals are advice only; no issue, attendance, usage, completion or plan transition is automatically created.

Report/evidence/assignment/work/context/memory/source versions are checked before and after execution and at human acceptance. Malformed, unavailable, stale and timed-out outputs fail closed. Tests use explicitly labeled non-live adapters only. No Muse Spark/Modal model call, credit consumption or network inference occurred. Default runtime has no inference adapter; AI requests return unavailable. Continuous deployment of an AI worker and live multimodal transport remain unimplemented. Human observation review approves advice only, never the work itself.

## 6. Human verification and progress

Organizer access and stage reviewer grants are explicit; a delegated reviewer must retain a current accepted assignment in the authorized stage and cannot self-verify their own report. A grant adds no inventory, event-wide private-source or plan authority. Review notes and exact evidence versions accompany decisions. Report verification is bound to a submitted revision, and cumulative verified percent cannot silently decrease—reopening provides the correction path.

Reported percent, AI narrative interpretation and human-verified percent remain separate. Finish-to-start work and stage predecessors must have verified completion before readiness/final completion. Acknowledged work conditions/exclusions are explicit in start commands. Stage and event progress use known confirmed person-hour weights; unknown or incomplete weighting returns unavailable rather than assuming equal tasks. Known unit counts are displayed separately. Verified source measurements remain separate: if multiple independent report measurements share a legacy impact metric, no cumulative total is silently selected or summed; aggregation/overlap policy remains a human product decision. Relative dates without a reliable anchor do not become invented overdue timestamps; detailed overdue/at-risk forecasting is not implemented in this slice.

Measured impact requires a separate organizer confirmation of an exact measurement present in a reviewed report. Generic metric/unit values remain generic; recognized environmental metrics map only with their explicit matching unit. Task completion never generates waste weight, area improved, attendance or beneficiaries. Corrected report/evidence revisions invalidate dependent published measurements. Reopening and human-recorded outcomes are contextual historical records, not automatic generalizable success lessons.

## 7. Attendance and resource invariants

Acceptance/schedule is not attendance. The existing execution read projection exposes own attendance records or the organizer’s event records with exact revisions. An assignee may record a current check-in claim; an organizer separately verifies or corrects it. Claims carry server recording timestamps; no GPS proof or inferred attendance exists. A changed self-report clears current verification pending renewed review. No current frontend attendance screen was invented; typed APIs provide the boundary.

Group 3 receipt/reservation accounting is extended rather than replaced. Participant declarations do not consume stock. Organizer reconciliation links the exact report revision, usage ID, unit and work-compatible reservation. Only verified received stock can be consumed/issued. Concurrent operations serialize under the event lock. Unique references make repeat operations idempotent; changed payloads cannot reuse a reference. Consumption cannot exceed declared quantity/remaining reservation; negative inventory and implicit conversions are rejected.

Consumables use consume/reversal; reusable equipment uses checkout/partial return. Outstanding checkout reduces usable stock and cannot be issued twice. Returns cannot exceed outstanding quantities; reservations cannot be released while equipment remains checked out. Authorized organizers can return an existing recorded loan while its original report awaits correction, without restoring participant reporting authority. Consumption reversals append linked operations; original movements are immutable. Reported usage with ledger history cannot be silently edited. Damage/loss/shortage may be reported as typed issues; automatic loss write-off, replacements and complete custody transfer between people are not implemented. Services/facilities/funding do not use fake consumable or equipment commands. No payment settlement was added.

## 8. Coordination and communication limits

Typed persisted announcements, internal notes, work-linked discussions/replies, meetings/agendas/invitee associations/RSVP, decisions and human-approved follow-up actions share the existing workspace/dashboard. Public, participants and internal visibility are checked server-side; private meeting/action access follows invitation/organizer scope. Internal messages do not leak to public profiles or participant updates. Explicit schedule confirmation records metadata; RSVP is neither attendance nor schedule confirmation.

No email/WhatsApp/SMS/push delivery, real-time calls, calendar synchronization or WebSockets exist. invitation_delivery remains not_sent. Meeting availability/conflict optimization, automatic scheduling, live AI meeting suggestions and conducted-meeting recording are not claimed. HTTP AI-meeting controls clearly show unavailable; manual meeting records work. Follow-up approval records approved only. A separate explicit human completion command and note are required before the follow-up becomes completed; neither action mutates operational work or plans. Schedule-intent publishing and some advanced invitation editing remain explicitly unavailable.

## 9. Issue boundary for Group 5

Typed source-linked issues retain original reporter/work/resource/evidence references, reported occurrence, received time, severity, effects and history. Handling state is reported → acknowledged → investigating → resolved/closed, with reinvestigation allowed. condition_cleared is separate: acknowledging/closing a ticket without verified clearance leaves blocking readiness in place. Human review records the clearance basis; AI possible-issue signals cannot create verified incidents or activate plans.

Group 4 provides records only. No affected-subgraph recovery engine, alternatives, plan activation, revised assignment reconfirmation or external incident verification was added. Existing Group 5 HTTP operations fail explicitly; demo recovery remains unchanged. Issue handling/clearance APIs are working, while the existing frontend primarily displays/reports issues and does not expose every investigation transition.

## 10. Event Memory lineage and eligibility

ExecutionRevision is a first-class source kind with exact revision/digest/actor and immutable plan/work/assignment/terms linkage. Genuine submitted attempts, human decisions, attendance, evidence changes, stage/measurement confirmations and coordination records create transactional audit/outbox records. Private draft report/media content is not projected to organizer memory before submission. Storage keys and media bytes are excluded from memory snapshots.

Evidence stages proposed/attempted/verified and outcome unknown/successful/failed/mixed/inconclusive remain independent. Human report review may explicitly classify an attempt outcome with rationale; ordinary completion defaults to inconclusive for reusable learning, never an invented success lesson. Human inventory reconciliation can preserve its exact verified-operation provenance without implying event success.

Memory retrieval checks latest aggregate sources, reviewer permission, stage work-version dependencies and measurement report revisions. Corrections/reopening/retraction immediately make stale derived entries ineligible; immutable original memories and source history remain. Cross-event private reuse is disabled. Tests exercise verified source classification, actual persisted derived memory, and ineligibility after correction; no real-world success was fabricated.

## 11. Frontend HTTP integration

AroundYouService remains the single boundary. HTTP execution state and commands use actual server IDs/versions; binary file upload sends the selected File, not an IndexedDB reference. Existing demo IndexedDB storage and all fixture scenarios remain separate. No fallback demo execution data is returned after HTTP failure. Unsupported Group 5 actions fail before execution-state fetching.

Wired existing report draft/submit/review/completion, source inspection/retraction/download, explicit start conditions, human progress input, resource reconciliation, stage review, issue reporting, organizer notes/announcements/meetings/follow-ups/RSVP and public discussion/reply actions. Public profile/progress and participant/organizer projections use shared persisted records. Participant-targeted updates stay in authorized workspace reads. Existing pages/routes/sidebar/styles remain; HTTP-only labels/controls avoid claims of local-only storage, demo identity or live AI.

Not every API has a dedicated frontend control: attendance, human transcript entry, detailed issue investigation, execution advice review UI, work reopening and ledger reversals are principally API-level. The backend returns explicit unavailable/empty states for unsupported scheduling/recovery/delivery integrations. No second dashboard, workspace or communication product was created. Browser layout/screenshot comparison and actual running browser-to-backend walkthrough were not performed.

## 12. Verification

Final results are recorded in outputs/backend-group4/verification.json. Required evidence includes backend JUnit XML, frontend Vitest JSON, demo TAP, OpenAPI, runtime status and file hashes. **Do not treat earlier intermediate reports as final passing results.**

| Command | Working directory | Final result |
|---|---|---|
| `backend/.venv/Scripts/python.exe backend/tools/run_postgres_tests.py -q --tb=short --junitxml=../outputs/backend-group4/backend-tests-final.xml` | repository | **128 passed, 0 failed/errors/skipped**, real isolated PostgreSQL; exit 0; includes all prior 108 tests. |
| `backend/.venv/Scripts/python.exe backend/tools/run_postgres_tests.py tests/test_group4.py -q --tb=short --junitxml=../outputs/backend-group4/group4-final.xml` | repository | **20 passed**, final execution recheck after the final report/custody/measurement/read-projection corrections; exit 0. These overlap the full suite, not 20 extra tests. |
| `node node_modules/vitest/vitest.mjs run --reporter=json --outputFile=../outputs/backend-group4/frontend-tests-final.json` | frontend | **72 passed / 25 test files**, 0 failed; exit 0. |
| `node node_modules/vitest/vitest.mjs run tests/http-group4.test.ts tests/execution.test.tsx --reporter=json --outputFile=../outputs/backend-group4/frontend-focused-final.json` | frontend | 10 passed in the focused HTTP/execution check; overlaps full suite. |
| `node --test --test-reporter=tap demo/tests/*.test.mjs > outputs/backend-group4/demo-tests.tap` | repository | **146 passed**, 0 failed/skipped, fixtures unchanged; exit 0. |
| `node node_modules/typescript/bin/tsc -b > ../outputs/backend-group4/typecheck.log 2>&1` | frontend | Passed, exit 0. |
| `npm run build > ../outputs/backend-group4/build.log 2>&1` | frontend | TypeScript + production Vite build passed, exit 0. |
| `backend/.venv/Scripts/python.exe -m compileall -q backend/app backend/migrations backend/tests` | repository | Passed, exit 0. |
| `backend/.venv/Scripts/python.exe -m pip check` | repository | No broken requirements, exit 0. |

The final 20-case recheck validates the latest Group 4-only changes; it was not another full 128-case run. Coverage includes raw original text, current assignment authority/withdrawal, scoped review, partial progress/corrections, no participant-driven reopening of completed work, actual private byte ingestion/retraction, missing storage/transcription, attendance claims/read/review, consumption concurrency/reversal, partial equipment returns during report correction, distinct issue handling/clearance, meetings/discussion privacy and separate follow-up approval/completion, malformed/stale/timeout observations, source-linked derived memory invalidation, a true expected-version race, weighted dependency progress, explicit stage approval and separate source measurements. No browser walkthrough/screenshot comparison, live provider, configured application DB or cloud storage was verified.


Intermediate failures were preserved rather than hidden: a sandbox temp-directory failure was fixed by using workspace-private test storage; a missing test import was corrected; a long measurement idempotency operation key was shortened without weakening payload binding; an attendance test was corrected to accept explicit null unverified fields. An obsolete HTTP test expecting execution to be unavailable was updated to assert the real route. Frontend timeout runs under concurrent heavy tests and an unsupported-operation test were rerun after sequential verification/fix. Fixtures were not changed to pass tests. Non-failing upstream TestClient deprecation and Vite bundle warnings are reported with final results.

## 13. Exact files changed

Source/document manifest: outputs/backend-group4/files-changed.txt. Hash manifest: file-manifest.json. The workspace project directories are currently untracked in Git; these are task-change manifests, not a clean committed diff. Runtime .tmp/private objects, caches/build outputs and secret .env files are excluded from source manifests. No demo fixtures or CSS files were modified.

```text
MODIFIED backend/.env.example
MODIFIED backend/README.md
MODIFIED backend/app/ai/planning_port.py
MODIFIED backend/app/ai/service.py
MODIFIED backend/app/api/group2.py
MODIFIED backend/app/api/group3.py
CREATED backend/app/api/group4.py
CREATED backend/app/execution/__init__.py
CREATED backend/app/execution/advisory.py
CREATED backend/app/execution/coordination.py
CREATED backend/app/execution/evidence.py
CREATED backend/app/execution/ledger.py
CREATED backend/app/execution/models.py
CREATED backend/app/execution/projections.py
CREATED backend/app/execution/schemas.py
CREATED backend/app/execution/service.py
CREATED backend/app/execution/storage.py
MODIFIED backend/app/main.py
MODIFIED backend/app/memory/projections.py
MODIFIED backend/app/memory/schemas.py
MODIFIED backend/app/models.py
MODIFIED backend/app/participation/projections.py
MODIFIED backend/app/publication/service.py
MODIFIED backend/app/resources/service.py
MODIFIED backend/app/settings.py
MODIFIED backend/app/shared/source_resolver.py
CREATED backend/migrations/versions/0005_execution_evidence.py
CREATED backend/tests/test_group4.py
CREATED docs/implementation/group4-checkpoint.md
CREATED docs/implementation/group4-implementation-report.md
CREATED docs/implementation/group4-task.md
MODIFIED frontend/src/features/event-profile/ProfileTabs.tsx
MODIFIED frontend/src/features/execution/EvidenceAttachments.tsx
MODIFIED frontend/src/features/execution/EvidencePreview.tsx
MODIFIED frontend/src/features/execution/ExecutionReviewPanel.tsx
MODIFIED frontend/src/features/execution/ReportReviewControls.tsx
MODIFIED frontend/src/features/execution/WorkExecutionDetail.tsx
MODIFIED frontend/src/features/organizer/OrganizerMeetings.tsx
MODIFIED frontend/src/features/organizer/OrganizerOverview.tsx
MODIFIED frontend/src/services/execution-contracts.ts
MODIFIED frontend/src/services/http-adapter.ts
MODIFIED frontend/src/services/organizer-contracts.ts
MODIFIED frontend/tests/http-adapter.test.ts
CREATED frontend/tests/http-group4.test.ts
```

## 14. Configuration and deployment blockers

Secret-safe inspection still finds placeholder application DATABASE_URL credentials. No connection, reset or migration was attempted against that URL, and no credentials were invented/printed/overwritten. Real disposable PostgreSQL tests do not establish configured-application connectivity. EVIDENCE_DIRECTORY is unset; configure a dedicated private path or object-storage implementation before real byte uploads. Production login/session integration, deployment, backups/retention, cloud object policy and continuously running AI/notification workers remain separate work. Meta/Modal keys and CLI authentication were not modified.

## 15. Completion assessment, Group 5 dependencies and deferrals

Group 4 delivers a tested bounded operational core and HTTP integration, with runtime/frontend coverage limits listed above. It is not a complete production execution, communications or media platform. Remaining: live providers/multimodal/transcription, cloud/presigned storage, malware/semantic media verification, physical location proof, external notifications/calls, detailed overdue forecasting, meeting availability scheduling/conducted state, loss write-off/complex custody transfer, some per-transition UI controls, scalable pagination and performance optimization. Reports use conservative version conflicts and straightforward event-scoped queries suitable for the hackathon; large-event query efficiency is not certified.

Group 5 can consume immutable report/evidence/verification/usage/issue and decision sources, current plan dependencies, accepted terms, exact source versions and outbox/audit. It must compute affected dependency subgraphs, produce scoped pending proposals and require human review/deterministic activation and renewed consent as appropriate. No Group 5 implementation, model deployment or external service request was started. Stop here for review.
