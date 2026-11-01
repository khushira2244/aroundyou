# AroundYou backend — Groups 1 and 2

FastAPI modular monolith; PostgreSQL operational authority; source-linked derived Event Memory. Group 2 adds event creation, planning, advisory governance, setup and versioned publication. Replay fixtures and provider credentials remain unchanged.

## Local setup (PowerShell, from `backend`)

```powershell
python -m venv .venv
$env:TEMP = (New-Item -ItemType Directory -Force .tmp).FullName
$env:TMP = $env:TEMP
.venv/Scripts/python -m pip install -r requirements.lock
.venv/Scripts/python -m pip install --no-deps -e .
# Configure .env using .env.example; keep your own provider secrets private.
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

The database must already exist. Migrations are explicit, never run during app import/startup. `DATABASE_URL` must use `postgresql+psycopg://`. `SESSION_SECRET` must have at least 32 characters. No fallback secret or demo login is accepted. `.env`, virtualenv, test clusters and caches are Git-ignored.

To replace a short session secret yourself without printing it, run the following inside `backend` (invalidates tokens signed with the old secret):

```powershell
.venv/Scripts/python -c "import secrets; from dotenv import set_key; set_key('.env', 'SESSION_SECRET', secrets.token_urlsafe(48))"
```

Group 2 replaced only the invalid short session secret with a secure local random value. No Meta/Modal keys were printed, changed, or used. Their presence does not enable provider calls in Group 1.

## Trusted local administration

```powershell
.venv/Scripts/python -m app.cli provision --subject local-owner --name Organizer --title 'Community reading workshop' --category Education --context 'Plan reading practice for local adults'
.venv/Scripts/python -m app.cli token --subject local-owner
.venv/Scripts/python -m app.cli worker --once
# Or keep a worker running:
.venv/Scripts/python -m app.cli worker
```

Provisioning deliberately requires an explicit original context and category; it never imports Canary Hill or generates successful outcomes. It creates a user if needed, a new event, explicit event grants, an immutable original context, audit and an outbox record in one transaction. It is an administrative CLI, not an HTTP signup/identity-picker endpoint. Token prints a short-lived bearer token only when YOU invoke that command; do not commit/share its output. There is no public token-minting/password/OAuth endpoint. Production identity-provider login and individual-token revocation remain future integration work. User disablement and grant revocation are checked on requests. `SESSION_SECRET` authenticates the local trusted issuer; Meta and Modal tokens are never login credentials.

## Implemented API

`/health` is public readiness-of-process only (not a DB/provider connectivity claim). OpenAPI `/docs` and `/openapi.json` describe the installed app. Everything below requires signed bearer auth, active provisioned user, and explicit database grants:

- `GET /v1/me`
- `GET /v1/events/{event_id}` — minimal event identity/version; not the full frontend canonical profile DTO.
- `GET /v1/events/{event_id}/sources/current` — source refs for authorized original-source readers.
- `POST /v1/events/{event_id}/memory/extractions` — 202 durable receipt, `Idempotency-Key` required.
- `GET /v1/events/{event_id}/memory/extractions/{run_id}`
- `GET /v1/events/{event_id}/memory` — lexical query, kind/evidence/outcome, category/work-pattern/tags/conditions filters, bounded pagination.
- `GET /v1/events/{event_id}/memory/{memory_id}` — current eligible published revision.
- `POST /v1/events/{event_id}/memory/{memory_id}/review`
- `POST /v1/events/{event_id}/memory/{memory_id}/corrections`
- `POST /v1/events/{event_id}/memory/{memory_id}/retract`

Memory decisions require the exact digest, immutable revision, `If-Match` mutable version and idempotency key. API responses use `data/meta`; domain failures are bounded `error` envelopes. Inaccessible IDs return 404. Do not use disabled buttons as authorization.

Example extraction body (get actual IDs/digests from `/sources/current`):

