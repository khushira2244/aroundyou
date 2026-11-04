# Prompt 3 — selected-stage correction

Date: 2026-11-03. Local implementation and approved three-call live verification complete. Browser visual verification remains outstanding.

## Root cause and correction

The frontend selected a stage visually, but HTTP generation omitted that stage ID and requested work for all stages. The previous large schema also asked the model to invent identifiers and links, contributing to invalid windows, excessive output and the runaway zone reference. Earlier requests additionally encountered a 28-second timeout.

Work and actor requests now carry `stage_id`. The API validates membership in the selected event and confirmed stage structure. Actor generation requires that particular stage's confirmed work. Context contains the selected stage, its schedule and predecessor stages, selected-stage work, relevant resource demands, reviewed governance, event context and stage-filtered conversation history. The whole plan is retained server-side for validation and merging, not sent as a work-generation request.

The small Work Design schema allows 1–6 work units (instructions recommend 1–4), with objectives, outcomes, explicit schedules, skills, conditions, evidence and resource demand. It contains no generated stage/group/zone/resource IDs. Backend IDs derive from the run and stage; local dependency positions become actual work IDs. Duration derives from the exact submitted schedule. Timezone, stage windows, graph references, cycles and precedence remain validated. No schedule is repaired merely to pass validation. Existing shared cross-stage dependencies/resources/roles require explicit manual review before destructive replacement.

Actor output references only selected-stage work. Backend code derives stable role IDs and exact source-work windows. Coverage is mandatory. The model estimates demand and capabilities, never recruited participants. Applying either proposal preserves other stages' work, groups, resources and requirements.

Migration `0009_stage_reviews.py` adds `planning_drafts.stage_reviews`, storing separate work and actor confirmation fingerprints per stage. Existing confirmed drafts retain compatible legacy confirmation semantics. Subsequent changes invalidate only affected fingerprints. Global work/actor flags become true only when all stages have valid respective confirmations. Existing immutable snapshots, reviews, audit and expected-version checks remain in use.

## Frontend

- Existing Work Design generation, questions and confirmation send the selected stage ID.
- Existing actor stage-name buttons are accessible tabs backed by PostgreSQL stage IDs. Selection filters roles, proposal review and conversation history. Generation and confirmation are per stage.
- Selecting a different stage no longer keeps displaying the previously selected role.
- Existing planning assistant provides stage-aware advisory chat; questions do not mutate work or timing. Saved history is read without inference.
- Existing Gantt, manual editing and explicit stage recalculation remain. Stage moves preserve work intent and surface stale timing.
- No new dashboards, demo data or unrelated workflow changes.

## Database and verification

Development PostgreSQL was reachable and verified at migration `0009`; `python -m alembic upgrade head` completed. No reset or fixture changes. The existing private live-verification event still has its three confirmed stages. After explicit user approval, exactly three new paid requests ran successfully, with zero automatic retries.

Commands from `backend` (`TEMP` and `TMP` set to `backend/.tmp`):

```powershell
.venv/Scripts/python.exe tools/run_postgres_tests.py tests/test_stage_scoped_planning.py tests/test_prompt3_planning.py tests/test_group2.py tests/test_meta_provider.py -q
```

49 tests passed against isolated real PostgreSQL. The harness subsequently timed out during database shutdown; a later `pg_ctl status` confirmed that isolated server was no longer running. This is a harness cleanup failure, not an assertion failure. The first attempted invocation before local network permission was granted could not connect and did not execute tests.

After the final scope/error tests and timezone validation:

```powershell
.venv/Scripts/python.exe tools/run_postgres_tests.py tests/test_stage_scoped_planning.py -q
```

2 tests passed, command exit 0. These exercise two stages independently, preserve the first stage byte-for-byte when generating the second, persist confirmations, invalidate only edited-stage reviews, reject missing/foreign stage IDs, reject invalid stage windows and cross-stage actor work references, and prove saved reads do not invoke the offline provider. Offline adapters are test doubles, not genuine inference.

Commands from `frontend`:

```powershell
npm test -- tests/prompt3-planning.test.tsx tests/planning.test.tsx tests/backend-manual-planning.test.tsx tests/http-adapter.test.ts
npm run build
```

