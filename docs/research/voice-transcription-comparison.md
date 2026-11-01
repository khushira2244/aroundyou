# AroundYou — Voice transcription comparison (Phase 2)

Review date: **27 October 2026 (Asia/Kolkata)**. Extends [Phase 1](meta-ai-technical-study.md); does not repeat API fundamentals. **Documented** = official source support, not an executed API test. **Recommended** = proposed engineering design. **Unverified** = needs credentials, experiments, or product decisions. No paid calls or credentials were used.

## 1. Decision and comparison

**Recommended:** begin voice evaluation with Muse Voice Transcribe alongside the mandated Meta Model API development baseline. Benchmark AssemblyAI independently when word timestamps, longer recordings, or alternative Hindi-English recognition are required. Neither has demonstrated superior accuracy on AroundYou audio. Transcription and agent inference are independent provider choices.

| Dimension | Muse Voice Transcribe | AssemblyAI | AroundYou implication |
| --- | --- | --- | --- |
| English/Hindi | Documented: both among 25 languages, code-switching [M1] | Documented: current 3.5 recorded/3.6 realtime support both with native switching [A1–A3] | Evaluate actual Hinglish; no inferred winner |
| Recorded | Multipart file response, JSON/SSE/text [M2] | Async upload/submit/poll or webhook [A4–A5]; separate Sync API exists | Keep file-job abstraction |
| Live | WebSocket, mode selected at start [M3–M4] | V3 WebSocket, model/config-specific events [A6–A7] | Distinct transport adapters |
| Speakers | Session-local diarization labels [M4] | Recorded utterances/word labels; realtime labels and revisions [A8–A9] | Labels are not authenticated identities |
| Timing | Turn boundaries, not precise acoustic alignment; no word timing [M4] | Word start/end milliseconds; utterance segments [A5, A8] | Missing word timing stays null |
| Finality | PUSH_TO_TALK final transcript; multi-turn speechComplete [M4] | Turn finality differs by model/format configuration [A7] | Normalize finality, not raw fields |
| Recorded input | PCM WAV, mono, 16/24 kHz; ≤10 min; request ≤32 MB [M1–M2] | Broad audio/video containers; transcript ≤5 GB/10 h, upload ≤2.2 GB [A10–A11] | Validate per adapter |
| Live input | Raw PCM s16le mono 16/24 kHz [M3] | PCM plus documented Opus/AAC variants [A6] | Browser recording format must be inspected |
| Price snapshot | $0.18/audio hour [M5] | 3.5 recorded $0.21/h; 3.6 realtime $0.45/h, diarization extra [A12] | Include add-ons and session billing |
| Accuracy/latency | Unverified on AroundYou | Unverified on AroundYou | Matched corpus and latency measurements |
| Privacy | Standard no-training; ASR ZDR pricing exists; account terms unverified [M5] | Opt-out/TTL controls; conditional streaming ZDR [A13–A14] | Verify account settings before personal audio |

**Documented freshness issue:** current AssemblyAI model references use `universal-3-5-pro` and `universal-3-6-pro`; older indexed FAQ pages still describe Universal-3 Pro and six-language limits. Some API example responses retain old strings while field definitions list new enums. Use current field definitions/model pages and record the actual model used. Do not copy stale snippets unquestioningly. [A1–A6]

## 2. Muse request/response contracts

### File contract

**Documented:** `POST https://api.meta.ai/v1/asr/transcribe`, HTTP Bearer key, multipart `request` JSON part and `audio` file part. Optional `sessionId` query parameter correlates logs; it is not a resumption token. Accept JSON (default), `text/event-stream`, or `text/plain`. SSE ends without an appended JSON summary. Errors: 400 invalid audio/duration/body; 406 unsupported Accept; 413 body >32 MB; 429 quotas; 500 processing failure, or terminal error event after an SSE HTTP 200. [M2]

Illustrative multipart specification, not executed:

