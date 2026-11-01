# AroundYou — AI provider adapter design (Phase 2)

Review date: **27 October 2026 (Asia/Kolkata)**. Architecture planning only; no application code. Extends [Phase 1](meta-ai-technical-study.md), [voice comparison](voice-transcription-comparison.md), and [Modal investigation](modal-muse-spark-open-integration.md).

Labels: **Documented** = official source, not runtime verification; **Recommended** = proposed internal contract; **Unverified** = requires tests/access/product decision. No frontend routes, screens, database migrations, or product rules are asserted here.

## 1. Architectural decision

**Recommended:** keep inference and transcription as distinct ports. Initially select Meta Model API for inference; evaluate Muse Voice Transcribe first without coupling domain workflows to it. Add Modal inference only after access, credit eligibility, and capability gates. AssemblyAI is a transcription alternative. Baseten is a limited advisory inference fallback, not a strict-output replacement.

Conceptual flow:

```text
Authenticated domain request / consented audio
  → deterministic scope, policy and budget checks
  → versioned context or authorized audio asset
  → orchestrator / durable transcription worker
  → capability selection → provider adapter
  → normalized, validated advisory artifact
  → transcript correction / human review where needed
  → domain proposal → authorized approval → deterministic command
```

Agents support stage planning, work design, actor requirements, participation advice, governance assistance, resources, live updates, blocker assessment, replanning, acceleration, and verified learning. No model acquires authority to approve participation, verify stock, change schedules/quantities, or close work. Resource/progress/waste workflows use these common services; none defines the entire product.

## 2. Facts that require separate adapters

**Documented:** Meta supports Responses reasoning replay and strict output with endpoint-specific fields; public Chat lacks reasoning continuity. Meta ASR authenticates realtime in the first frame. Modal generally exposes compatible inference protocols with proxy auth, but Spark-specific strict output/replay parity is unverified. AssemblyAI ASR uses raw-key Authorization, queued recorded jobs, and a different realtime event protocol. Baseten explicitly excludes Spark Open structured outputs/JSON mode. See the linked official references in §10 and the detailed companion studies.

**Recommended:** adapter boundaries translate protocol, model-specific capability, and event semantics. They do not implement domain authorization or grant model authority. Avoid a generic `base_url + model` wrapper that assumes every feature is interchangeable. Never forward arbitrary unvalidated provider kwargs from the frontend or model.

## 3. Proposed internal Pydantic contracts

These are **Recommended logical model specifications**, not implemented classes. Later Pydantic models should use strict types, bounded collections/strings, discriminated unions, and `extra='forbid'` on application boundaries. Provider envelopes should tolerate documented additive fields without passing them through as permissions.

| Contract | Proposed fields/types | Trusted ownership and validation |
| --- | --- | --- |
| RequestContext | run_id UUID, actor_id UUID, tenant/community_id UUID, scope_refs list, policy_version str, record_versions map | Entirely server-injected; never from inference output |
| Budget | deadline UTC datetime, max_attempts int, max_steps int, max_tool_calls int, input/output token bounds, max_cost Decimal+currency | Server policy; global totals include child agents/retries |
| InferenceIntent | role enum, task text, authorized evidence refs, required_capabilities set, output_schema_id/version, effort_intent enum | Fixed role/schema allowlists; no authority-bearing arbitrary prompt overrides |
| ToolSpec | registry_id, version, description, parameters schema, read/propose classification | Server-owned; schema is not permission |
| ProposedToolCall | call_id str, tool registry key, arguments JSON object, provider item ID | Untrusted until parsed/authorized; dedup by attempt+call ID |
| ProposalArtifact | artifact_id UUID, schema version, claims/changes, evidence refs, unknowns, source versions, validation report | IDs/provenance generated server-side; proposed changes remain advisory |
| ProviderAttempt | provider/model/endpoint_profile IDs, attempt ID, request/response IDs, continuation handle, status | Opaque sensitive handles scoped to provider+model+protocol |
| Usage | input/cached/output/reasoning tokens int or null, audio/session duration or null, price version, actual/estimated flag | Never equate missing usage with zero; reasoning subset not double-counted |
| NormalizedFailure | category enum, provider_code str or null, retry_after duration or null, safe_message, outcome_known bool | Sanitized; provider errors cannot become user instructions |
| TranscriptionIntent | authorized audio asset/live session ref, purpose enum, languages, diarization/timing needs, consent ref | Actor/scope/capture authorization checked before provider submission |
| TranscriptArtifact | source hash, provider/model, attempt/session, original timeline, segment revisions, completion, review status | Immutable machine source; reviewed revisions separate |
| TranscriptEvent | schema_version, event_id, app sequence, session/segment/revision keys, discriminated payload | Idempotent reducer; provider ordering rules applied before normalization |

