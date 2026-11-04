# Prompt 2 — real Meta event understanding, voice and governance

Implemented and reviewed 2 November 2026. Status: implemented and verified through FastAPI, real Meta inference and Docker PostgreSQL; browser microphone/visual acceptance remains manual. No live inference success is inferred from mocks.

## Verified integration

Server-only Bearer credentials and the Standard model `muse-spark-1.3` use `POST https://api.meta.ai/v1/chat/completions`. Requests use JSON Schema output, `max_completion_tokens=4096`, low reasoning effort, `store=false`, a 28-second HTTP timeout and no automatic retries. The transport accepts only understanding/governance requests and exposes no mutation tools. The existing worker validates output, exact cited event facts, permissions and source versions before storing a pending immutable proposal. Human review revalidates current sources before confirming anything.

Voice uses `muse-voice-transcribe-1.0` at `POST https://api.meta.ai/v1/asr/transcribe`, with multipart request/audio fields. The server checks content signatures, container type, size and decoded duration; FFmpeg converts to mono 24-kHz signed 16-bit PCM WAV. Limits are 10 MB and 60 seconds. Browser recording stops after 55 seconds. Upload and transcription are separate explicit actions. Neither recording nor visiting a screen sends audio for inference automatically.

Original audio is stored under the ignored private voice directory; original recognized text, audio SHA-256, provider session/model, source context, duration and failure state are saved in `ai_runs`. A corrected human transcript is a separate immutable context revision referencing that run. Transcription never confirms the event interpretation. The latest saved transcript can be restored without another inference call. Failed latest runs do not cause a sample/older transcript to be substituted.