```text
POST /v1/asr/transcribe
Authorization: Bearer <server-managed key>
Accept: application/json
Content-Type: multipart/form-data; boundary=<client-generated>

request part Content-Type: application/json
{"model":"muse-voice-transcribe-1.0","audioEncoding":"WAV","mode":"DIARIZATION","languageBias":["English","Hindi"]}
audio part: <mono 16-bit PCM WAV bytes at 16 or 24 kHz>
```

**Documented response projection:** JSON contains `sessionId`, `transcript`, `audioDurationMs`, `turns`; each turn has `turnId`, `startMs`, `endMs`, `transcript`, optional `speaker`. PUSH_TO_TALK has empty turns. A truncated turn can have empty text. [M4]

**Recommended:** participant voice update clips use PUSH_TO_TALK; live updates/blockers use ENDPOINTING where useful; meetings use DIARIZATION. Do not assume diarization has the same endpoint latency as endpointing. Treat 32 MB as a multipart-body ceiling, allowing overhead. A 10-minute 24 kHz mono s16 recording is about 28.8 MB before WAV/multipart overhead; validate actual encoded bytes. Split longer recordings with explicit original-audio offsets and overlap metadata; do not silently discard the end.

### Realtime contract

**Documented:** connect `wss://api.meta.ai/v1/asr/realtime`; within 10 seconds send the first text frame below. HTTP Authorization is ignored. Await the acknowledgement containing `sessionId`, then send paced binary PCM. `endStream` half-closes input; continue receiving pending results until normal close. No Meta resume token exists; a reconnect creates a new session. [M1, M3]

Illustrative handshake, not executed:

```json
{
  "authorization": {"accessToken": "Bearer <server-managed key>"},
  "audioEncoding": "PCM_24KHZ",
  "model": "muse-voice-transcribe-1.0",
  "mode": "ENDPOINTING",
  "partialMode": "CUMULATIVE",
  "emitAudioProgress": true,
  "languageBias": ["English", "Hindi"],
  "keywords": ["AroundYou"]
}
```

**Documented:** modes/keywords/language hints are fixed at session start. CUMULATIVE replaces the active hypothesis; DELTA appends but compatibility varies. `speechStart` opens a turn; `speechEnd` is a boundary, not final text; `speechComplete` supplies completed text. Partials lack turnId and attach to the latest speechStart; completions can arrive after a later turn opens. Speaker events describe preceding audio spans and are not boundaries. `audioProcessedMs` is a processed-audio marker, not exact acoustic timing. [M1, M4]

**Recommended reducer:** maintain per-session active-turn pointer plus a map keyed by turnId; replace partials, commit speechComplete to its ID, and retain speaker-span attribution separately. PUSH_TO_TALK uses transcript `final:true`; do not use that as the sole multi-turn completion rule. Unknown event types must not crash the stream. Preserve raw event order and versioned normalized segments for testing.

### Recovery, quotas, and latency

**Documented:** realtime maximum defaults 60 minutes; pace near realtime, keeping backlog ≤5 seconds. Close 1000 means normal, 1008 means invalid configuration/pacing, 1011 means backend failure or max duration, 1013 means throttling. Both ASR endpoints share 256 concurrent sessions and 16,000 starts/hour. [M1, M3, M5]

**Recommended:** send/receive concurrently with bounded queues; reconnect before expiry using an application capture timeline. Keep a bounded consented audio buffer or durable recording where policy permits. Mark lost ranges explicitly if replay is impossible. Speaker labels are scoped to the new session and must not be merged by letter. Deduplicate overlap using source offsets, not text equality alone. Retry file 500 once per Meta guidance, then escalate with session ID; back off 429/1013. Repair 1008 and 400/406/413 instead of retrying unchanged. A lost response may already have consumed billable audio.

**Unverified:** exact language-specific accuracy, diarization error rate, noise robustness, final-turn delay, and regional latency. There is no AroundYou latency SLA. Hindi script/transliteration preferences are product decisions; never silently translate evidence.