**Recommended invariants:** reject cross-scope evidence, expired consent/approval, non-finite quantities, invalid timing ranges, extra authority fields, unknown tool names, and stale record versions. Treat language hints as hints; do not invent per-word language tags if unavailable. Provider confidence may be null and must carry its kind/calibration status.

Transcript segment contract should distinguish `timing_kind = word_alignment | acoustic_segment | processed_audio_boundary | unknown`. Muse turn timing maps to processed_audio_boundary; do not call it word alignment. Unavailable word arrays/confidence remain null. Speaker refs include provider session and raw label; confirmed identity linkage is a separate reviewed product operation.

### Illustrative normalized artifact

This JSON is **Recommended application data**, not a provider response, existing frontend contract, or proof that an API call succeeded. Provider-specific raw records remain separately access-controlled.

```json
{
  "schema_version": "transcript-artifact.v1",
  "artifact_id": "00000000-0000-4000-8000-000000000001",
  "source_asset_id": "00000000-0000-4000-8000-000000000002",
  "provider": "meta_voice",
  "provider_model": "muse-voice-transcribe-1.0",
  "completion_status": "complete",
  "review_status": "unreviewed",
  "segments": [
    {
      "segment_id": "session-example:1",
      "revision": 1,
      "text": "We still need two chairs.",
      "start_ms": 1200,
      "end_ms": 3600,
      "timing_kind": "processed_audio_boundary",
      "speaker_ref": null,
      "words": null,
      "confidence": null
    }
  ],
  "gaps": []
}
```

The example reports a statement. It does not reduce inventory or establish an approved requirement. A subsequent agent may propose a resource issue; deterministic services check quantities and approvals.

## 4. Capability registry and selection

**Recommended capability record:** provider, endpoint profile, model/version, protocol, official source/review date, `documentation_status`, `test_status`, tested SDK/runtime, accepted input types, exact schema subset, effort mapping, limits, tool/replay behavior, stream terminal events, usage units, privacy/region policy, and cost profile.

Separate documented support from tested support. Suggested test status: `not_tested | passed | failed | expired`. A failed capability should not become available because the marketing page lists it. An absent claim is unknown, not unsupported; Baseten's explicit Spark strict-output exclusion is unsupported.

| Requested capability | Initial route | Alternate gating |
| --- | --- | --- |
| Strict plan/progress proposal | Meta Responses after contract test | Modal only after strict-output tests pass |
| Read-tool investigation | Meta, bounded server gateway | Modal/Baseten after tool/replay tests |
| Transcript evidence | Meta Voice candidate | AssemblyAI after language/privacy/cost tests |
| Word timestamps | Cannot require Muse to invent them | AssemblyAI profile that passes timing tests |
| Hindi-English realtime | Meta Voice evaluation | AssemblyAI current 3.6 profile; matched corpus |
| Verified historical knowledge | Application retrieval tool | Same authorized evidence contract for every inference provider |
| Web grounding | Meta documented surface | Explicit unsupported/unknown alternate route; no silent hallucinated substitute |

Selection is deterministic: filter by authorized data region/privacy, required capabilities, usable model/account access, and budgets; then apply configured priority. A model can suggest which analysis is needed but cannot choose an unapproved provider or data destination.

