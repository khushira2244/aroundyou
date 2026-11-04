# Prompt 7 implementation and verification

Review date: 2026-11-03. Status: **partially complete**. No paid model calls, model downloads, Modal deployment, cloud deployment, or Prompt 8 work were performed.

## Implemented

- Typed personal, resource, dependency, venue/access, safety and equipment issues. Reported claims do not change inventory or become confirmed blockers automatically. Personal descriptions are limited to the reporter and organizer. Protective holds remain separate from ordinary reports.
- Deterministic impact calculation uses actual work/dependency links. Scoped stage/work/resource/actor edits persist in the existing coordination store. Local confirmation does not activate a plan. Final submission requires every scoped node reviewed and full candidate validation; existing version checks, overall human approval, participant consent and atomic activation remain authoritative.
- Event-specific workspace/node query parameters support reload and return navigation. Exact affected accepted participants, delegated stage leads and accepted resource sponsors are derived from records. Targeted notifications use a recipient-authorized inbox. Meetings reuse the existing coordination module and link back to the recovery workspace. These are in-app records, not external message delivery.
- Organizer access to issue-linked original media is restricted to those exact assets; it does not disclose the participant's entire draft report.
- Recovery outcome recording requires activated recovery, independent reviewed evidence covering changed work and separate completion records for successful outcomes. Approval and activation alone cannot manufacture success.
- A narrow optional Modal extraction adapter validates HTTPS endpoints, proxy authentication, pinned model identity, bounded source/output size, source IDs and exact quoted excerpts. Candidates remain pending human review. Human edits preserve source assertions, and published reusable lessons require explicit real-event provenance. Synthetic events cannot be promoted into real lessons.
- Cross-event retrieval requires authorization for both target and original source events, including private-source permissions, plus applicability filtering. Source corrections invalidate derived outcomes/memories. Muse Spark context includes scoped recovery state and authorized memory manifests; AI never commits plans.
- Sponsor headers retain the Sponsor Portal and omit personal My Events.

## Database and HTTP

Migration `0010`, following `0009`, adds `events.memory_data_class` with `unclassified`, `real`, `synthetic` constraint. Existing events default to unclassified. Existing memory, coordination, immutable plan, source revision, job and audit tables are reused; there is no separate memory database.

New `/v1/events/{event_id}` routes: `POST /recovery/workspaces`, `GET /recovery/workspaces/{id}`, `POST /recovery/workspaces/{id}/local-review`, `/submit`, `/communication`; `POST /recovery/alternatives/{id}/outcome`; `POST /memory/data-class`. Added `GET /v1/notifications`, pending memory candidate listing and version-checked candidate editing under the existing memory router. Existing recovery approval/activation/consent and memory review/correction routes are reused.

Real HTTP verification created synthetic event `01b19638-0f30-47ff-af9f-cfc51bde2354` in the configured development PostgreSQL database. Signup/signin, accepted commitment, private issue, human blocker confirmation, local review/reload, linked meeting/RSVP/inbox, overall approval, deferred activation, participant consent, activation, independent outcome persistence, synthetic provenance rejection and unconfigured Modal rejection passed. Provider calls: **0**. Migration head: **0010**. No fixture reset or existing event transfer occurred. An earlier verification-only event's invalid internal draft metadata was repaired after it exposed a strict-form validation error; provenance now uses the dedicated column.

## Verification commands

From repository root (PowerShell):

```powershell
$env:TEMP="$PWD/backend/.tmp"; $env:TMP=$env:TEMP
backend/.venv/Scripts/python.exe backend/tools/run_postgres_tests.py tests/test_prompt7_workspace.py tests/test_group5.py tests/test_group5_resume.py tests/test_group1.py tests/test_group4.py -q
backend/.venv/Scripts/python.exe backend/tools/verify_prompt7_http.py
```

PostgreSQL tests: **70 passed**, one dependency deprecation warning. The test runner uses an isolated native PostgreSQL 16 test database, not a SQLite substitute. The HTTP tool additionally used the configured development PostgreSQL database. Earlier runs found and corrected a missing Literal import, strict draft metadata misuse and an offline job retry regression; final selected backend tests pass.

From `frontend`:

```powershell
npm run build
npm test -- --run
```

