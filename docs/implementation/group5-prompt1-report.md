# Group 5 implementation checkpoint â€” PARTIAL

Group 5 is not complete. This document records the implemented foundation and the outstanding assignment, not acceptance of either full workstream.

## 1. Recovery contracts
Authenticated organizer POST `/v1/events/{event_id}/recovery/impact` takes `issue_ids` and `expected_plan_id`. POST `recovery/issues/{issue_id}/confirm` takes `expected_revision` and `reason`, with event If-Match/idempotency headers. Confirmation appends an immutable execution revision and existing audit/outbox lineage. Later issue reviews invalidate confirmation. Acknowledgment alone is insufficient.

## 2. Deterministic graph
Pure work/stage dependency closure rejects unknown references, duplicate identifiers and cycles, including mixed stage/work cycles. Output separates direct, downstream, unaffected and verified complete work and carries schedule/resource/skill/condition references and digest. It establishes impact only; capacity, resource feasibility and scheduling are not established. No work is cancelled or mutated.

## 3â€“5. Recovery transitions, reconfirmation and activation
NOT IMPLEMENTED: persisted investigation/alternatives, typed recovery model runs, deterministic alternative feasibility, digest-bound human option decisions, revised assignment offers/consent and atomic plan activation. The impact response explicitly says activation unavailable. Existing Group 1â€“4 version/consent behavior is unchanged.

## 6â€“7. Memory and models
Existing event-only memory retrieval remains intact, but recovery-context retrieval and recovery outcome projection are NOT wired. No provider calls, GPU deployment, paid worker or credentials changes. No fictional alternatives or success claims.

## 8. Insight documents
Event-specific structured single-choice questions support stable IDs, bounded choices, required/enabled/aggregate flags, labels/descriptions and configuration revision. Organizer configuration uses exact revision and event version/idempotency checks. Responses store exact configuration version and explicit consent separately from assignment consent. Own response GET and revocation DELETE are available. Originals remain immutable in the existing operational_sources journal; no recovery tables contain demographic answers. Changing configuration conservatively excludes older responses rather than reinterpreting choices. No new migration or tables yet; 0005/43-table baseline remains.

## 9. Privacy
Server derives accepted people from current effective assignments, one contribution per account, and separately recorded explicit insight consent. Every released bucket and population require five eligible people; small missing-response complements suppress the entire dimension. Arbitrary combined filters return suppressed without counts. Configuration public_aggregates gates release. Only the author can read their raw response through these APIs; generic memory/source resolution rejects all insight documents. No precise DOB or unrestricted text demographic categories. This is conservative suppression, not a formal differential privacy guarantee; longitudinal differencing resistance remains unresolved.

## 10. Frontend
Existing React design, HTTP adapter and synthetic fixtures are untouched. New dynamic APIs are NOT wired to settings, application flow or six-tab modal yet; the existing legacy aggregate projection still serves those views. Recovery screens are NOT connected to the new impact endpoint. These are outstanding Group 5 requirements, not tomorrow-only polish.

## 11. Files and schema
See outputs/backend-group5/files-changed.txt and file-manifest.json. Existing immutable operational_sources and execution_revisions are reused. No migration beyond 0005.

## 12. Verification
See outputs/backend-group5/verification.json and raw artifacts for actual results. Initial focused run passed 3 tests on isolated real PostgreSQL. Full backend regression: 132 passed against real isolated PostgreSQL. Final focused run: 5 passed (overlapping, includes latest exact-condition confirmation). Demo: 146 passed. Build including TypeScript: passed. Compileall and pip check passed. Initial frontend suite: 66 passed, 6 failed (five timeouts and one missing-element assertion); single-worker full rerun: 71 passed, 1 failed (40-second ten-participant replay timeout). No frontend code changed; no claim that the full frontend suite passed. Browser/provider tests unperformed. Commands: `backend/.venv/Scripts/python.exe backend/tools/run_postgres_tests.py -q --tb=short --junitxml=../outputs/backend-group5/backend.xml`; focused run substitutes `tests/test_group5.py` and `focused-final.xml`; frontend cwd `node node_modules/vitest/vitest.mjs run --reporter=json --outputFile=../outputs/backend-group5/frontend.json`; rerun adds `--maxWorkers=1 --testTimeout=30000` with `frontend-final.json`; `npm run build`; root `node --test --test-reporter=tap demo/tests/*.test.mjs`; Python `-m compileall -q backend/app backend/tests` and `-m pip check`.

## 13â€“14. Runtime limits
No browser or screenshot test, configured application DB migration, private evidence production storage, production identity or live provider verification. Existing DATABASE_URL placeholder and EVIDENCE_DIRECTORY configuration requirements remain unchanged. No secrets were read into this report or overwritten.

## 15. Integration sequence
Finish Group 5 recovery candidate/validation/reconfirmation/activation tests; add recovery memory/context/outcome wiring; connect dynamic configuration and answers through AroundYouService to existing forms/modal; verify complete required scenarios and concurrent activation rollback. Then separately address tomorrow's explicitly reserved frontend scope.

## 16. Not delivered / resume boundary
Both full workstreams remain partial. No landing-page redesign, My Events redesign, external deployment or live inference was started. Resume from this checkpoint and the saved exact group5-task.md; do not treat this as Group 5 completion.

The ten-participant test file passed its isolated final rerun; see frontend-targeted.json. The earlier full-suite timeout is retained in the evidence.