```json
{"source_refs":[{"source_kind":"context","source_id":"REPLACE","source_revision":1,"source_digest":"REPLACE_WITH_64_HEX_DIGEST"}],"extractor":"deterministic","schema_version":"memory-v1","purpose":"planning"}
```

A worker must run to consume queued jobs. A 202 response is not model success. Outbox source capture uses the same deduplicated projection service. PostgreSQL leases, SKIP LOCKED claims, fencing tokens, retries/backoff and terminal exhaustion survive process restarts; provider work runs outside transactions and its results are revalidated before commit. A lost worker's late result is rejected.

## Memory behavior and current limits

- Genuine immutable context/plan/observation-decision revisions are resolved by event, revision and hash. Private originals require separate permission, even for event members.
- Deterministic projection copies bounded original excerpts with citations; it does not generate a lesson, measure work or infer success. Full originals remain in their source records. Model output stays candidate until reviewed and cannot invent outcome verification.
- Source correction and revoked permissions exclude stale memory at read time, independently of background invalidation. Memory correction appends a candidate successor and retires the original; reviewed publication is separate. Observation-decision corrections invalidate the prior outcome lineage.
- Memory run records capture extraction provenance and retrieval selection manifests. Generic audit stores bounded IDs/digests, not tokens or private prompts. Invalidation/retraction excludes old revisions; physical retention/deletion workflows remain outside Group 1.
- Source kinds currently supported: context, plan, decision. Execution reports, files, blockers, resource receipts and their real source resolvers arrive with their owning group. Do not manufacture those sources in memory.
- Same-event memory only. `include_reusable=true` does NOT broaden permission or enable cross-event sharing; the result explicitly states cross-event reuse is disabled. A reviewed sanitization/sharing policy is still required before enabling it. Partial stage/work grants fail closed for whole-event memory queries.
- Correction currently accepts exactly one correcting source. Candidate output limits: 20 entries, 20 assertions each, total text 16,000 characters. Source input budget: 20 refs, 12,000 characters. Filters use exact supplied conditions; they do not prove unspecified applicability.
- `ModalExtractionPort` is an interface with a fake implementation in tests. No live hosted model or network adapter is enabled, even when CLI credentials exist. `open_weight` API requests return 503 without an explicitly injected port. No synthetic successful provider result is substituted.
- `MuseSparkContextBuilder` is an implemented structured context assembly/revalidation service and a consumer interface, not a model call. It separates current authority from derived memory and records citation manifests. Caller-owned application transaction must commit its retrieval manifest.
- Foundation plan schema validates IDs, stage membership and dependency acyclicity; Group 2 adds draft planning and publication; resource-constrained scheduling and operational recovery remain outside this group. New plan context mismatch invalidates its use for planning input.
- Local shared-secret JWT boundary is for trusted development integration. External IdP/OAuth, browser session cookies/CSRF, rate limiting, retention administration and deployment hardening are not claimed complete. An opt-in Group 2 HTTP adapter is available; default demo mode remains separate.

## Tests

```powershell
# Uses a separate disposable PostgreSQL cluster, never the database in .env:
$env:PG_BIN = 'C:/Program Files/PostgreSQL/16/bin'
.venv/Scripts/python tools/run_postgres_tests.py -q --tb=short --junitxml=.tmp/group1-results.xml
# Or use explicitly supplied, disposable databases named with _test suffix:
$env:TEST_DATABASE_URL = 'postgresql+psycopg://.../aroundyou_group1_test'
$env:TEST_MIGRATION_DATABASE_URL = 'postgresql+psycopg://.../aroundyou_group1_migration_test'
.venv/Scripts/python -m pytest -q
# From ../demo:
npm test
```

Integration tests downgrade/rebuild/truncate ONLY the explicitly named `_test` databases. Do not point them at personal/project data. Without those variables the PostgreSQL tests skip with an explicit reason; skips are not passes. The runner binds its trust-authenticated test cluster only to loopback, stops it in `finally`, and keeps local data/logs ignored under `.tmp`.

