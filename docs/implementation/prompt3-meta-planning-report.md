# Prompt 3 — planning implementation and verification

Review date: 2026-11-02. Status: implemented and locally tested; **full live acceptance remains incomplete**.

## Result and limits

The existing Stage Planning, Work Design, Actor Requirements, Gantt, AroundYouService and HTTP adapter are connected to scoped Muse Spark proposal contracts. No replacement screens, participant fixtures, Modal calls, SAM calls, execution workflows or recovery features were introduced in this task.

Six explicitly bounded live requests were used, with no automatic paid retries. Two succeeded: real stage generation and stage recalculation. Four Work Design attempts failed closed. No invalid work proposal was applied. Actor recommendations and conversational inference were tested offline, not live. The final output-schema correction has not been tested against Meta because the six-call budget is exhausted. This is not a claim of a fully verified live chain.

## Implemented behavior

- Confirmed event context, reviewed governance, current planning versions and permitted relevant memory form model context. The model returns scoped structured advice, not authoritative mutations.
- Stage edits are pending human proposals with deterministic dependency impact. Moving a stage preserves work descriptions and schedules exactly. Out-of-window work is explicitly stale; work confirmation and actor generation reject it until reconciled. Other invalid dependencies remain errors.
- Explicit recalculation uses the pending edit and affected stages. No inference runs on pointer movement, page opening or history reads. Apply and confirmation remain separate human actions, with stale-version protection and immutable snapshots.
- Existing Gantt controls support movement, an end resize handle, keyboard resizing, numeric timing, anchored calendar dates, title/dependency editing and removal. Pointer listeners clean up on unmount. Calendar dates extending past the event brief produce a review warning; event dates are not silently changed.
- Work generation uses confirmed parent stage windows, skills, resource demand, effort, dependencies and evidence expectations. It does not create received inventory or completed work.
- Actor proposals use confirmed work and exact source schedule windows; recommendations represent demand, never committed people. Existing manual editing and confirmation remain available. Empty actor state no longer crashes.
- Existing planning chat separates advisory questions from proposal requests. Saved conversation history is read without inference. Advisory-only answers have no Apply action; proposed stage changes use the normal review mechanism.
- Local memory is optional and filtered for permission, review/provenance and structured applicability. Unavailable or unauthorized memory does not block ordinary planning. No historical success or Modal inference is claimed.

## Endpoints

All paths below use `/v1` and existing authenticated event-scoped validation, idempotency and version checks where applicable.

New:

- `POST /events/{event_id}/planning/actor-proposals`
- `POST /events/{event_id}/planning/conversations`

Reused/extended:

- `GET /events/{event_id}/planning`
- `POST /events/{event_id}/planning/stage-proposals`
- `POST /events/{event_id}/planning/stage-proposals/revisions`
- `POST /events/{event_id}/planning/work-proposals`
- `POST /events/{event_id}/planning/stage-edits`
- `POST /events/{event_id}/planning/arrangements`
- Existing planning item editing, proposal apply/reject, stage/work/actor confirmations and actor requirement editing routes.
- `GET /ai-runs/{run_id}`

## Live verification

Provider: Meta chat completions, `muse-spark-1.3`. Existing private Prompt 2 health-awareness verification event: `3db4b03a-d8ef-4d15-84b3-a82928bcc6e9`. This does not alter the demo scenario fixtures.

1. Stage generation succeeded: three event-specific nonclinical awareness stages, Day 1/2/3. Applied and confirmed in PostgreSQL.
2. A manual first-stage delay generated deterministic downstream dependency conflicts without inference; the active schedule stayed unchanged. Explicit Muse Spark recalculation succeeded, producing Day 2/3/4. Applied and confirmed as a later immutable snapshot.
3. Work attempt rejected for out-of-stage schedules.
4. Work attempt rejected as invalid model output.
5. Work attempt timed out at the then-current 28-second transport bound.
6. Final work attempt reached its 8192-token output limit. Retained private diagnostics showed a runaway generated zone reference consuming the output. No work was committed.

Corrections now in code: explicit required schedule fields and parent-window context, short bounded reference IDs and explanatory lists, instructions against fabricated zones/hash-derived IDs, and a bounded 68-second work transport / 70-second worker deadline. Other requests retain shorter limits. These corrections pass offline tests; they **do not establish live Work Design success**. Future live work/actor/chat verification requires a fresh user-approved budget.

Private diagnostics and six-call counter are under ignored `backend/.tmp/`; credentials were not printed or changed. The three explicit live-test tools share the persisted counter and require an approval flag. They are not application startup hooks.

## PostgreSQL

Verified against real Docker PostgreSQL 16.14. Existing development migration head is `0008`.

