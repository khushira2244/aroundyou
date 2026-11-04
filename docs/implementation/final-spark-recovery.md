# Final Spark recovery integration

2026-11-03. One authorized live Muse Spark request executed successfully. No Modal inference, deployment, extra paid request, database reset or frontend redesign.

## Reused and changed

Reused existing human blocker confirmation, PostgreSQL plan/dependency impact, recovery workspace/local reviews, resource and assignment projections, scoped memory retrieval, Meta transport, durable AI runs/pending proposals, source-version checks, overall approval/activation, participant consent and notification/meeting coordination.

RecoveryAdvice now supports zero to three alternatives (the provider is asked for at most two), questions, existing work schedules, scoped patches to stage/work/resource/actor requirements, trade-offs and affected reconfirmation work IDs. It does not introduce another recovery engine. Existing patch allowlists deny IDs, inventory, units, permissions, assignments and qualification verification changes. Schedule/dependency/stage-window and quantity checks run through existing PlanContent and individual node validation against a full authoritative plan retained server-side, while the model receives the scoped subset. Shared actor/resource edits require all linked work in the affected scope. Existing completed/unaffected nodes cannot be edited. Capacity/stock sufficiency is explicitly conditional; AI advice cannot establish either.

The provider receives authorized historical-memory context explicitly for recovery. Strict retrieval admits reviewed, applicable records with original-source permissions and current provenance; synthetic lesson candidates remain excluded. No eligible approved history existed in the live scenario, so memory count was zero. Positive authorized cross-event retrieval and negative authorization/source-correction behavior were verified by existing PostgreSQL tests, not fabricated live history.

In the existing workspace, an organizer can load a selected suggestion's fields into the selected local editor, inspect/edit them, and then explicitly save/confirm each local review. Loading does not persist or approve changes. Dismiss returns to the manual path; it is a local UI dismissal, not a persisted proposal rejection. Existing advice review and recovery approval services remain authoritative. Overall recovery submission, participant reconsent and activation still use the established deterministic workflow.

## Genuine live result

The HTTP harness used real signup-independent authenticated identity, local Uvicorn/FastAPI and configured development PostgreSQL. It created a new explicitly synthetic education verification event with stored work/resource/actor requirements and a confirmed resource blocker. Existing data/fixtures were not reset. A durable exclusive provider-call marker prevents another paid request.

Event `a1d5a93d-6227-4664-b5b9-4b7c95506c49`; run `6c9bdccb-05fb-4b84-982b-17dced387625`; pending proposal `e1ca37ff-959e-4f6e-9d73-1d25c005f37c`. Configured model and response model: `muse-spark-1.3`. Genuine successful Meta chat-completions transport and structured response; request ID `chatcmpl-01a1a088-7459-75dd-8f16-ce97f04a6a20`. No automatic provider retries; job has one attempt.

Actual validated payload contained **zero alternatives and three questions**: whether the organizer checked missing workbooks, the verified on-hand quantity against ten required books, and whether work should remain on hold without rescheduling pending review. Referenced actual work `efe4aa31-cca5-40d2-8c9a-d0aeaf3b47fa`, resource `193ffa2d-c921-4afd-8e59-de778c220cca`, stage `0d235e57-f7cc-4b6e-8144-3ce4d163f704`, issue `f5bec95f-c967-4cb7-a56b-552fe9e1e3a3`. No actor edit or claimed available stock was returned.

This is successful missing-information handling, **not a live demonstration of a feasible changed-plan alternative**. No alternative was rejected because none was proposed; invalid/unrelated changes were tested offline. Schema validation, source/fingerprint validation and pending persistence passed. Human decision remains required; plan ID unchanged. Manual recovery workspace `ff6c35e2-47d4-4f8a-9958-ec923bd1e4a9` opened successfully afterward through actual HTTP. No recovery activation or authoritative modification occurred from the model.

Provider usage: 2,931 prompt tokens, 961 completion tokens (770 reasoning), total 3,892; zero cached tokens. Exact billed dollar cost was not exposed by this response and is not claimed. The successful response/metadata and local verification summary are retained in ignored `backend/.tmp/final-recovery-spark-result.json`; no API key is logged. Modal automatic integration remains disabled and no Modal calls were made.

## Verification and limitations

Initial isolated PostgreSQL run: 50 existing tests passed; the new test had a missing fixture import. Corrected import and reran the focused validator test: one passed. Thus 51 tests passed across the final existing-plus-corrected runs. Covers single-work/multi-stage impact, unrelated preservation, stale/unauthorized scope, human local/overall review, participant consent, manual fallback, notifications/meetings and memory permissions. New test checks questions-only output, valid scoped work patch and rejection of unrelated IDs, assignment-like fields and negative resource quantities. No validation was weakened.

Frontend: seven relevant recovery/workspace/organizer tests passed; production TypeScript/Vite build passed, including the final editor-load change. Existing bundle-size and dependency deprecation warnings remain. Browser visuals and the new load-button interaction were not browser-verified. No live multi-layer changed-plan candidate or positive real historical-memory retrieval was available in this single call. No broad resource-constrained feasibility claim is made.

Deployment readiness: the bounded reasoning/pending-review path is verified, including honest no-feasible-answer handling. Full product deployment readiness is **not certified** by this test: specialized multi-layer live alternatives and browser acceptance remain unverified, alongside previously documented Prompt 7 limits. Do not start Prompt 8 automatically.

Commands:

```powershell
$env:TEMP="$PWD/backend/.tmp"; $env:TMP=$env:TEMP
backend/.venv/Scripts/python.exe backend/tools/run_postgres_tests.py tests/test_final_recovery_ai.py tests/test_prompt7_workspace.py tests/test_group5.py tests/test_group5_resume.py tests/test_group1.py -q
backend/.venv/Scripts/python.exe backend/tools/run_postgres_tests.py tests/test_final_recovery_ai.py -q
backend/.venv/Scripts/python.exe backend/tools/verify_final_recovery_spark.py
# From frontend:
npm test -- --run tests/prompt7-workspace.test.tsx tests/recovery.test.tsx tests/organizer-dashboard.test.tsx
npm run build
# From repository root:
git diff --check
```

The live harness initially stopped on a missing Event import before any provider call; corrected and executed once. Changes: `backend/app/recovery/advisory.py`, `backend/app/ai/service.py`, `backend/app/ai/meta_provider.py`, `frontend/src/features/recovery/RecoveryWorkspace.tsx`; added `backend/tests/test_final_recovery_ai.py`, `backend/tools/verify_final_recovery_spark.py` and this report. No migration, credential change, infrastructure deployment or unrelated feature work.