Official sources reviewed: [Chat Completions](https://dev.meta.ai/docs/protocols/chat-completions), [structured output](https://dev.meta.ai/docs/structured-output), [speech transcription](https://dev.meta.ai/docs/speech-to-text), [pricing and limits](https://dev.meta.ai/docs/pricing-rate-limits). The actual transports and schema configuration were exercised successfully; no undocumented fallback model was used.

## Live results and cost boundary

The user approved four Spark request attempts and one transcription, then explicitly approved two additional governance attempts. Exactly six Spark requests were attempted: the first two returned HTTP 400 before inference because an existing blank `META_MODEL_ID` overrode the default. The configuration was corrected to `muse-spark-1.3`, and constructor validation now prevents an empty model being sent. Four subsequent completions succeeded. Exactly one voice request succeeded. There were no automatic paid retries or further calls.

- Initial reading-workshop understanding generated five contextual questions about room authorization, attendance, projector, reading materials and facilitators.
- The next understanding request incorporated organizer answers and reduced the remaining questions to three. The reviewed interpretation and all source revisions persisted.
- Education governance recommended library authorization, attendance/volunteer confirmation, printed sheets when a projector is unavailable, and handling reviewed feedback.
- Health governance recommended venue capacity for 150 attendees, crowd/emergency arrangements, maintaining a non-clinical scope, and demonstrator readiness. The health brief explicitly excluded diagnosis, medication and treatment.
- Both governance assessments were accepted through the review API on private verification events. Tickets, document references, notes and responsibility fields persisted. Both retained `permission_status=not_verified` and no external submission.
- Repeated saved-state reads did not increment the inference counters. Applying the corrected real transcript to the education verification event marked its earlier governance advice stale.
- The voice test used locally synthesized speech, not a browser microphone recording. Meta returned recognized text including “We expect 20 adults and three volunteers.” Browser microphone capture is covered by a mocked device test, not claimed as live device verification.

Four successful Spark calls reported 4,762 input and 6,092 completion tokens, including reasoning. At the reviewed Standard rates, their estimated token charge is about $0.032, plus the short transcription. This is an estimate, not an invoice or guaranteed billing cap. Rejected requests reported no token usage; their billing was not independently verified.

Live evidence is retained locally in ignored `backend/.tmp/prompt2-live-results.json`, `prompt2-voice-results.json`, `prompt2-governance-results.json` and the call-budget file. These contain synthetic verification content only. Private verification users/events are separate from existing accounts, published demo events and fixtures; nothing was reset or transferred.

## Controls and APIs

All paths below have `/v1` prefix. Cookie sessions or valid signed Bearer identity are required. Event source access and event-scoped permissions are enforced. Operational writes use existing If-Match/idempotency rules; voice uses an idempotency key and does not itself change authoritative event state.

| Existing control | Backend contract and effect |
|---|---|
| Load Previous Inputs | `GET /me/previous-creation-inputs?exclude_event_id=...`; returns only this organizer's previously entered CreationForm fields. Acknowledgements reset. No interpretation, clarification history, generated documents, plan or synthetic transcript is copied. Only an unconfirmed draft without existing context can use the UI button. |
| Record voice / Upload audio, then Transcribe | `POST /events/{id}/voice-transcriptions`, multipart `audio`; stores a private run and original source, returns editable recognized text. Same idempotency key never invokes the provider twice. |
| Reopen voice input | `GET /events/{id}/voice-transcriptions`; restores the requester's latest saved successful transcription, without inference. |
| Use as Event Context, then Review intent | The organizer applies corrected text to the existing form; `POST /events/{id}/context-revisions` records `{text,source,transcript_run_id?}`. The run must belong to this organizer/event and have succeeded. |
| Review intent | Saves the complete current human brief first, then `POST /events/{id}/context-proposals` returns a durable run. A background task executes only that run; `GET /ai-runs/{id}` polls saved status. |
| Clarification inputs + Review intent | `POST /events/{id}/context-clarifications` appends answers/source revisions, then an explicitly requested new proposal incorporates them. No canned questions. |
| Accept / Correct / Reject interpretation | Existing `POST /events/{id}/context-proposals/{proposal}/review` validates exact digest and versions. Accepting records the exact human-reviewed interpretation; rejected/stale proposals cannot alter it. Manual authoring remains available. |
| Generate Advisory Guidance | `POST /events/{id}/governance/assessments`; live inference requires confirmed event understanding and uses the actual scoped event brief. |
| Accept / Edit / Dismiss governance advice | `POST /events/{id}/governance/proposals/{proposal}/review`, with optional `corrected_governance`. Original AI content remains immutable. Individual advice can be removed while editing before human acceptance. |
| Start Governance Ticket | Existing `POST /events/{id}/governance/tickets`; one internal follow-up ticket per event. |
| Save internal follow-up | Existing `PATCH /events/{id}/governance/tickets/{ticket}`; stores status, note, responsible party and history. Closed never means government-approved. |
| Add document / reminder preferences | Existing ticket `/documents` and `/reminders` endpoints. These are document references/metadata and saved preferences; no government filing, original document-byte upload, email or reminder delivery is claimed. |

The checked-out Wizard did not contain the reported Load Previous Inputs control. A minimal button was restored alongside the existing creation-form controls, using the existing service boundary and human-input history. No additional page or dashboard was created.

## Persistence and reuse

PostgreSQL 16.14 was reached through the existing ignored database configuration. Migration `0007` was applied after inspecting the existing database at `0006`; existing data was retained. The migration adds nullable JSONB `review_decisions.reviewed_content` to preserve human-corrected governance content separately from immutable AI proposals. No tables were replaced and no second database was introduced. The immutable review trigger protects the new field too.

Existing `events`, `event_context_revisions`, `ai_runs`, `ai_proposals`, `review_decisions`, `job_tasks`, `idempotency_records`, audit/outbox records and governance tickets are reused. Clarification rounds preserve original input and confirmed-context history. Material changes stale dependent proposals/advice. Unchanged autosaves no longer unnecessarily advance the event version or invalidate a pending review. Model output includes applicability conditions, responsible party, preparation information, recommendation type and uncertainty. Verified legal requirements/unsupported external rule citations remain rejected.

Only explicit generation/transcription actions request inference. GETs, mounting/revisiting screens, loading previous inputs and accepting already generated outputs do not. Live jobs allow one attempt; timeout/failure requires an explicit new user request. A process interruption may require explicit regeneration/retry rather than an automatic paid recovery call. Existing memory foundations remain in place; no Modal integration was added.

## Commands and verification

Run from `backend` unless otherwise specified:

| Exact command | Result |
|---|---|
| `.venv/Scripts/python.exe -m pip install --no-cache-dir "python-multipart>=0.0.18,<1"` with local TEMP/TMP | Installed successfully. The first attempt failed due to sandbox temporary-directory permissions; using the workspace temporary directory resolved it. |
| `.venv/Scripts/python.exe -m alembic upgrade head` | Real existing Docker development DB upgraded `0006 → 0007`; column existence verified. |
| `.venv/Scripts/python.exe tools/run_postgres_tests.py tests/test_prompt2_integration.py tests/test_group2_context_governance.py tests/test_meta_provider.py -q` | **29 passed**, isolated PostgreSQL; migration downgrade/upgrade confined to the disposable `_test` database. Includes authorization, no automatic paid retry, unchanged authoritative state on failure, schema/error handling, provenance, transcript normalization, review correction immutability, stale advice and human-only input copying. |
| `.venv/Scripts/python.exe -m pytest tests/test_meta_provider.py -q` after adding the provenance-digest check | **11 passed**, including one additional check that legacy decision hashes remain unchanged and new human corrections participate in their digest. In total, 30 distinct focused backend tests passed across these runs. |
| `npm test -- tests/voice-input.test.tsx tests/group2-context-governance.test.tsx tests/http-adapter.test.ts` from `frontend` | **11 passed**. Microphone lifecycle is mocked. |
| `npm test -- tests/voice-input.test.tsx tests/group2-context-governance.test.tsx` from `frontend`, after final control cleanup | **6 passed**. |
| `npm run build` from `frontend` | TypeScript and production build passed; existing bundle-size warning remains. |
| `npm --prefix demo test` from repository root | **146 passed**; fixtures unchanged. |
| `.venv/Scripts/python.exe tools/verify_prompt2_live.py --approved-bounded-tests` | Two genuine successful understanding/clarification completions persisted in the real DB, plus the two earlier rejected attempts retained as failures. |
| `.venv/Scripts/python.exe tools/verify_prompt2_voice.py --approved-bounded-tests` | One genuine successful speech transcription persisted in the real DB. |
| `.venv/Scripts/python.exe tools/verify_prompt2_governance.py --approved-two-governance-tests` | Two genuine successful context-dependent governance completions, ticket/document/responsibility persistence and stale-source checks. |

Early local failures were corrected: an incorrect context-history timestamp reference, attempting to modify immutable proposal provenance, and a test assertion matching an exception's message instead of its code. The final focused run has no failures. A FastAPI TestClient/httpx deprecation warning is environmental and does not invalidate the exercised calls.

## Browser verification and runtime limits

Existing React at `http://127.0.0.1:5173/` and the previously configured API at `http://127.0.0.1:8002/health` responded HTTP 200 from the terminal. Those pre-existing processes were left untouched. A tool-started replacement API reported startup on 8003 but was not reachable from the host; the verification process was stopped. The frontend API URL was not changed to an unreachable server.

**Restart the updated runtime from normal Windows PowerShell at the repository root:**

```powershell
.\backend\tools\start_live_runtime.ps1
```

The existing helper selects a free API port, validates its OpenAPI schema, updates only the frontend API URL and prints its exact `/docs` URL. It preserves other environment values and does not reset PostgreSQL. `backend/.env` now explicitly contains the approved model ID and `META_AI_ENABLED=true`; API credentials, Modal settings and other secrets were preserved. Environment files and private recordings are Git-ignored. Import/startup itself makes no inference call.

1. Open `http://127.0.0.1:5173/signin`, sign in to a personal account, then `/create/1`.
2. On a new empty draft, click **Load Previous Inputs** if that account has prior human inputs. Verify that no AI summary/questions/plan were loaded. Fill the existing first two steps normally.
3. On Event Context, record up to 55 seconds or upload at most 60 seconds/10 MB. Click **Transcribe**, correct text, and click **Use as Event Context**. Manual text also works.
4. Click **Review intent**, answer the actual clarification fields and request another review. Inspect the proposed content, then explicitly accept it. Reload to verify restoration without generation.
5. Finish the existing event creation flow, open Governance, generate advice, inspect applicability/responsibility/preparation/uncertainty, edit or dismiss advice, then accept/reject. Create an internal ticket and save follow-up/document references.
6. Reload/revisit without pressing Generate: saved outputs should return. Revise the event context materially and verify stale-advice status before explicit regeneration.

Browser microphone/device use, screenshots/mobile visual comparison, and the full React→running HTTP server→Meta journey have **not** been claimed as passed. The actual live verification used FastAPI TestClient, real external Meta APIs and real Docker PostgreSQL; frontend bindings and capture/review controls were tested separately. Any manual browser generation is an additional user-triggered paid call, not part of the completed automated budget.

## Exact changed files

Base: `C:/Users/Khushboo/Documents/Codex/2026-10-27/br/`. These are this task's changes; other pre-existing working-tree edits were not reverted or attributed to this task.

- `.gitignore`
- `backend/app/ai/meta_provider.py`
- `backend/app/ai/voice.py`
- `backend/app/ai/service.py`
- `backend/app/api/group2.py`
- `backend/app/events/creation_service.py`
- `backend/app/governance/service.py`
- `backend/app/main.py`
- `backend/app/settings.py`
- `backend/app/shared/models.py`
- `backend/app/shared/source_resolver.py` (include new reviewed content in provenance digests; preserve legacy hashes)
- `backend/migrations/versions/0007_reviewed_content.py`
- `backend/pyproject.toml`
- `backend/tests/test_meta_provider.py`
- `backend/tests/test_prompt2_integration.py`
- `backend/tools/verify_prompt2_live.py`
- `backend/tools/verify_prompt2_voice.py`
- `backend/tools/verify_prompt2_governance.py`
- `frontend/src/features/event-creation/EventContext.tsx`
- `frontend/src/features/event-creation/Review.tsx`
- `frontend/src/features/event-creation/Wizard.tsx`
- `frontend/src/features/event-creation/VoiceInput.tsx`
- `frontend/src/features/event-creation/voice-input.css`
- `frontend/src/features/governance/Governance.tsx`
- `frontend/src/services/contracts.ts`
- `frontend/src/services/http-adapter.ts`
- `frontend/src/services/planning-contracts.ts`
- `frontend/tests/voice-input.test.tsx`
- `docs/implementation/prompt2-meta-event-understanding-governance.md`

Ignored local configuration/evidence: `backend/.env`, `backend/.private/voice/`, and `backend/.tmp/prompt2-*`. No secret values are reproduced in this report. Stop after Prompt 2; subsequent AI workflows require their own integration task.