Production build passed (TypeScript included). Vite reports the existing bundle-size warning. Full frontend suite: **99 tests passed across 33 files**, including existing ten-participant and blocker-recovery scenarios. Focused Prompt 7/workspace/recovery/media tests also passed: 12 tests. Build commands initially issued from the repository root failed because package.json belongs in frontend; corrected commands above passed. `git diff --check` passed with line-ending warnings only.

Python compilation of app and Modal preparation files passed; that verifies syntax, not Modal runtime compatibility. No automated screenshot comparison or live browser visual acceptance was performed.

## Modal deployment preparation — approval still required

Prepared checkpoint: `Qwen/Qwen2.5-1.5B-Instruct`, revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, Apache-2.0. Planned T4 GPU, 2 CPU, 8 GiB host RAM, one container/input, zero minimum containers, 30-second scale-down window, 120-second timeout, zero retries. Input <=4096 tokens and output <=768 tokens. Estimated FP16 weight storage ~3.1 GB; estimated total GPU use ~5–8 GB is **unbenchmarked**. Cold start includes package/model download and load; latency is unknown.

Published T4 price checked at $0.000164/sec: 30–120 GPU seconds approximately $0.00492–$0.01968, plus CPU/RAM, cold-start and idle-tail charges. This is an estimate, not a billing cap. Credits, expiry and workspace billing eligibility were not verified.

The local backend environment does not have the Modal SDK installed. The prepared deployment has not been imported with the SDK, deployed or GPU-tested. After separate approval: install/check Modal SDK, verify intended workspace and billing, deploy `backend/modal_memory/app.py`, create scoped proxy credentials, configure `MODAL_MEMORY_ENABLED`, endpoint and proxy key/secret locally, then run one bounded real-source extraction. Existing CLI management tokens and Meta credentials were not modified. Management tokens are not substituted for endpoint proxy credentials.

Primary sources reviewed: [model card](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/blob/main/README.md), [Modal proxy authentication](https://modal.com/docs/guide/webhook-proxy-auth), [scaling](https://modal.com/docs/guide/scale), [pricing](https://modal.com/pricing).

## Remaining limits

- No live Prompt 7 Spark recovery or Modal extraction has been verified. Modal parsing tests use an explicit mock transport. Manual recovery works without either provider.
- Spark recovery suggestions currently use the existing schedule-oriented schema; arbitrary stage/resource/actor AI patches and one-click proposal import are not implemented.
- Local draft editing uses structured fields/JSON within the existing hub, not specialized visual editors. A source change makes the workspace stale; automatic rebasing of valid local reviews is not implemented.
- Meeting creation, exact invitees, confirmation, RSVP and return navigation work; revising an existing meeting's agenda/schedule through the recovery hub is not yet implemented. Sponsor targeted notices work, but sponsor meeting participation is not supported by the existing participant meeting authorization boundary.
- Event-location changes and generalized assignment splitting are outside the scoped patch contract. New capability requirements fail closed pending verified qualifications.
- Explicit real-event provenance is a human attestation, not independent verification of real-world truth. Outcome evidence and human review remain required.

## Task files

Created: `backend/app/recovery/workspace.py`, `backend/app/memory/modal_adapter.py`, `backend/modal_memory/app.py`, `backend/migrations/versions/0010_memory_data_class.py`, `backend/tests/test_prompt7_workspace.py`, `backend/tools/verify_prompt7_http.py`, `frontend/src/features/recovery/RecoveryWorkspace.tsx`, `frontend/src/features/recovery/RecoveryLearning.tsx`, `frontend/tests/prompt7-workspace.test.tsx`, this report.

Updated: backend `execution/{schemas,coordination,service,projections,evidence}.py`, `api/group5.py`, `recovery/{service,lifecycle,advisory}.py`, `ai/{meta_provider,service,context_builder}.py`, `memory/{service,router,repository,retrieval}.py`, `shared/source_resolver.py`, `events/models.py`, `settings.py`, `main.py`; frontend `features/execution/WorkExecutionDetail.tsx`, `features/recovery/HttpRecoveryPanel.tsx`, `features/organizer/OrganizerMeetings.tsx`, `app/layout.tsx`, `services/{contracts,http-adapter}.ts`. The checkout also contains earlier task changes; this list is not a claim that all currently dirty files were created by Prompt 7.