## 3. AssemblyAI contracts and operational differences

### Recorded transcription

**Documented:** use `Authorization: <API key>` without Bearer. Local files upload to `POST https://api.assemblyai.com/v2/upload`; response includes `upload_url`. Submit JSON to `/v2/transcript`; poll `GET /v2/transcript/{id}` or receive configured authenticated webhooks. States include queued/processing/completed/error; HTTP 200 job creation is not transcript completion. [A4–A5]

Illustrative request, not executed:

```json
{
  "audio_url": "<upload_url or provider-fetchable media URL>",
  "speech_models": ["universal-3-5-pro"],
  "language_detection": true,
  "speaker_labels": true
}
```

**Documented:** 3.5 supports 18 languages and native code-switching including Hindi-English; 3.6 realtime supports 32. Universal-2 provides broader 99-language recorded coverage. Recorded results include `text`, word timing/confidence, and speaker utterances when enabled. Inspect `speech_model_used` when fallback is configured. [A1–A3, A5, A8]

**Recommended:** pin one candidate first; add fallback only after testing and keep actual-model provenance. Use webhook authentication plus a server-side job lookup, reject cross-scope IDs, acknowledge quickly, and fetch authoritative provider status asynchronously. Deduplicate repeated callbacks. Keep polling as a bounded reconciliation path, not a second submission. Upload URLs are provider references, not browser-playback artifacts.

### Realtime transcription

**Documented:** endpoint `wss://streaming.assemblyai.com/v3/ws`; server-side key in Authorization, or server-minted temporary token where browser headers are unavailable. Never put a permanent key in a URL. Current model ID is `universal-3-6-pro`. Supported encodings include pcm_s16le, pcm_mulaw, opus, ogg_opus, and AAC ADTS; raw Opus needs one packet/message, Ogg Opus accepts stream chunks, MP4/M4A is not AAC framing. PCM sample rates span 8–96 kHz; session maximum is three hours. [A6]

Illustrative URL (16 kHz mono PCM experiment):

```text
wss://streaming.assemblyai.com/v3/ws?sample_rate=16000&encoding=pcm_s16le&speech_model=universal-3-6-pro&speaker_labels=true
```

**Documented:** Begin acknowledges applied configuration/expiry. Turn messages supersede prior messages with the same turn_order. For 3.6, final has end_of_turn and turn_is_formatted true. Older Universal Streaming with formatting can emit two final messages; without formatting its final can be unformatted. Send Terminate and consume pending speaker revisions and Termination. [A7]

**Documented:** SpeakerRevision corrects earlier speaker assignments without changing text/timestamps. PENDING/unattributed words and early label uncertainty must be handled. Speaker confidence is experimental and not calibrated as probability. [A9]

**Recommended:** model-specific finality reducer, not a universal two-boolean rule. Normalize final text separately from later attribution revisions. Preserve source revisions; replace label confidence after corrections rather than carry obsolete scores. No label binds a voice to a member. Avoid Voice Focus for multi-speaker meetings until tested: suppressing background speakers could discard relevant evidence.

### Reliability and privacy

**Documented:** recorded concurrency defaults: free 5, paid 200+, excess queued. Streaming limits count new sessions/minute: free 5, paid 100+ initially, with documented paid autoscaling; inspect actual account limits. Streaming 1008 covers both quotas and invalid credentials/accounts: retry only the documented too-many-sessions case. 3007 indicates over-fast audio, 3006 inactivity, 3008 expiry; V2 is retired. [A15–A17]

**Recommended:** bounded job polling/backoff, jittered reconnection, session rollover, and explicit audio gaps. No cross-socket resume guarantee was established; do not assume session IDs resume recognition. Do not resubmit an acknowledged queued job. Synchronous SDK calls and audio decoding must not block FastAPI's event loop.