Migration `0008_proposal_order.py` adds `ai_proposals.created_at` for stable proposal/conversation ordering. Existing event/context, draft, plan version, AI run/proposal and review infrastructure is reused. Existing rows receive a migration-time timestamp; their exact historical ordering cannot be reconstructed from this new column alone.

The live stage generations and confirmations used the real development database. Backend regression tests used an isolated real PostgreSQL database, not SQLite and not the user's development data.

## Tests executed

From `backend`, with `TEMP` and `TMP` set to `backend/.tmp`:

```powershell
.venv/Scripts/python.exe tools/run_postgres_tests.py tests/test_prompt3_planning.py tests/test_group2.py tests/test_prompt2_integration.py tests/test_meta_provider.py -q
```

51 passed before the final bounded-reference test was added.

Final targeted pass:

```powershell
.venv/Scripts/python.exe tools/run_postgres_tests.py tests/test_prompt3_planning.py tests/test_group2_context_governance.py tests/test_meta_provider.py -q
```

31 passed. Covers scoped stage/work/actor/chat approval and persistence, no inference on reads, manual impact/recalculation, exact work preservation and stale blocking, cross-event permission denial, stale proposals, graph validation, schema bounds, context/governance and provider errors. Model responses in these regression tests are offline test doubles.

From `frontend`:

```powershell
npm test -- tests/prompt3-planning.test.tsx tests/planning.test.tsx tests/backend-manual-planning.test.tsx tests/http-adapter.test.ts
npm run build
```

12 passed; TypeScript and production build passed. Existing Vite bundle-size warning remains.

From `demo`:

```powershell
npm test
```

146 passed, including the existing connected participation and recovery scenarios. Fixtures unchanged.

`git diff --check` passed. The existing Starlette/httpx deprecation warning remains. Early regression failures exposed automatic stale marking of new invalid manual work and an old assertion expecting stage moves to shift work; code was corrected and that assertion updated for the explicit Prompt 3 requirement. A frontend text-encoding/label test failure was also corrected before the final pass.

## Prompt 3 files

Backend created:

- `backend/app/planning/intelligence.py`
- `backend/migrations/versions/0008_proposal_order.py`
- `backend/tests/test_prompt3_planning.py`
- `backend/tools/verify_prompt3_live.py`
- `backend/tools/verify_prompt3_remaining.py`
- `backend/tools/verify_prompt3_final_work.py`

Backend updated:

- `backend/app/planning/schemas.py`
- `backend/app/planning/service.py`
- `backend/app/planning/dto.py`
- `backend/app/ai/meta_provider.py`
- `backend/app/ai/planning_port.py`
- `backend/app/ai/service.py`
- `backend/app/ai/context_builder.py`
- `backend/app/ai/models.py`
- `backend/app/api/group2.py`
- `backend/tests/test_group2.py`
- `backend/tests/test_meta_provider.py`

Frontend updated:

- `frontend/src/services/planning-contracts.ts`
- `frontend/src/services/http-adapter.ts`
- `frontend/src/features/planning/StagePlanning.tsx`
- `frontend/src/features/planning/WorkDesign.tsx`
- `frontend/src/features/planning/ActorRequirements.tsx`
- `frontend/src/features/planning/PlanningAssistant.tsx`
- `frontend/src/features/planning/Timeline.tsx`
- `frontend/src/features/planning/PlanningLayout.tsx`

Frontend created: `frontend/tests/prompt3-planning.test.tsx`. This report is also new. The checkout contains earlier unrelated changes; they were not reverted or attributed to Prompt 3.

## Manual browser verification remaining

Full browser-to-running-server-to-provider verification, screenshot comparison, mobile layout, actual pointer drag/resize and browser refresh/back were not verified. Component tests and TestClient persistence do not substitute for these checks.

1. In normal Windows PowerShell at the repository root, run `./backend/tools/start_live_runtime.ps1` to start/reuse the local runtime. Use the exact API URL it reports; do not stop an unrelated occupied port. Existing processes must load the updated code.
2. Open `http://127.0.0.1:5173`, sign in as your organizer and open an event with confirmed context. Opening it should only read saved data.
3. Inspect existing saved stages. Move/resize one, inspect the pending edit and affected-stage conflicts, then apply only a valid reviewed proposal. Refresh and verify the saved timing. Confirm work remains unchanged and timing conflicts are visible.
4. A future explicitly approved live test can request stage recalculation, review/apply/confirm it, then generate Work Design, review/apply/confirm it, generate Actor Requirements and review/apply/confirm them.
5. Ask an advisory planning question, verify no schedule change, revisit saved history and refresh without a new model request.
6. Test dependency edits, rejection, stale proposals in a second tab, keyboard resizing and tablet/mobile layout. The full live Work Design/actors/chat sequence remains an acceptance item, not a passed test.

Stopped at Prompt 3. No participation, sponsorship, execution, recovery or deployment work begins automatically.
