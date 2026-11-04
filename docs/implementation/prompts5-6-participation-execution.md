# Prompts 5–6: participation, execution and media integration

Reviewed and tested 2026-11-03. The deterministic connected journey works. Live voice and visual interpretation work; a valid live suitability recommendation and positive SAM geometry remain unverified. Browser acceptance remains outstanding.

## Implemented behavior

- Reused existing applications, organizer review, immutable assignment terms, explicit acceptance/decline and event-specific participant workspace. Approval does not create a commitment.
- Enabled the existing participation AI workflow on the Meta provider and scheduled its existing worker after the explicit HTTP request. Recommendations remain saved proposals; reading them does not call Meta. Capacity, permissions, availability and exact assignment terms remain deterministic.
- Retained six-tab Insights and the existing configured-question, separate-consent and minimum-five aggregation rules. Regression tests cover acceptance eligibility, combined-filter suppression, revocation and configuration lineage.
- Reused execution reports, original private evidence, human progress review, resource accounting, attendance and issues. No AI update verifies progress, stock, completion or an outcome.
- Added explicit private audio transcription and image segmentation/interpretation actions using existing evidence assets and AI-run persistence. Corrected transcripts retain the original machine text and original audio; participants use the reviewed text in their report before submission.
- Added meeting invitee revision before confirmation. Existing meeting schedules, agendas, stage/work references, RSVP, notes and human-approved follow-ups remain in the existing coordination module. No conference hosting or external invitation delivery is claimed.
- Fixed authenticated binary evidence transfers to include the browser cookie session, as JSON requests already do. Preserved page layout and service boundaries.

## API additions / wiring

All media paths are under `/v1/events/{event_id}/media/{asset_id}` and require an authenticated permitted user.

| Method and suffix | Request | Result and authority |
|---|---|---|
| POST `transcription-runs` | `{}` and Idempotency-Key | Own draft audio only; saved machine transcript, run ID/status. No report verification. |
| POST `transcript-review` | `expected_revision`, `text`, Idempotency-Key | Own current draft; saved correction alongside original machine text. |
| POST `segmentation-runs` | `concept`, Idempotency-Key | Reviewer of submitted image report; SAM wire output and normalized boxes, followed by Spark categories, observations, uncertainty and questions. |

`POST /v1/events/{event_id}/participation-assessments` now executes the configured live participation adapter through the existing worker. Existing proposal review and exact assignment APIs remain authoritative boundaries.

`POST /v1/events/{event_id}/coordination/{id}/actions` accepts `revise_invitees` with exact revision and actual accepted participant IDs. Meeting creation forwards optional existing stage/work references through the HTTP adapter.

Inference is explicit, bounded and idempotent. Evidence/report revisions are checked again before an output is saved; inference runs outside the database transaction. Inference failure retains original evidence. No model runs on GET or screen reopening. A process crash can leave a synchronous media run marked running; automatic crash recovery for these media runs is not implemented.

## Verified official model contracts

Official documentation reviewed on 2026-11-03:

