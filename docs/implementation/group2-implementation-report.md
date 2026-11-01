# AroundYou Group 2 implementation report

Reviewed and verified 2026-11-01. Group 2 core persistence/API flows are implemented and tested. Live provider integration and full browser HTTP workflow verification remain partial. Group 3 has not started.

## Files

The exact absolute file manifest is [files-changed.txt](../../outputs/backend-group2/files-changed.txt). No demo source changes were found against the reviewed source hashes. Fixtures were not modified. No frontend visual redesign or CSS changes were made. Existing architecture reports remain design references; this report and generated OpenAPI describe actual implementation.

## Environment and migrations

Only invalid SESSION_SECRET was securely replaced locally; no secret value was displayed. Other environment values were preserved. Configured DATABASE_URL credentials remain placeholders, so the configured application database was not connected, migrated or reset. This is the remaining local runtime setup blocker. Docker is not required: PostgreSQL 16.11 native binaries ran an isolated loopback test cluster.

Additive migration `0002_group2_planning_publication` follows unchanged 0001, adds eight tables and event lifecycle/context/setup/publication pointers plus AI job linkage. New tables: planning_drafts, ai_runs, ai_proposals, governance_tickets, event_setup_revisions, event_finalizations, publications, published_roles. Total: 21 tables. Immutable database protections cover reviewed payloads and published snapshots; composite foreign keys preserve event scope. Migration roundtrip, metadata match and upgrade of existing Group 1 rows were tested without changing the configured application database.

## Implemented workflows

- Four-step durable draft save/resume, independent server-issued event IDs, exact original text/reviewed transcript history, manual reviewed interpretation and explicit created-unpublished transition.
- Manual stage/work/group/zone/resource plan editing; ordering, dependencies, quantities/units, cycles, references and finish-to-start timing validation. Work and stage revisions invalidate affected downstream confirmations. Immutable confirmed milestone snapshots and digest/version-bound pending proposals support apply/reject; stale results are rejected.
- Actor demand derives from confirmed work with skills, schedule coverage and manual corrections. Known zero remains zero; unknown demand remains unknown. No people, accepted commitments or inventory are manufactured. This is not a complete resource-constrained scheduler.
- Advisory governance tickets, document references and reminder preferences. Advice never constitutes external permission. Context changes invalidate stale advice. Document byte storage, government submissions and reminder delivery are not implemented.
- Immutable setup successors, explicit finalization and coherent publication snapshots. Changes require reconfirmation; the prior published snapshot stays intact until explicitly replaced. Reported resources are separate from verified stock. Invites/partners are draft records, not delivered invitations or accepted sponsorship fulfillment. Scheduled publication execution is unavailable.
- Canonical profile has exactly eight tabs: Overview, Stages, Volunteer Roles, Updates, Photos, Sponsors, Discussions, Impact. Public projection removes private context, emergency contacts, invite drafts and private partner/contact details. Operational tabs remain empty where their owning later groups are absent.

## AI and memory

Implemented typed Muse Spark request/output ports, current authoritative context separated from cited historical memory, input/output budgets, durable leased jobs, bounded retries, fencing, structured validation and source rechecks before/after inference. Results remain pending until human review. Fake adapters are used only in tests and report no live model execution. No network Muse Spark transport or automatically configured AI worker daemon is shipped; keys alone do not enable calls. Unconfigured requests return 503, not fabricated content. Modal extraction remains Group 1 interface/test implementation. Zero live Meta and zero live Modal calls were made in this task.

Existing authorized memory retrieval/context construction is reused. Immutable context/plan/decision sources project into source-linked derived memory; bounded excerpts/counts prevent large plans exceeding extraction budgets, while original full sources/digests remain unchanged. Existing correction, supersession, source invalidation and event authorization regressions passed. Execution/blocker/receipt source resolvers depend on their later groups; no fabricated outcomes or cross-event private sharing are added.

## Frontend status

AroundYouService remains the boundary. Default demo mode and replay scenarios remain separate. Opt-in HTTP mode uses real authenticated identity, per-event versions, serialized writes, idempotency and server DTOs; unsupported later-group operations fail closed. It supports Group 2 creation/planning/setup/publication actions plus discovery and organizing drafts. Selected draft resume and empty manual stage/work controls are tested; no Canary Hill template is used for backend creation. Advanced domain fields are API-supported but not all have expanded frontend editors. Full browser-driven HTTP flow, screenshots and visual comparison are unverified. Production authentication UI is not implemented; trusted short-lived CLI tokens are development-only. Runtime setup is documented in backend/README.md.

## Verification

- Working directory `backend`: `.venv/Scripts/python tools/run_postgres_tests.py -q --junitxml=.tmp/group2-results.xml` â€” 75 passed, 0 failed, 0 skipped; real isolated PostgreSQL 16.11.
- Working directory `frontend`: `npm test -- --reporter=json --outputFile=../outputs/backend-group2/frontend-tests.json` â€” 63 passed across 22 files.
- Working directory `frontend`: `npm run build` â€” passed TypeScript and Vite production build; large-chunk warning.
- Working directory `demo`: `npm test` â€” 146 passed, 0 failed, 0 skipped.
- Working directory `backend`: `.venv/Scripts/python -m compileall -q app migrations tests` â€” passed.