12 tests passed; TypeScript and production build passed. After the last selected-stage chat/filter adjustment, the focused `npm test -- tests/prompt3-planning.test.tsx` also passed all 3 tests. The final production build after that adjustment passed. The existing Vite bundle-size and Starlette/httpx deprecation warnings remain. An initial frontend assertion expecting generation without a stage ID was updated to the corrected contract and passed.

## Live and browser status

All three approved real `muse-spark-1.3` calls passed, through authenticated FastAPI TestClient against development PostgreSQL:

| Check | Actual result |
| --- | --- |
| Work Design | Passed. Two work units for `s1_setup`, Venue Access and Safety Setup, within its approved Day 2 window. Applied and confirmed. |
| Actor Requirements | Passed. Two demand-only role requirements covering the selected stage's two confirmed work units. Applied and confirmed. No assignments created. |
| Planning chat | Passed. Advisory answer cited the actual Day 2 schedules, empty dependency lists, staffing demand, unconfirmed resources and governance uncertainty. It distinguished possible parallelism from the currently sequential schedule and applied no changes. |
| Persistence | Repeated reads restored identical saved work, roles and confirmations with no additional inference. Other stages' work/roles remained unchanged. |

Private verification event: `3db4b03a-d8ef-4d15-84b3-a82928bcc6e9`; selected stage: `s1_setup`. Work run: `ee6952d0-912e-4269-82a8-da773ce46098`; actor run: `518dc70b-77dd-42b4-a5c4-ecb3571dc0d3`; chat run: `26db8a6a-66f9-4d93-91d8-c2a257a4c00e`.

Exact approved command from `backend`:

```powershell
.venv/Scripts/python.exe tools/verify_prompt3_stage_scope.py --approved-three-stage-calls
```

Exit 0; exactly 3 calls; provider token usage respectively 3,124 / 3,599 / 4,881 total tokens (11,604 total). No further paid calls ran. Actual billed cost was not queried. Private results and persisted budget are ignored under `backend/.tmp/prompt3-stage-scope-results.json` and `prompt3-stage-scope-budget.json`. Existing Meta credentials and model were preserved.

`backend/tools/verify_prompt3_stage_scope.py` requires a fresh approval flag, enforces a persisted three-call cap, stops on the first failure, and refuses automatic reruns. It uses the existing private verification event and existing credentials/model. Sequence: selected-stage work → apply/confirm → selected-stage actors → apply/confirm → advisory question → repeated persistence reads and other-stage equality checks. It makes no calls on application startup. The previous exhausted six-call budget remains untouched.

Browser visual comparison and browser-to-live-model journey remain unverified. React component tests verify tab selection, correct stage IDs, no automatic generation, advisory separation, and existing Gantt controls. After restarting the updated local runtime, manually open a confirmed event, select a stage, generate/review/edit/apply/confirm its work, open Actor Requirements, select the same named tab, generate/review/apply/confirm requirements, ask a question, refresh and switch stages. The approved live budget is now exhausted; additional paid verification requires fresh approval.

## Files changed for this correction

Backend updated:

- `backend/app/planning/intelligence.py`
- `backend/app/planning/service.py`
- `backend/app/planning/draft_models.py`
- `backend/app/planning/dto.py`
- `backend/app/ai/service.py`
- `backend/app/ai/meta_provider.py`
- `backend/app/api/group2.py`
- `backend/tests/test_prompt3_planning.py` (explicit legacy offline adapter scope)

Backend created:

- `backend/migrations/versions/0009_stage_reviews.py`
- `backend/tests/test_stage_scoped_planning.py`
- `backend/tools/verify_prompt3_stage_scope.py`

Frontend updated:

- `frontend/src/services/http-adapter.ts`
- `frontend/src/services/planning-contracts.ts`
- `frontend/src/features/planning/WorkDesign.tsx`
- `frontend/src/features/planning/ActorRequirements.tsx`
- `frontend/src/features/planning/PlanningAssistant.tsx`
- `frontend/src/features/planning/StagePlanning.tsx`
- `frontend/tests/prompt3-planning.test.tsx`

This report is new. Earlier unrelated checkout changes were preserved. No Organizer/Sponsor, Participation, Execution or Recovery work was started.