- [SAM overview](https://dev.meta.ai/docs/sam/overview)
- [SAM segmentation requests](https://dev.meta.ai/docs/sam/segmenting)
- [Reading SAM segmentation results](https://dev.meta.ai/docs/sam/reading-segmentation)
- [Image understanding](https://dev.meta.ai/docs/image-understanding)
- [Media segmentation](https://dev.meta.ai/docs/media-segmentation)

SAM uses `sam-3.1` with `POST /v1/responses`, one short object concept and the actual private image encoded as an input-image data URL. It is not a general scene-understanding or completion-verification model. Spark receives the same original image plus work/report context and SAM observations through the existing chat-completions transport.

The implementation retains original SAM mask wire records and parses boxes; it does **not** decode or render raster masks. Explicit image analysis currently accepts at most 2 MB and 2048 pixels per dimension, although original evidence upload permits larger files. It does not silently resize originals. Voice normalization requires FFmpeg/ffprobe and enforces 60 seconds. Pillow 12.3.0 was installed for validated image decoding; its dependency is declared in pyproject.toml.

## Actual live verification

Exactly four billable requests were attempted, with a persisted four-request guard and no automatic paid retries:

1. Muse Spark suitability: response received but rejected by existing provenance validation. It quoted plan/role statements as supporting applicant statements. No recommendation was applied. The prompt now explicitly prohibits that mistake; the corrected prompt has **not** been live retested.
2. Muse Voice: succeeded; original audio, machine transcript and participant correction persisted.
3. SAM 3.1: request completed, but returned zero parsed boxes and zero mask records for the genuine 736×736 locality reference image. This does not establish successful positive object detection. Nonempty geometry handling is tested with an explicitly fake offline response only.
4. Muse Spark image interpretation: succeeded against the genuine original image and work context. Categories included missing/unclear evidence and potential issue; this was not treated as proof of education work or progress.

The under-$1 estimate was not a billing cap. Actual dollar billing was not independently verified. No Modal or recovery inference was invoked.

The new synthetic verification event is `1bae104c-9bbd-42b6-a234-039136ef85ab`. Its description identifies integration verification, not a genuine activity. A synthetic human review recorded 20% strictly to test state transitions; it is not evidence of an actual community outcome. Existing events and demo fixtures were not reset or overwritten.

Actual loopback HTTP checks against the configured development PostgreSQL covered signup/signin, publication, application/review, exact accept and decline, restored My Events, original-byte upload/download, unauthorized evidence denial, saved voice/image analysis, human report review, meeting confirmation, invite revision, RSVP, notes, follow-up approval, attendance and issue acknowledgement. The first script stopped on an invalid test severity (`minor`); the deterministic follow-up used the existing supported `delayed` enum and completed without further inference.

Database migration head is `0009`; no new migration or database architecture was needed. Evidence bytes live in ignored local private storage; metadata, model runs, execution revisions and decisions live in PostgreSQL. Existing credentials were preserved.

## Commands and outcomes

From `backend` (TEMP and TMP set to the workspace `.tmp` directory):

```powershell
.venv/Scripts/python.exe tools/run_postgres_tests.py tests/test_group3.py tests/test_group4.py tests/test_prompt56_media.py -q
.venv/Scripts/python.exe tools/run_postgres_tests.py tests/test_prompt56_media.py -q
.venv/Scripts/python.exe tools/run_postgres_tests.py tests/test_group3.py tests/test_group4.py tests/test_prompt56_media.py tests/test_group5.py -k 'not recovery and not impact and not graph and not stage_dependencies' -q
.venv/Scripts/python.exe tools/verify_prompt56_http.py
.venv/Scripts/python.exe tools/verify_prompt56_followup.py
```

The initial test command passed 26 tests and hit two new-test fixture import errors. After correcting that import, the two new tests passed. Final PostgreSQL command: **30 passed, 4 deselected**, including the additional inference-failure retention test. These regression tests use an isolated real PostgreSQL 16 cluster, not the development database. The HTTP scripts separately used the configured development database and preserved its data. The live script returned nonzero on the test severity error; the deterministic follow-up passed. Do not rerun the live script expecting more calls: its persisted budget is exhausted.

From `frontend`:

```powershell
npm run build
npm test -- --reporter=dot
npm run build
npm test -- tests/prompt56-media-http.test.ts tests/http-group4.test.ts tests/participant-workspace.test.tsx tests/dynamic-insights-http.test.tsx
```

Full frontend suite: **95 passed across 31 files**. After the final cookie-transfer fix and new regression test, production build/typecheck passed again and **11 focused tests passed across four files**. Existing bundle-size warning remains. `git diff --check` passed (only existing Windows line-ending notices).

## Files created or changed for this task

Backend:

- `backend/app/ai/meta_provider.py`: participation provider support and stricter applicant-quotation instruction.
- `backend/app/api/group3.py`: explicit participation-run background execution.
- `backend/app/api/group4.py`: real media route replacement and truthful explicit-provider availability.
- `backend/app/execution/media.py`: new private source-linked media inference and correction endpoints.
- `backend/app/execution/coordination.py`, `schemas.py`: exact meeting invitee revision.
- `backend/app/main.py`: media router registration.
- `backend/pyproject.toml`: Pillow dependency.
- `backend/tests/test_prompt56_media.py`: offline provider, original-byte, provenance, permission, idempotency, correction, human authority and failure retention tests.
- `backend/tools/verify_prompt56_http.py`, `verify_prompt56_followup.py`: bounded live and deterministic real-HTTP verification.
- Local ignored `backend/.env`: private EVIDENCE_DIRECTORY only; existing secrets preserved. Ignored `.tmp` files retain test results/budget and original evidence.

Frontend:

- `frontend/src/services/execution-contracts.ts`: explicit media operations/provider state.
- `frontend/src/services/http-adapter.ts`: media endpoints, cookie binary transfers, meeting invitee updates and reference forwarding.
- `frontend/src/features/execution/EvidenceAttachments.tsx`: explicit analysis and reviewed-transcript controls, saved output display.
- `frontend/src/features/organizer/OrganizerMeetings.tsx`: existing draft/proposed meeting and follow-up states.
- `frontend/tests/prompt56-media-http.test.ts`: cookie/private binary and scoped inference contract regression.
- This report.

The workspace contains earlier uncommitted work; this list is task-specific, not a claim that every dirty file was changed in this task.

## Remaining limits / stop

- A successful, validated live suitability proposal is outstanding. Its failed run and rejection are persisted; no canned result or weaker validation was substituted.
- Positive SAM detections and mask raster rendering are not live verified; the observed live result was empty. Full video analysis is not implemented; original video evidence storage remains supported.
- Browser rendering, microphone capture, click-through acceptance and screenshot comparison remain unverified. Automated frontend and actual HTTP checks are not browser acceptance.
- Meeting records do not send external invitations or host calls. Unsupported AI meeting-plan generation is not claimed.
- Development file storage is local, private and ignored; cloud storage/deployment remain outside this task.

Stopped after participation/execution integration. No Blocker Recovery, Modal Event Memory or cloud deployment changes were started.