**Documented:** AssemblyAI offers account opt-out/TTL controls. Streaming ZDR for audio/transcripts is conditional on opting out of training; billing/log metadata remains. Async artifacts have different TTL/deletion behavior, and deletion can lag TTL. [A13–A14]

**Unverified:** current account opt-out, exact region, contractual retention, promotional entitlements, and end-to-end AroundYou latency. Do not generalize streaming ZDR to async jobs. Region selection and provider failover require approved data-processing policy.

## 4. Cost comparison and measurement

**Documented price snapshot:** Muse $0.18/audio hour. AssemblyAI 3.5 recorded $0.21/h + $0.02/h diarization; 3.6 realtime $0.45/h + $0.12/h diarization. Additional prompting/redaction features can cost extra. AssemblyAI streaming billing uses session duration; confirm exact applicable terms before budget estimates. [M5, A12, A18]

**Recommended:** compare total accepted-transcript cost: billed duration, silence, add-ons, retries, storage/transcoding, and human correction. Example at one billable hour: Meta $0.18; Assembly recorded+diarization $0.23; realtime+diarization $0.57, before other charges. These are arithmetic, not equivalent-quality benchmarks. Measure realtime partial latency, endpoint delay, final text delay, and post-session speaker revision separately.

Accuracy corpus: consented English, Hindi, sentence-level and intra-sentence Hinglish, regional accents, multiple devices, background noise, names, quantities, dates, negations, overlapping speech, and silent clips. Have bilingual reviewers create references; preserve script. Report WER/CER with stated normalization, named-entity/quantity/negation errors, diarization error, and human correction time. Transliteration-equivalent scoring must be reported separately from verbatim scoring. Provider benchmark claims are not direct comparisons on this corpus.

## 5. Pydantic contracts and async FastAPI pattern

All names below are **Recommended internal contracts**, not existing frontend endpoints or provider fields. See [adapter design](ai-provider-adapter-design.md) for shared envelopes.

| Proposed model | Fields/types | Validation |
| --- | --- | --- |
| AudioAssetRef | asset_id UUID, content_hash str, format str, sample_rate int, channels int, duration_ms int, size_bytes int | Positive bounds; server-authorized asset; MIME and decoded bytes agree |
| TranscriptionIntent | asset/session ref, purpose enum, language_hints list[str], diarization bool, consent_record_id UUID, idempotency_key str | Scope/actor injected by server; provider capability checked |
| TranscriptSegment | segment_id str, revision int, text str, start/end_ms int or null, timing_kind enum, speaker_ref str or null, words list or null | end≥start; source/session scope; null means unavailable |
| TranscriptEvent | schema_version, run/attempt/session IDs, sequence int, event_kind, segment/revision, gap range | Discriminated event union; monotonic application sequence |
| TranscriptArtifact | artifact_id, source hash, provider/model, segments, status, language metadata, source offsets | Complete/partial status explicit; no fabricated word timing/confidence |
| TranscriptReview | artifact_id, expected_revision, edits, reviewer_id from auth, reviewed_at | Optimistic concurrency; authorized reviewer; immutable provenance |

Normalize internal events as session_started, partial_replaced, segment_final, attribution_revised, progress, gap, failed, session_completed. Differentiate provider-final, transcript-reviewed, and domain-approved; they are separate states.

Recorded pattern: authenticated upload/intention → durable queued job → worker transcodes/validates → adapter submit/read → immutable artifact → correction/review → agent extracts proposed update/blocker → deterministic services validate/approve any authoritative action. Return promptly using whatever existing product API is later supplied; no frontend endpoint is invented here.

Live pattern: authenticated application connection → async provider send/receive tasks → bounded audio/event queues → persisted finalized segments/revisions → flush/terminate → durable artifact. Propagate cancellation, enforce capture quotas, and handle backpressure without unbounded RAM. Thread/process-isolate synchronous SDK operations and CPU transcoding; prefer async HTTP/WebSocket clients. FastAPI in-process background tasks alone are insufficient durability for long recordings.