Verified implementation run: 44 backend tests passed on real PostgreSQL 16.11; all 146 existing demo tests passed unchanged. Initial test-fixture naming and stale disposable migration-schema failures were corrected before the final pass. One upstream Starlette/httpx TestClient deprecation warning remains; no failing/skipped backend tests in the isolated run. `pip check` and compileall passed. No production/configured database migration, frontend connection or live provider test was performed.

Framework references used: [SQLAlchemy transaction/session documentation](https://docs.sqlalchemy.org/en/20/orm/session_basics.html), [FastAPI bearer/JWT documentation](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/), [PostgreSQL initdb documentation](https://www.postgresql.org/docs/16/app-initdb.html). These inform infrastructure mechanics, not approval of operational AI authority.


## Group 2 runtime and limits

Migration `0002_group2_planning_publication` adds eight tables (21 total), immutable setup/finalization/publication records, planning drafts and version-bound AI proposals. OpenAPI is the exact installed route catalogue; see `../outputs/backend-group2/openapi.json` and `../docs/implementation/group2-implementation-report.md`.

The configured development database was NOT migrated: its credentials remain placeholders. Set a real intended local development DATABASE_URL, then run the explicit Alembic command above. Real isolated PostgreSQL tests do not establish connectivity to that configured database.

For frontend integration, set `VITE_AROUNDYOU_MODE=http` and `VITE_AROUNDYOU_API_URL=http://127.0.0.1:8000` in frontend development configuration. Start both servers. Use a short-lived trusted local CLI bearer token in browser sessionStorage under `aroundyou.http.token`, then reload. Never put Meta/Modal credentials in frontend variables or browser storage. This is development identity integration, not production login. HTTP mode never falls back to demo writes or identity switching. Draft selection is per browser identity; My Events can resume a selected draft. Manual initial stage/work controls are available; advanced plan fields are supported through the API. Unsupported Groups 3–5 actions fail closed.

Muse Spark has a typed injectable adapter boundary, validated pending proposals and a durable leased execution function; no live HTTP provider transport is configured. The standalone CLI worker currently consumes memory work only. Controlled fake adapters are test-only and report no live model execution. No live Meta or Modal calls were made. Context understanding, stage/work proposal and governance requests return unavailable without an injected adapter. API keys alone do not configure one. Pending-run polling is bounded; full reconnect/resume UX remains future work.

Governance documents store references/metadata, not uploaded bytes. Reminder preferences and invitation drafts do not send notifications. Scheduled publication intent is stored but no scheduling service is connected. Resources are reported requirements, not verified stock. Publication returns the existing eight-tab public projection with private data removed, not fabricated operational updates. Large plan memory projections contain bounded cited facts/counts; full immutable originals and digests remain authoritative.

Final Group 2 verification: 75 backend tests passed on isolated PostgreSQL 16.11, including the original 44. Frontend and demo results are recorded in the implementation report. Browser screenshots/live end-to-end HTTP interaction were not verified. The upstream TestClient deprecation and Vite large-chunk warnings remain non-failing.


## Group 2 Prompt 2 correction

Migration `0003_context_snapshots` adds immutable context snapshot content to the existing context revision table (still 21 tables). Original text remains complete; clarification rounds, supplied brief facts and exact confirmed interpretation are versioned with source hashes. Acknowledgement-only edits do not discard accepted meaning. Material brief changes have an explicit context-details revision command and invalidate derived confirmations; old published releases remain immutable. Legacy rows retain empty snapshots rather than fabricated review history.

The existing HTTP context screen now supports structured clarification answers/history, manual completion, proposal recovery/refresh and exact acceptance/rejection. Governance presents pending advice for human review and supports internal open/in-review/waiting-for-documents/closed follow-up. A closed ticket never means external approval. Recommendations distinguish conditional/advisory/unknown/not-applicable classifications. Verified external requirements/rule citations are rejected because no trusted external evidence verifier exists in this group. Documents remain private references only; reminders are preferences without a sender.

Provider input includes organizer-reported event facts, confirmed meaning, planned work and reported setup separately from applicable memory; emergency contacts are omitted from the setup context. Memory eligibility is rechecked at human acceptance and when displaying current governance advice. A bounded worker deadline discards late provider results; a future real network adapter must additionally enforce its transport timeout/cancellation. Timed-out daemon calls have no database session or business mutation tools. No live Meta or Modal calls were authorized or made.

The opt-in service exposes only the existing scoped development identity boundary; running application DB setup remains blocked until DATABASE_URL has real intended local credentials. Do not point the isolated test runner at that database. See `../docs/implementation/group2-prompt2-implementation-report.md` for exact APIs, verification, limitations and files changed. The exact prompt and resumable checkpoint are saved beside that report.

## Group 3 runtime and limits

Migration `0004_participation_support` adds 13 tables (34 total) for private applications and immutable revisions, exact assignment terms and consent, organizations and support history, verified receipt/correction/reservation accounting, and operational memory sources. See `../docs/implementation/group3-implementation-report.md` and `../outputs/backend-group3/openapi.json` for implemented scope and contracts.

The opt-in HTTP adapter now connects Group 3 participation/review/consent, My Events/workspace projections, organization support and resource views. Existing frontend/demo behavior and fixtures remain available in demo mode. HTTP mode does not mix in demo records. Execution reporting, meetings, updates and blocker recovery remain unavailable backend features for Group 4; no consumption, attendance or completion commands were added. Funding intents/references are not payment settlement or physical inventory. Organization registration remains self-declared and unverified.

Participation/resource intelligence reuses the existing scoped, version-bound durable AI proposal workflow. Only explicitly non-live test adapters were executed. A real transport and continuous AI worker deployment remain future integration work; model credentials alone do not enable inference. No configured application DB migration or browser walkthrough was performed in Group 3.

## Group 4 execution and private evidence

Migration `0005_execution_evidence` adds nine tables (43 total). Execution, original report revisions, human review, scoped stage-review grants, attendance claims/review, typed work issues, coordination records and resource consumption/custody now have backend APIs. Existing frontend screens use these through opt-in HTTP mode; fixture demo mode is preserved. Recovery candidates and activation remain Group 5 and unavailable.

Optional real-byte development storage is configured using `EVIDENCE_DIRECTORY` on the backend or an injected `PrivateObjectStorage` implementation. Use a dedicated private absolute directory outside all web roots; `public`, `static` and `dist` locations are rejected. Do not use frontend environment variables for private paths or credentials. Without configured storage, upload returns `storage_unavailable`; metadata/text reporting remains available. Objects use server-generated opaque basenames and authenticated attachment downloads, bounded upload size/type/signature/hash checks and explicit human inspection. Uploaded bytes are not automatically verified, virus-scanned, transcribed or interpreted by AI. Local storage relies on the backend host's filesystem permissions; cloud storage, encryption-at-rest/key management, orphan cleanup and multi-host deployment are not provided here.

A participant submits only their own current accepted work/terms. Original private drafts remain private until submission. Uploaded originals may be submitted pending inspection; human acceptance for review is required before report verification. Human verified progress, final work completion, stage completion, attendance and resource reconciliation are separate operations. Report corrections append source revisions. Media retraction invalidates affected verified work and measurements. No external notifications, actual calls, GPS proof, live Muse Spark or Modal inference is claimed. The execution AI port receives metadata/text only and produces pending observations, not operational authority.

See `../docs/implementation/group4-implementation-report.md` and `../outputs/backend-group4/` for final actual verification and limitations. Configured application DATABASE_URL remains a separate unresolved setup step; do not migrate it while placeholder credentials remain.
