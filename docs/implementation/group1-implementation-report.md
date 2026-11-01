# AroundYou Group 1 — implementation results

Date: 1 November 2026. **Coding delivered; stop after Group 1.**

## 1. Status

The agreed **bounded Group 1 foundation is implemented and tested**: one FastAPI monolith, real PostgreSQL migration/persistence/UoW, signed authenticated identity and event grants, original context/immutable plan/review records, audit/idempotency/outbox/jobs, source-linked deterministic Event Memory, retrieval, corrections/supersession and provider/context ports. This is not a claim that production login, provider deployment, cross-event sharing or Group 2 operational flows are implemented.

Local configured startup is **not ready until the existing short `SESSION_SECRET` is replaced with at least 32 characters**. It was preserved, never printed, and no Meta/Modal secret was changed. The real database URL in `.env` was not migrated or populated. Isolated disposable PostgreSQL was used for all integration tests. Installation/setup/admin/test commands are in [backend README](../../backend/README.md).

## 2. Exact files created/modified

All listed source/config/test files were newly created; `backend/.env` already existed and was not modified. No frontend, demo source, fixture or existing design document was changed. `.gitignore` was added at project root. Environment/runtime/cache/build files are excluded from this deliverable list.

- `.gitignore`
- `backend/.env.example`
- `backend/README.md`
- `backend/alembic.ini`
- `backend/app/__init__.py`
- `backend/app/access/__init__.py`
- `backend/app/access/authentication.py`
- `backend/app/access/authorization.py`
- `backend/app/access/models.py`
- `backend/app/access/router.py`
- `backend/app/ai/__init__.py`
- `backend/app/ai/context_builder.py`
- `backend/app/api/__init__.py`
- `backend/app/api/dependencies.py`
- `backend/app/api/errors.py`
- `backend/app/cli.py`
- `backend/app/events/__init__.py`
- `backend/app/events/models.py`
- `backend/app/events/router.py`
- `backend/app/events/source_revisions.py`
- `backend/app/main.py`
- `backend/app/memory/__init__.py`
- `backend/app/memory/models.py`
- `backend/app/memory/ports.py`
- `backend/app/memory/projections.py`
- `backend/app/memory/repository.py`
- `backend/app/memory/retrieval.py`
- `backend/app/memory/router.py`
- `backend/app/memory/schemas.py`
- `backend/app/memory/service.py`
- `backend/app/memory/worker.py`
- `backend/app/models.py`
- `backend/app/planning/__init__.py`
- `backend/app/planning/models.py`
- `backend/app/planning/schemas.py`
- `backend/app/settings.py`
- `backend/app/shared/__init__.py`
- `backend/app/shared/audit.py`
- `backend/app/shared/database.py`
- `backend/app/shared/idempotency.py`
- `backend/app/shared/jobs.py`
- `backend/app/shared/models.py`
- `backend/app/shared/outbox.py`
- `backend/app/shared/source_resolver.py`
- `backend/app/shared/types.py`
- `backend/app/shared/unit_of_work.py`
- `backend/migrations/env.py`
- `backend/migrations/script.py.mako`
- `backend/migrations/versions/0001_access_event_memory_foundation.py`
- `backend/pyproject.toml`
- `backend/requirements.lock`
- `backend/tests/conftest.py`
- `backend/tests/test_additional.py`
- `backend/tests/test_contracts.py`
- `backend/tests/test_group1.py`
- `backend/tests/test_migrations.py`
- `backend/tools/run_postgres_tests.py`

Additional implementation artifacts:

- `docs/implementation/group1-implementation-report.md` (this report).
- `outputs/backend-group1/files-changed.txt` (complete delivery manifest).
- `outputs/backend-group1/backend-tests.xml` (final PostgreSQL pytest JUnit result).
- `outputs/backend-group1/verification.json` (commands/results/source-preservation summary).

The local `.venv`, editable-install metadata, `.tmp` test database/logs and pytest caches are generated development artifacts, not application source or deployable database state. No real secret is included in this report or manifest.

## 3. Database tables and migration