Correction keeps original machine text immutable and creates a reviewed revision with changed spans/reason. A later re-transcription cannot overwrite reviewed text. Invalidate dependent agent drafts after material edits. A participant saying work is complete creates a claim; it does not close a work item. Meeting decisions require the existing governance process. Retain only policy-permitted audio for replay/review and delete source/derived artifacts according to the same policy.

## 6. Proof-of-concept gates (not run)

| Test | Pass condition |
| --- | --- |
| File limits/containers | Exact boundaries; malformed WAV/unsupported codec rejected before charge where possible |
| Hindi/English/Hinglish matched corpus | Published task-specific metrics; no unsupported superiority claim |
| Muse overlapping-turn reducer | Late speechComplete updates correct ID; no partial duplication |
| Assembly finality/revisions | One final artifact/turn; later speaker corrections preserved |
| Disconnect/rollover | New attempt/session, offsets retained, overlap deduplicated, gaps visible |
| Queued-job/webhook replay | One artifact; authenticated callback; no duplicate submission/domain write |
| Human correction conflict | Stale edit rejected; original preserved; dependent proposals invalidated |
| Privacy/isolation | Zero cross-community references; secrets absent from logs; deletion exercised |
| Cost/latency | Actual billed durations/add-ons and p50/p95 measured with explicit workload |
| Authority | Transcribed commands cannot approve participants, verify quantities, change plans, or close work |

## Sources (all reviewed 2026-10-27)

- M1 [Meta speech-to-text guide](https://dev.meta.ai/docs/speech-to-text)
- M2 [Meta file reference](https://dev.meta.ai/docs/api-reference/voice/transcribe)
- M3 [Meta realtime reference](https://dev.meta.ai/docs/api-reference/voice/realtime)
- M4 [Meta voice schemas](https://dev.meta.ai/docs/api-reference/voice/schemas)
- M5 [Meta pricing/limits](https://dev.meta.ai/docs/pricing-rate-limits)
- A1 [AssemblyAI current models](https://www.assemblyai.com/docs/getting-started/models)
- A2 [Recorded code switching](https://www.assemblyai.com/docs/pre-recorded-audio/code-switching)
- A3 [Realtime multilingual](https://www.assemblyai.com/docs/streaming/multilingual-transcription)
- A4 [Recorded quickstart](https://www.assemblyai.com/docs/pre-recorded-audio/getting-started/transcribe-an-audio-file)
- A5 [Submit transcript reference](https://www.assemblyai.com/docs/pre-recorded-audio/api-reference/transcripts/submit)
- A6 [Streaming reference](https://www.assemblyai.com/docs/streaming/api-spec/streaming-websocket)
- A7 [Message sequence](https://www.assemblyai.com/docs/streaming/message-sequence)
- A8 [Recorded diarization](https://www.assemblyai.com/docs/pre-recorded-audio/label-speakers)
- A9 [Streaming diarization/revisions](https://www.assemblyai.com/docs/streaming/label-speakers-and-separate-channels)
- A10 [Recorded size/duration](https://www.assemblyai.com/docs/faq/are-there-any-limits-on-file-size-or-file-duration-for-files-submitted-to-the-api)
- A11 [Supported file types](https://www.assemblyai.com/docs/faq/what-audio-and-video-file-types-are-supported-by-your-api)
- A12 [Pricing](https://www.assemblyai.com/pricing)
- A13 [Data controls](https://www.assemblyai.com/docs/data-controls)
- A14 [Retention/training](https://www.assemblyai.com/docs/data-retention-and-model-training)
- A15 [Recorded rate limits](https://www.assemblyai.com/docs/pre-recorded-audio/rate-limits)
- A16 [Streaming rate limits](https://www.assemblyai.com/docs/streaming/rate-limits)
- A17 [Session errors](https://www.assemblyai.com/docs/streaming/common-session-errors-and-closures)
- A18 [Billing and pricing](https://www.assemblyai.com/docs/billing-and-pricing)