Backend total includes all original 44 Group 1 tests and 31 new Group 2/migration tests, with no failures or skips. Coverage includes two-event isolation, private-source permission revocation, context races during inference, stale proposals, exact approvals, dependency validation, work-only confirmation invalidation, actor derivation, immutable publication/private redaction, idempotency, memory and migration preservation. Frontend transport and JSDOM tests complement real API/database tests; they do not constitute browser end-to-end verification. Existing ten-participant and blocker-recovery scenarios remain demo-only regressions. Non-failing warnings: upstream Starlette/httpx TestClient deprecation and Vite bundle above 500 kB.

## Working API surface

Generated [OpenAPI](../../outputs/backend-group2/openapi.json) records request/response schemas and required headers. There are 62 installed HTTP operations including retained Group 1 routes. Write commands require authenticated grants, idempotency and expected versions as specified by their schemas. Model proposal endpoints require an explicitly injected provider; scheduled publication and unsupported operational commands are not claimed working services.

- `GET /health`
- `GET /v1/me`
- `GET /v1/events/{event_id}`
- `GET /v1/events/{event_id}/sources/current`
- `POST /v1/events/{event_id}/memory/extractions`
- `GET /v1/events/{event_id}/memory/extractions/{run_id}`
- `GET /v1/events/{event_id}/memory`
- `GET /v1/events/{event_id}/memory/{memory_id}`
- `POST /v1/events/{event_id}/memory/{memory_id}/review`
- `POST /v1/events/{event_id}/memory/{memory_id}/corrections`
- `POST /v1/events/{event_id}/memory/{memory_id}/retract`
- `POST /v1/events/drafts`
- `GET /v1/events/{event_id}/creation`
- `PATCH /v1/events/{event_id}/draft`
- `POST /v1/events/{event_id}/context-revisions`
- `POST /v1/events/{event_id}/context-interpretations`
- `POST /v1/events/{event_id}/confirm-creation`
- `POST /v1/events/{event_id}/planning/draft`
- `GET /v1/events/{event_id}/planning`
- `POST /v1/events/{event_id}/planning/checkpoints`
- `POST /v1/events/{event_id}/planning/items/{kind}`
- `PATCH /v1/events/{event_id}/planning/items/{kind}/{item_id}`
- `DELETE /v1/events/{event_id}/planning/items/{kind}/{item_id}`
- `PUT /v1/events/{event_id}/planning/stage-order`
- `PUT /v1/events/{event_id}/planning/manifest`
- `POST /v1/events/{event_id}/planning/stage-edits`
- `POST /v1/events/{event_id}/planning/arrangements`
- `POST /v1/events/{event_id}/planning/work-edits`
- `POST /v1/events/{event_id}/planning/work-proposals/{proposal_id}/apply`
- `POST /v1/events/{event_id}/planning/proposals/{proposal_id}/apply`
- `POST /v1/events/{event_id}/planning/proposals/{proposal_id}/reject`
- `POST /v1/events/{event_id}/planning/{level}-confirmations`
- `POST /v1/events/{event_id}/planning/actor-derivations`
- `PATCH /v1/events/{event_id}/planning/actor-requirements/{role_id}`
- `POST /v1/events/{event_id}/planning/actor-requirements`
- `POST /v1/events/{event_id}/governance/assessments`
- `POST /v1/events/{event_id}/planning/work-proposals`
- `POST /v1/events/{event_id}/planning/stage-proposals/revisions`
- `POST /v1/events/{event_id}/planning/stage-proposals`
- `POST /v1/events/{event_id}/context-proposals`
- `GET /v1/ai-runs/{run_id}`
- `POST /v1/events/{event_id}/governance/proposals/{proposal_id}/review`
- `POST /v1/events/{event_id}/context-proposals/{proposal_id}/review`
- `GET /v1/events/{event_id}/governance`
- `POST /v1/events/{event_id}/governance/tickets`
- `POST /v1/events/{event_id}/governance/tickets/{ticket_id}/documents`
- `PATCH /v1/events/{event_id}/governance/tickets/{ticket_id}/reminders`
- `POST /v1/events/{event_id}/setup/draft`
- `GET /v1/events/{event_id}/setup`
- `POST /v1/events/{event_id}/setup/checkpoints`
- `PATCH /v1/events/{event_id}/setup/sections/{section}`
- `PUT /v1/events/{event_id}/setup/participant-configuration`
- `POST /v1/events/{event_id}/setup/invitation-drafts`
- `DELETE /v1/events/{event_id}/setup/invitation-drafts/{invite_id}`
- `POST /v1/events/{event_id}/setup/partner-drafts`
- `PATCH /v1/events/{event_id}/setup/publication-preferences`
- `POST /v1/events/{event_id}/finalizations`
- `POST /v1/events/{event_id}/publications`
- `GET /v1/events/{event_id}/profile`
- `GET /v1/events`
- `GET /v1/me/events`
- `GET /v1/events/{event_id}/context-proposals/{proposal_id}`

## Group 3 dependencies and stopping point

Before running the configured application: replace placeholder development database credentials, create/select the intended local database, explicitly apply Alembic and provision trusted identities/grants. Group 3 can build on immutable published role requirements, event-scoped auth, plan/setup/publication IDs, transactional idempotency/audit/outbox and the isolated test harness. It must implement real applications, human approval, assignment offers, conflict checks and participant acceptance independently; role requirements must never be counted as participants. Sponsorship receipts, inventory, evidence/execution and blocker recovery remain later-group work. Live provider transport/worker deployment, production authentication and scheduled delivery require separate integration decisions. No Group 3 coding was started.