`backend/migrations/versions/0001_access_event_memory_foundation.py`, revision **0001**, creates these **13 application tables** (plus Alembic's version table):

| Area | Tables |
|---|---|
| Identity/access | `users`, `event_grants` |
| Authoritative originals | `events`, `event_context_revisions`, `plan_versions`, `review_decisions` |
| Infrastructure | `audit_events`, `idempotency_records`, `outbox_events`, `job_tasks` |
| Derived intelligence | `memory_entries`, `memory_sources`, `memory_runs` |

Frozen PostgreSQL DDL includes indexes, uniqueness, checks, same-event composite FKs, immutable original/plan/review/audit/source triggers, and immutable memory-content protection. Memory lifecycle/review versions can change through validated services; assertion content corrections append a successor. Context/plan/decision corrections retain originals. The migration is reversible and does not import fixtures or dynamically create tables on application startup.

Database tests executed upgrade -> metadata/schema comparison -> downgrade -> empty-schema assertion -> upgrade -> repeat upgrade, against a separate real PostgreSQL migration database. Business tests use a second disposable PostgreSQL database. No SQLite substitution was used.

## 4. API endpoints actually implemented

These routes are exercised with FastAPI TestClient backed by real PostgreSQL. Not deployed to the frontend or a public server. `/docs` and `/openapi.json` are available when launched with valid settings.

| Method/path | Actual behavior |
|---|---|
| `GET /health` | Public process-health response; not a DB/provider readiness guarantee. |
| `GET /v1/me` | Validated bearer identity, active database user only. |
| `GET /v1/events/{event_id}` | Authorized minimal event identity/version and permitted source pointers. |
| `GET /v1/events/{event_id}/sources/current` | Authorized current original context/plan revision IDs and digests. |
| `POST /v1/events/{event_id}/memory/extractions` | Keyed, source-validated durable extraction receipt (202); open-weight unavailable returns 503. |
| `GET /v1/events/{event_id}/memory/extractions/{run_id}` | Permitted job status/result IDs; stale source metadata does not reveal its content. |
| `GET /v1/events/{event_id}/memory` | Eligible published memory with lexical and structured applicability filtering; bounded pagination. |
| `GET /v1/events/{event_id}/memory/{memory_id}` | Authorized eligible exact revision with source citations. |
| `POST /v1/events/{event_id}/memory/{memory_id}/review` | Exact candidate/digest/version decision; publish/reject derived content only. |
| `POST /v1/events/{event_id}/memory/{memory_id}/corrections` | Append a source-linked candidate successor and retire old eligibility. |
| `POST /v1/events/{event_id}/memory/{memory_id}/retract` | Retire derived retrieval eligibility with immutable decision/audit. |

Writes require validated actor/grants, idempotency, exact source lineage and applicable version/digest checks. Transaction dependencies close/commit before the response is sent. Missing/foreign/private records fail closed. No public identity picker, arbitrary CRUD, permission-setting endpoint, plan mutation tool or provider-URL input exists.

The minimal event/source reads are foundation contracts; they are **not** a full canonical-profile/My Events frontend HTTP implementation. `AroundYouService` and all React routing/mock behavior remain untouched. There is no `/me/events` claim in this release.

## 5. Memory functionality actually working

- Deterministic bounded excerpts from real persisted context/plan/observation-decision revisions, with exact immutable IDs, versions, digests and normalized assertion/source links.
- Private-source access independent of event membership; partial stage/work grants do not unlock whole-event memory. Foreign IDs and wrong digests are rejected.
- Distinct candidate/published/superseded/retracted lifecycle; proposed/attempted/verified evidence; unknown/successful/failed/mixed/inconclusive outcome. Human observation-review service can preserve a bounded source-supported success or failure; AI output cannot manufacture that basis.
- PostgreSQL structured conditions/category/tags/work-pattern filters and lexical text ranking. Successful and failed source-backed outcomes remain available under their respective filters; unknowns/conditions are retained. Cursors bind query/event/actor but never confer permission.
- Immediate source correction/review-correction/grant-revocation exclusion at retrieval; background job completion rechecks current sources and permissions, rejecting stale output.
- Memory correction currently accepts **one correcting source per successor**; replacement is candidate until separately reviewed. Physical retention/deletion workflow is not implemented.
- Durable extraction jobs with attempts/backoff, row locking/SKIP LOCKED, leases, fencing and terminal exhaustion. Transactional source outbox dispatch reuses deduplicated extraction; duplicate HTTP/outbox delivery cannot create duplicate jobs for the same extraction identity.
- Persisted extraction and retrieval manifests in `memory_runs`; selected memory revisions/source references retained for context traceability. Audit stores IDs/digests/review/attempt metadata, not provider secrets or hidden reasoning.
- `MuseSparkContextBuilder` assembles and revalidates labeled authoritative-current vs derived-historical memory input. It calls no model and grants no mutation authority.

## 6. Tests executed and real results

| Exact command | Final result |
|---|---|
| `backend/.venv/Scripts/python backend/tools/run_postgres_tests.py -q --tb=short --junitxml=.tmp/group1-results.xml` | **44 passed, 0 failed, 0 skipped**, real isolated PostgreSQL 16.11. |
| `npm test` from `demo` | **146 passed, 0 failed, 0 skipped**, including unchanged ten-participant and blocker-recovery scenarios. |
| `backend/.venv/Scripts/python -m pip install -e 'backend[test]'` (workspace-local TEMP/TMP) | Editable packaging installed successfully. |
| `backend/.venv/Scripts/python -m pip check` | No broken requirements. |
| `backend/.venv/Scripts/python -m compileall -q backend/app backend/tests backend/migrations` | Passed. |
| Source-hash comparison to reviewed frontend/demo baseline | No changes. |
| `git check-ignore backend/.env backend/.venv/pyvenv.cfg backend/.tmp/group1-results.xml` | All three ignored. |

Coverage includes auth signature/issuer/audience/expiry/required claims/inactive users; event/private/foreign/scope denial; provenance/hash validation; unsupported outcome rejection; filtering/empty results/pagination; idempotency and concurrent extraction; rollback and atomic outbox capture; retry/backoff/exhaustion/fencing; source-change-during-extraction; supersession/retraction; observation correction; immutable DB triggers and cross-event FK rejection; fake Modal candidate review; and planning-context invalidation.

Earlier failures were corrected: fixture name shadowed the imported models module; migration comparison initially inspected an older disposable schema without rebuilding it. Final results above supersede those failed attempts. One upstream Starlette/httpx TestClient deprecation warning remains; it is not a failing test. Initial pip temp-directory permission issues were resolved using ignored workspace-local TEMP/TMP. Test server lifecycle is managed inside the test runner and stopped afterward.

No frontend build/browser/screenshot test was run because no frontend code changed. No live Meta/Modal call, actual `.env` database migration, production auth-provider login, or deployment was tested. The isolated PostgreSQL runner is genuine database integration, not an in-memory substitute.

## 7. What remains interface-only or deliberately deferred

- Modal-oriented `ModalExtractionPort`: real typed interface; only a clearly named fake in tests. No hosted model deployment/network adapter. Missing runtime port produces unavailable/failure, not synthetic model success.
- Muse Spark consumer: actual context builder/revalidation, interface-only model execution. Meta credentials were not used.
- External identity provider/OAuth/browser session integration: deferred. Current trusted local administration issues short-lived signed JWTs for pre-provisioned active subjects; no public credential enrollment. Rate limits/individual-token revocation/production hardening remain outside this foundation.
- Cross-event reuse/sharing disabled and explicitly reported, including when requested. There is no private cross-event memory fallback. Sharing/sanitization/retention administration and vector embeddings are later work.
- Execution/evidence/blocker/resource/participation source tables and resolvers await their owning group. Group 1 source types are context, plan and decision; no fake cleanup completion, receipt, attendance or outcome data was seeded.
- Foundation plan manifest supports stable IDs/stage membership/acyclic dependencies, not a resource-constrained scheduler or full existing frontend plan-edit API.

## 8. Group 2 dependencies and stop condition

Group 1 foundation code is complete for this bounded delivery; the developer's actual runtime still needs a sufficiently strong `SESSION_SECRET`, a reachable provisioned application database and explicit migration/admin setup. Production readiness and full frontend/provider integration are not claimed.

Group 2 can build on the UoW/auth/grants/immutable source services and memory ports. Before connecting its frontend commands: agree on production identity/session adapter, extend the strict plan schema to the approved full stage/work/requirements contract, implement generic event creation/draft/confirmation/publication slices with deterministic validation and exact version checks, and add each real source resolver/outbox projection with its owning transition. Human approval/participant consent/resource accounting remain domain services, never memory/model side effects.

Do not start Group 2 automatically. No implementation of its event-creation/publication/participant/resource/recovery business workflows was included here.