Do not silently convert strict JSON requirement to prompt-only JSON. If a deliberately relaxed workflow is later approved, give it a distinct schema/quality policy, visible provenance, and bounded validation retries. It cannot masquerade as provider-enforced output.

## 5. Provider interfaces and translation

**Recommended inference port:** capability lookup; count-or-estimate input; generate/stream a bounded turn; cancel where verified; normalize result/failure/usage. The result separates provisional text, complete proposed calls, final artifact, finish status, and opaque continuation. These are conceptual operations, not implemented method signatures.

**Recommended transcription port:** validate media; submit recorded job or perform file call; read status/artifact; consume live events; finish input; cancel where available; request deletion where supported. Distinguish synchronous file completion from queued jobs and WebSocket sessions. A synchronous provider can still run under an asynchronous application job.

| Adapter | Documented transport | Required translation/limits |
| --- | --- | --- |
| Meta inference | api.meta.ai/v1; Bearer; Responses | text.format, reasoning.effort, typed items, strict schemas; explicit storage |
| Modal inference | Dashboard endpoint; combined proxy Bearer | Discover model; tested protocol; affinity header; per-model feature gates |
| Baseten fallback | inference.baseten.co/v1; Bearer | Full stateless history; block Spark strict schemas/JSON mode |
| Meta Voice | Multipart HTTP and handshake-auth WebSocket | Turn completion vs partials; audioProcessedMs; session rollover |
| AssemblyAI Voice | Raw-key HTTP/WS; upload/job/poll or callback | Job status, words/utterances; Turn finality; SpeakerRevision; session billing |

**Unverified:** Modal exact Spark field combinations, output cap, persistence, media wire schemas; account-specific quotas/regions/entitlements; exact SDK version compatibility. Default these gates closed until future authorized tests.

## 6. Async workers, streams, and durability

**Recommended recorded lifecycle:** accepted → validating → queued → submitted → processing → provider_complete/partial → review_ready, with failed/cancelled/expired branches. Domain approval is a separate workflow. Persist provider job/session ID immediately on acknowledgement. Atomically save final artifact and enqueue downstream analysis using an outbox. Worker lease/fencing prevents duplicate reducers after restart.

Use bounded parallelism and per-provider circuit breakers. Prefer async network clients; isolate synchronous SDK/transcoding from event loop. Store large audio/media in authorized object storage, not broker payloads or Pydantic JSON. Enforce byte/duration bounds while receiving, not after loading everything into memory. Queue backpressure must reject/defer cleanly.

**Recommended stream lifecycle:** session_started → partial replacements → segment finals → optional attribution revisions → flush → session completion. Failures/gaps are explicit events. Final text may precede final speaker attribution. Save revisions with stable keys and apply them idempotently. Do not dispatch tools from a text delta or partial transcript.

Separate UI consumption from durable collection. A disconnected viewer does not necessarily cancel a meeting capture; that behavior requires product policy. Stop recording/provider streams on actual capture cancellation, flush where possible, and enforce idle/max-duration ceilings to prevent cost leakage.

## 7. Retry, fallback, and cost semantics

**Recommended failure categories:** invalid_request, unsupported_capability, authentication, authorization, quota, transient_provider, timeout, content_restriction, interrupted_stream, ambiguous_submission, cancelled. Include raw safe code/status separately. Same numeric code can mean different things: AssemblyAI 1008 needs reason inspection; Meta 1008 indicates configuration/pacing policy.

One retry budget includes SDK, worker, and orchestrator. Honor provider delay hints; bound total wall time, tokens/audio, and spend. A queued AssemblyAI job is polled/reconciled, not resubmitted. A Meta realtime reconnect is a new session; recover with application offsets/gaps, not sessionId replay. A transport timeout after submission may incur charges.

Do not fall back to another provider mid-turn and concatenate results. Close/mark the old attempt, retain uncertainty, start a fresh compatible request with explicit provider history. A new transcription is a separate hypothesis, never an overwrite of reviewed text. Selectively retranscribe only approved audio ranges with preserved offsets. Default failover remains off until privacy and capability equivalence are approved.

Reserve worst-case allowed cost before dispatch; settle against actual usage and price version. Keep unknown usage as estimated until reconciled. Audio duration and connection-open duration are separate billing units. Do not add reasoning twice to output or speculative rejected tokens to billable output without a provider contract. Shared/Dedicated/promotional credit eligibility is not inferred from a dollar balance.

## 8. Transcript corrections, approvals, and historical learning

**Recommended:** preserve raw machine artifact, reviewed revision, and source links. Review approval means text is accepted as a transcript, not that its claims are verified. Extracted progress, blocker, resource, or governance proposals require separate validation and authorized approval. Transcript text saying approved or finished has no authority.

Bind domain approval to exact proposal hash/version, scope, approver, record preconditions, and expiry. Recheck authorization, scheduling constraints, quantities, state, and policy in a deterministic transaction; idempotency guards the command. A reviewed transcript edit invalidates stale dependent drafts/approvals where material.

Historical retrieval eventually supplies stage planning and other agents with permission-filtered, verified outcome records. Keep source status, verifier/date, versions, and supersession. Reviewed meeting text is not automatically a verified outcome. Generated memories cannot upgrade evidence status. Retrieval, indexing, and summaries are not model fine-tuning; no training job is proposed.

## 9. Pre-implementation proof-of-concept contract suite

| Category | Required assertion |
| --- | --- |
| Schema compatibility | Each provider accepts/rejects documented subset explicitly; no silently dropped strict flag |
| Identity/scope injection | Models cannot change actor/community; zero cross-scope data/tool access |
| Tool replay | Complete calls only; unique attempt+call IDs; refusals pair with requested IDs |
| Finality reducers | Meta overlapping turns and Assembly formatting/revisions yield one coherent artifact |
| Timestamp fidelity | Correct units/offsets; missing timing remains null; no fake precision |
| Human corrections | Immutable machine source; stale revisions rejected; agent dependencies invalidated |
| Durable execution | Crash after acknowledgement/commit cannot duplicate jobs or domain writes |
| Provider failover | Separate attempts; no opaque continuation transfer; privacy/capability gates |
| Cancellation/backpressure | No runaway queues/streams; gaps surfaced; finite resource use |
| Usage reconciliation | Duration units, cache/output/reasoning, and credit eligibility recorded accurately |
| Domain authority | No plan/volunteer/inventory/closure transition from transcript or inference alone |

**Unverified product decisions:** existing endpoints and UI behavior, membership/approver roles, resource rules, status machine, recording consent/retention, script preference, data region, quantitative quality/latency/cost gates. Future specs progressively supplied in this chat take precedence over these proposals.

## 10. Official source basis (reviewed 2026-10-27)

- [Meta Responses](https://dev.meta.ai/docs/protocols/responses), [structured output](https://dev.meta.ai/docs/structured-output), [tool calling](https://dev.meta.ai/docs/tool-calling)
- [Meta voice schemas](https://dev.meta.ai/docs/api-reference/voice/schemas), [file API](https://dev.meta.ai/docs/api-reference/voice/transcribe), [realtime API](https://dev.meta.ai/docs/api-reference/voice/realtime)
- [Modal Endpoints](https://modal.com/docs/guide/endpoints), [Shared](https://modal.com/docs/guide/shared-endpoints), [Spark Open](https://modal.com/library/meta/muse-spark-open)
- [AssemblyAI recorded reference](https://www.assemblyai.com/docs/pre-recorded-audio/api-reference/transcripts/submit), [streaming sequence](https://www.assemblyai.com/docs/streaming/message-sequence), [speaker revisions](https://www.assemblyai.com/docs/streaming/label-speakers-and-separate-channels)
- [Baseten Model APIs and Spark exclusions](https://docs.baseten.co/inference/model-apis/overview)

Exact provider wire examples and source-specific limitations are in the companion documents. This design adds internal contracts only; it is not an implementation or an assertion about an existing frontend.
