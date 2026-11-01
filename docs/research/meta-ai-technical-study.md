# AroundYou — Meta AI technical study

**Reviewed: 27 October 2026 (Asia/Kolkata).** Research only. No live inference calls, credentials, deployments, frontend changes, or backend implementation were performed.

## 1. Scope, evidence, and source register

AroundYou is a general-purpose community planning, participation, governance, and execution platform powered by cooperating agents. Events are one context type, not the product boundary. Recommendations cover learning groups, cultural programmes, shared resources, volunteer initiatives, community consultations, and other collective work.

The workspace initially contained only `work/` and `outputs/`. No existing code, specifications, architecture documents, or applicable AGENTS.md were found in the inspected workspace and parent instruction locations. This study uses the supplied product brief. Proposed architecture must later be reconciled with the real project and existing frontend contracts.

Evidence labels:

- **[D] Documented fact:** supported by linked official Meta or Modal documentation; not proof of successful execution.
- **[R] Engineering recommendation:** proposed AroundYou design, not a provider guarantee.
- **[U] Untested/unresolved:** requires contract tests, account access, or a product decision.

**[R] Recommendation:** begin with Meta Model API Responses, strict advisory outputs, bounded application orchestration, and deterministic approval gates. Compare Modal-hosted Muse Spark Open through a separately tested adapter. AI proposes; application services authorize, validate, and apply changes.

### Official sources

Every source below was reviewed **2026-10-27**. Canonical links omit project/team query identifiers from indexed results. Some pages were accessible through indexed query variants when bare URLs failed. Documentation is mutable; recheck before implementation and pin tested SDK/runtime versions.

| ID | Sources | Coverage |
| --- | --- | --- |
| S01 | [Overview](https://dev.meta.ai/docs/overview), [Models](https://dev.meta.ai/docs/models) | Families, versions, modalities |
| S02 | [Choosing an API](https://dev.meta.ai/docs/protocols), [Responses guide](https://dev.meta.ai/docs/protocols/responses) | Protocols, persistence, replay |
| S03 | [Chat Completions](https://dev.meta.ai/docs/protocols/chat-completions), [Quickstart recipe](https://dev.meta.ai/docs/cookbook/quickstart-chat-completions) | Messages, parameters, compatibility |
| S04 | [Structured output](https://dev.meta.ai/docs/structured-output), [Recipe](https://dev.meta.ai/docs/cookbook/structured-output) | Schemas, constrained decoding |
| S05 | [Tool calling](https://dev.meta.ai/docs/tool-calling), [Recipe](https://dev.meta.ai/docs/cookbook/tool-function-calling) | Calls, results, restrictions |
| S06 | [Reasoning](https://dev.meta.ai/docs/reasoning), [Thinking-token recipe](https://dev.meta.ai/docs/cookbook/reasoning-thinking-tokens) | Effort, billing, replay |
| S07 | [Error handling](https://dev.meta.ai/docs/error-handling), [Retry recipe](https://dev.meta.ai/docs/cookbook/error-handling-retry) | Errors and recovery |
| S08 | [Streaming recipe](https://dev.meta.ai/docs/cookbook/streaming-responses) | Chunk assembly, usage |
| S09 | [Image understanding](https://dev.meta.ai/docs/image-understanding), [Vision recipe](https://dev.meta.ai/docs/cookbook/vision-input) | Image contracts |
| S10 | [Prompt caching](https://dev.meta.ai/docs/prompt-caching), [Caching recipe](https://dev.meta.ai/docs/cookbook/prompt-caching) | Prefix reuse, routing hints |
| S11 | [Long-context recipe](https://dev.meta.ai/docs/cookbook/long-context) | Token counting, context budgets |
| S12 | [Search grounding](https://dev.meta.ai/docs/search-grounding), [Recipe](https://dev.meta.ai/docs/cookbook/search-grounding) | Search calls, citations |
| S13 | [Agent Patterns](https://dev.meta.ai/docs/cookbook/agent-patterns), [Basic loop](https://dev.meta.ai/docs/cookbook/basic-agent-loop) | Bounded execution |
| S14 | [Interleaved reasoning/tools](https://dev.meta.ai/docs/cookbook/interleaved-reasoning-tool-use), [Context management](https://dev.meta.ai/docs/cookbook/multi-turn-context-management) | Multi-step state |
| S15 | [Search-and-replace edits](https://dev.meta.ai/docs/cookbook/search-and-replace-edits), [Alert fatigue copilot](https://dev.meta.ai/docs/cookbook/alert-fatigue-copilot) | Preconditions, grounded proposals |
| S16 | [Muse Spark Open](https://dev.meta.ai/docs/muse-spark-open), [Inference](https://dev.meta.ai/docs/muse-spark-open/deploy), [Settings](https://dev.meta.ai/docs/muse-spark-open/settings) | Weights, hosting, runtime differences |
| S17 | [Speech to text](https://dev.meta.ai/docs/speech-to-text) | Muse Voice Transcribe |
| S18 | [Media segmentation](https://dev.meta.ai/docs/media-segmentation), [SAM overview](https://dev.meta.ai/docs/sam/overview), [Reading output](https://dev.meta.ai/docs/sam/reading-segmentation) | SAM 3.1 contracts/tracking |
| S19 | [Video/audio understanding](https://dev.meta.ai/docs/video-understanding) | Spark media |
| S20 | [Pricing and rate limits](https://dev.meta.ai/docs/pricing-rate-limits) | Cost, quotas, data use |
| S21 | [API reference index](https://dev.meta.ai/docs/api-reference) | Resource/schema entry point |
| S22 | [Modal Spark Open](https://modal.com/library/meta/muse-spark-open), [Modal Endpoints](https://modal.com/docs/guide/endpoints) | Provider auth, hosting, differences |

### Conflicting documentation

**[D]** The reasoning cookbook says `xhigh` maps to `high`; the current reasoning guide distinguishes deeper effort and lists model-dependent `max`. The Chat parameter table omits `max`, while the Spark 1.3 model page includes it. Search cookbook prose says Responses-only, while the protocol comparison also supports search through Messages. Some agent recipes retain Spark 1.1 headings despite 1.3 model tables. [S01–S03, S06, S12–S14]

**[R]** Start with low/medium/high; verify the exact endpoint/model before relying on higher effort. Prefer model-specific guides/reference over older recipe prose, retain discrepancies in the test ledger, and record observed behavior. Do not assume Messages search or effort equivalence. Coding-harness screenshots do not establish public private-reasoning access.

## 2. Authentication and API capability matrix

**[D]** Meta HTTP base: `https://api.meta.ai/v1`. Authentication: `Authorization: Bearer <MODEL_API_KEY>`. Pass that environment value explicitly to an OpenAI-compatible SDK. JSON requests use `Content-Type: application/json`; uploads use multipart. Realtime transcription authenticates differently. [S01, S03, S17, S21]

| Capability | Meta Chat Completions | Meta Responses | Spark Open / Modal | AroundYou recommendation |
| --- | --- | --- | --- | --- |
| Text/function tools | [D] Supported | [D] Supported | [D] Open supports tools; [U] serving contract | Responses first |
| Structured output | [D] `response_format` | [D] `text.format` | [U] Verify enforcement/subset | Validate again server-side |
| Reasoning continuity | [D] No public-key replay | [D] Encrypted replay or response ID | [U] No established Meta parity | Provider-bound histories |
| Streaming | [D] Chat SSE deltas | [D] Typed SSE events | [U] Verify events/usage | Drafts stay provisional |
| Web grounding | [D] Unavailable | [D] `web_search` | [U] Not established | Separate public/internal evidence |
| Image/audio/video understanding | [D] Spark media | [D] Spark media | [D] Model multimodal; [U] endpoint formats | Source-linked observations |
| Context | [D] Spark: 1,048,576 tokens | [D] Same window | [D] Open: 1,048,576; [U] serving limit | Selective retrieval |
| Transcription | Separate ASR service | Separate ASR service | [U] Separate capability | Dedicated adapter |
| Segmentation | [D] Use Responses | [D] `sam-3.1` | [U] No Modal SAM contract verified | Geometry adapter |
| Authority/approval | Application-owned | Application-owned | Application-owned | Deterministic domain services |

Documented entries derive from [S01–S06, S08–S12, S16–S19, S22]. Individual features do not establish every combination of tools, schemas, media, reasoning, and streaming.

## 3. API Fundamentals: ten topics and separate Agent Patterns

Each topic inherits HTTP authentication above. Deterministic boundaries are AroundYou design requirements, not model features.

### 3.1 Chat Completions

**[D] Support/contract:** `POST /v1/chat/completions` takes `model` and `messages`; text is in `choices[0].message.content`. Replay history client-side. `max_completion_tokens` bounds generation; Responses' `max_output_tokens` is rejected here. Temperature/top_p default to 1.0. Only `n=1` is supported. `top_p=0`, malformed history, unsupported fields, and context overflow produce 400. A seed is best effort, not guaranteed determinism. [S03]

**[R] Configuration/application:** use for simple explanations, classification, or extraction without reasoning continuity. Leave sampling defaults unless evaluation justifies changes. Explicitly set timeout/output budgets; prefer structured output for downstream fields and Responses for agent loops.

**[R] Recovery/deterministic boundary:** fix invalid requests instead of retrying unchanged. Preserve tool-call/result pairs. Identity, eligibility, identifiers, timezone conversion, and authoritative transitions remain application-controlled. Sampling does not enforce business rules.

### 3.2 Structured Output

**[D] Support/contract:** constrained decoding uses Chat `response_format.json_schema` or Responses `text.format`. Strict defaults false. Strict schemas require an object root, every property required, and `additionalProperties:false` on every object. `oneOf`/`allOf` are unsupported; `anyOf` is allowed below root. Limits: depth 10; 5,000 properties; 120,000 combined schema-string characters; 1,000 enum values by default; 200,000 expanded nodes. String enums above 250 values have a 15,000-character aggregate limit. Recursive references and invalid/oversized schemas produce 400. [S04]

**[R] Configuration/application:** shallow, strict, versioned schemas for plans, participation suggestions, resource needs, and evidence references. Use null for unknowns rather than fabricated defaults. Inspect generated Pydantic schemas before submission.

**[R] Recovery/deterministic boundary:** accept only complete successful results; parse/validate locally, then check domain rules/current records. Conformance proves shape, not truth or approval. Regenerate advisory failures within budget. Do not extract arbitrary JSON fragments to authorize writes.

### 3.3 Tool and Function Calling

**[D] Support/contract:** Chat definitions nest under `tools[].function`; Responses uses flat definitions. Arguments are JSON strings. Chat `tool_calls` require `tool` results keyed by `tool_call_id`; Responses `function_call` requires `function_call_output` keyed by `call_id`. Parallel defaults on; `parallel_tool_calls:false` requests serial calls. Only `tool_choice:"auto"` is accepted; `none`, `required`, and named choices return 400. `max_tool_calls` bounds built-ins, not client functions. Function names allow at most one dot. [S05]

**[R] Configuration/application:** expose narrow context/history/availability reads and advisory proposal tools. Omit tools for no-tool steps. Require expected output through validation, since the API cannot force the desired function call.

**[R] Recovery/deterministic boundary:** dispatch only completed calls after registered-name, schema, permission, and scope checks. Return typed refusal/failure with the matching ID. Derive actor/tenant from trusted context. No arbitrary Python, SQL, shell, or URL execution. Bound calls in application code; serialize authoritative writes.

### 3.4 Reasoning and Thinking Tokens

**[D] Support/contract:** Chat uses `reasoning_effort`; Responses uses `reasoning.effort`. Reasoning consumes output budget and billed output tokens. Spark rejects `none`. The guide lists minimal/low/medium/high/xhigh and model-dependent max; Spark 1.3 Contributor excludes max. Responses supports `include:["reasoning.encrypted_content"]`; public Chat `reasoning_content` is redacted. Optional reasoning summaries are documented. [S06]

**[R] Configuration/application:** low for extraction/routing, medium for synthesis, high for conflicting constraints. Measure cost per accepted workflow. Audit conclusions, evidence, tool outcomes, and validations rather than private chain-of-thought.

**[R] Recovery/deterministic boundary:** incomplete output needs reduced scope or sufficient bounded budget. Higher effort never grants permission to approve volunteers, verify inventory, change plans, or close work. Resolve effort discrepancies through endpoint tests.

### 3.5 Error Handling and Retry

**[D] Support/contract:** envelope fields: `error.message`, `type`, `param`, `code`; code may be null. Transient 429/500/503 failures warrant backoff; honor Retry-After. Invalid input, authentication, billing/access, missing resources, and oversized payloads require correction. A 504 can reflect long generation or delay before a first stream event. Background Responses can address long jobs; unchanged timeout-prone retries are discouraged. [S07]

**[R] Configuration/application:** one retry owner avoids multiplying SDK/worker retries. Initial policy: three inference attempts maximum, jittered backoff, Retry-After as lower bound, and total deadline. Queue delayed retries instead of blocking FastAPI request workers.

**[R] Recovery/deterministic boundary:** separate repairable input, transient provider, terminal access/policy, and ambiguous side effects. A model retry does not make earlier writes safe to repeat. Persist idempotency and reconcile unknown outcomes. Exhaustion yields failed/pending status, not fabricated success.

### 3.6 Streaming Responses

**[D] Support/contract:** `stream:true` yields SSE. Chat text uses `choices[].delta.content`; guard empty choices/null deltas. Chat usage requires `stream_options:{"include_usage":true}`. Responses uses typed events/final usage. Handle completed, incomplete, failed, and terminal error events. Ordinary interrupted Chat generation restarts on retry; background retrieval documents sequence-based continuation. [S02, S07, S08]

**[R] Configuration/application:** provisional progress/drafts through existing frontend contracts later. Distinguish run and provider-attempt IDs; assemble calls by item/call ID. Set connection, first-event, idle-read, and total deadlines.

**[R] Recovery/deterministic boundary:** partial JSON/arguments cannot execute tools or update authoritative records. Mark interrupted drafts incomplete; deduplicate restarts. Client disconnect does not prove provider cancellation. Local cancellation stops future dispatch even if provider processing continues.

### 3.7 Vision Input

**[D] Support/contract:** Spark returns text from image-plus-text input. Responses uses `input_image` with a string `image_url` or uploaded `file_id`; Chat uses `image_url` content parts. Public URLs/base64 data URLs are documented. Vision describes scenes, extracts text, and localizes objects. Inaccessible URLs/corrupt images cause request errors. [S09, S07]

**[R] Configuration/application:** candidate receipt/resource extraction, site accessibility descriptions, and documentation-photo organization. Prefer private uploads or scoped URLs. Preserve source hash, dimensions, provenance, and capture-time claims.

**[R] Recovery/deterministic boundary:** validate MIME/decode/size first; repair inaccessible media rather than repeating fetches. Require uncertainty/review. Photos cannot verify availability, identity/consent, completion, or actual time/location. Independently check measurements/counts.

### 3.8 Prompt Caching

**[D] Support/contract:** automatic prefix caching reuses stable leading tokens; volatile early content breaks matching. Chat reports `usage.prompt_tokens_details.cached_tokens`; Responses reports `usage.input_tokens_details.cached_tokens`. Optional `prompt_cache_key` groups requests. `prompt_cache_retention` accepts in_memory/24h as hints, not guarantees. [S10, S03]

**[R] Configuration/application:** stable instructions/schema guidance/examples first; changing context/user input last. Version prompts and measure hit ratio/latency. Do not confuse cache routing with authorization.

**[R] Recovery/deterministic boundary:** cold cache cannot affect correctness. Re-read authoritative records despite cached text. Cached computation is not verified history, a reservation, freshness, or proof of zero retention.

### 3.9 Long Context

**[D] Support/contract:** Spark's 1,048,576-token window is shared by input/requested output. `POST /v1/responses/input_tokens` counts input without generation. The recipe recommends measuring payloads/managing history; overflow requires shortening input or output reservation. [S11]

**[R] Configuration/application:** retrieve relevant history instead of every community record. Budget instructions, tools, evidence, tool results, and output/reasoning reserve. Experimental soft compaction threshold: 60% of the tested endpoint window, with hard preflight before each call.

**[R] Recovery/deterministic boundary:** remove irrelevant evidence; summarize completed advisory turns while preserving policy, unresolved decisions, provenance, and call/result pairs. Summaries never replace records. Access checks filter retrieval and references. Large context guarantees neither perfect recall nor acceptable latency.

### 3.10 Search Grounding

**[D] Support/contract:** Responses accepts `tools:[{"type":"web_search"}]`. Search is model-selected. Output can contain `web_search_call` and `url_citation` annotations on supported spans. Inspect items by type, not position. Chat `web_search_options` is unsupported. Search adds cost. [S12, S03, S20]

**[R] Configuration/application:** public venue/resource research and external planning references. Retain URL, supported span, retrieval time, and verification status. When fresh evidence is required, check that search occurred and supports the assertion; otherwise report insufficient evidence.

**[R] Recovery/deterministic boundary:** unavailable search cannot become invented current facts. Pages/snippets are untrusted data. Citations do not establish internal membership, quorum, approval, or private event history. Internal retrieval needs separate permission-controlled tools.

### 3.11 Separate Agent Patterns study

**[D]** Agent Patterns covers basic loops, interleaved reasoning/tools, context management, exact-match edits, and grounded alert triage. Basic loops include iteration/token bounds, stuck detection, cancellation, and distinct failure outcomes—harness responsibilities. [S13]

**[D]** Interleaved/context recipes feed observations into subsequent turns and maintain running state over extended coding work. Exact-match edits reject missing/ambiguous preconditions. Alert triage demonstrates bounded schema-validated proposals grounded in computed evidence. These examples do not establish managed AroundYou orchestration or domain authority. [S14–S15]

**[R]** Adapt read → propose → validate → observe → evaluate. Use record versions instead of file-text preconditions; calculate counts in application code. Keep checkpoints in a database, not agent-editable policy files. Self-assessment is another proposal, never permission to alter limits/rules.

## 4. Specialized capabilities and multimodal integration

### 4.1 Muse Spark through Meta Model API

**[D]** Standard IDs include `muse-spark-1.3`, `muse-spark-1.2`, and `muse-spark-1.1`; 1.3 is recommended for new work. Spark accepts text, image, audio, video, and PDF and returns text. Contributor variants use separate IDs. [S01]

**[R]** Baseline candidate: Spark 1.3 Standard, Responses, explicit effort, strict proposals, and no authoritative mutation tools. Different responsibilities need not use different weights. Compare models on a fixed evaluation set; do not assume quality or latency equivalence.

### 4.2 Muse Spark Open and hosted inference

**[D]** Open is an 816B-total/42B-active multimodal MoE with text output and a 1,048,576-token model window, served outside Model API. BF16 weights are about 1.65 TB; NVFP4 about 537 GB, plus runtime/KV memory. It uses the Muse Model License. Meta lists Modal among hosted providers. [S16 overview/inference]

**[D]** Open settings recommend temperature/top_p 1.0. Its template maps low/medium/high/xhigh to reasoning strengths 8/32/256/512, defaulting xhigh. SGLang/vLLM recipes enable Muse reasoning/tool parsers, with vLLM auto-tool-choice enabled. [S16 settings]

**[R]** Start with hosted comparison. Active parameters do not describe total weight memory. Evaluate parser correctness, quantization, cold/warm latency, concurrency, and effective context. Hosted Spark 1.3 behavior cannot be inferred from the Open checkpoint or vice versa. Self-hosting also needs runtime patching, GPU capacity, monitoring, and license review.

### 4.3 Muse Voice Transcribe

**[D]** `muse-voice-transcribe-1.0` uses file `POST /v1/asr/transcribe` and live `wss://api.meta.ai/v1/asr/realtime`. File auth is HTTP Bearer; realtime auth is first-frame `authorization.accessToken` with Bearer prefix, not HTTP Authorization. Files use multipart `request` JSON plus `audio`. Output includes transcript/duration/turns and optional speaker labels. Timestamps are turn-level; word timestamps, confidence scores, and speech synthesis are unavailable. [S17]

**[D]** Files require mono 16-bit PCM WAV at 16/24 kHz, at most 10 minutes/32 MB. Realtime takes raw signed 16-bit little-endian mono PCM. Handshake deadline: 10 seconds; send near realtime with at most five seconds backlog. Default session length: 60 minutes. Both endpoints share 256 concurrent streams and 16,000 starts/hour. [S17]

**[R]** Use consented meeting transcription and voice-submitted suggestions. Split long files with explicit offsets and tested overlap/deduplication. Replace cumulative partials; do not append them as new final text. Speaker labels do not identify authenticated members. Reviewed minutes cannot themselves cast votes or approve changes.

**[R] Recovery:** convert invalid formats first; back off on file 429/realtime close 1013. Retain session ID and confirmed-segment offsets for reconnect reconciliation. Evaluate relevant Indian languages, code-switching, names, noise, and overlapping speech with consented samples. Language support does not guarantee equal accuracy.

### 4.4 Segment Anything Model 3.1

**[D]** `sam-3.1` uses Responses and Meta Bearer auth. Supply one concrete noun phrase plus `input_image` or `input_video`; box/point prompts identify specific objects. Video supports MP4/MOV with H.264/H.265/MPEG-4. Streaming is recommended for video. Output is special-token text carrying geometry, not an ordinary JSON segmentation object. [S18 overview/media]

**[D]** Output has explicit frame markers, object IDs, boxes, and masks. Mask payloads are base85, not base64. Frames/IDs may be sparse; tracking direction affects ordering. Zero matches can succeed with empty output. IDs must not be trusted across full occlusion, exit/reentry, or very long clips. Official client parsers are documented. [S18 reading]

**[R]** Applications include resource annotations, equipment-count suggestions, site-layout assistance, and review overlays. Preserve dimensions, frame IDs, prompt/model, and mask provenance. Verify a supported Python parser for FastAPI or use an isolated tested conversion service; Python package/version availability was not verified here. Validate coordinates, decoded size, and raster dimensions.

**[R] Recovery/deterministic boundary:** empty detection means no detected match, not verified absence. Reject malformed/truncated geometry. Physical measurement requires calibration. Segmentation cannot verify inventory ownership/availability, participant approval, or completed work. Review redaction coverage before reliance.

### 4.5 Spark audio/video/image processing

**[D]** Spark interprets video visuals and embedded audio together and returns text. The guide uses Files upload with `purpose:"user_data"`, then Responses `input_file` by `file_id`. Audio/video understanding also works through Chat. This differs from SAM's `input_video` contract. [S19]

**[R]** Pipeline: authorize upload → validate/scan media → attach consent/access metadata → select transcription, interpretation, or segmentation → persist source-linked observations → human review → domain validation. Use separate adapters instead of assuming one media payload fits all models.

**[U]** Verify exact codec/file/frame/duration limits and feature combinations for the selected endpoint. ASR's 10-minute/32-MB limits do not automatically apply to Spark media; one Open provider's sampling cap does not establish Meta's cap. No measured latency or SLA was established here.

## 5. FastAPI multi-agent orchestration recommendations

Everything in this section is **[R] proposed application architecture**, pending actual project specs. The provider is an inference dependency; application code owns state and authority.

### 5.1 Specialized responsibilities

| Role | Responsibility | Candidate scoped reads | Output/authority |
| --- | --- | --- | --- |
| Intake/context | Clarify intent and missing information | Community/project context | Summary/questions |
| Planning | Tasks, dependencies, alternatives | Approved plan/constraints | Draft plan |
| Participation | Role matches and unmet needs | Consented skills, availability, eligibility result | Suggestions; no volunteer approval |
| Resources | Resource requirements/shortages | Verified ledger/reservations | Needs proposal; no verification |
| Governance | Explain rules, compare proposals | Versioned policy/decisions | Analysis; no vote/approval |
| Execution support | Blockers and candidate next steps | Task state/accepted evidence | Follow-up proposals; no closure |
| Knowledge | Retrieve verified prior outcomes | Permission-filtered history | Source-linked evidence |
| Review/synthesis | Contradictions/missing evidence | Proposals and snapshot | Consolidated proposal/escalation |

Use deterministic routing for established workflows. AI can suggest a route only through an allowlist and validated output. Invoke only necessary roles. Typed artifacts move through the orchestrator instead of unbounded peer conversations. Roles can initially share one tested model.

### 5.2 Shared context and controlled state

Inject a trusted envelope containing actor, tenant/community, project/activity/event scope, run ID, source versions, policy version, tools, deadline, and budgets. Identity/scope are server-assigned and cannot be overridden by model arguments.

Maintain three logical stores, even if one database implements them:

1. Authoritative records: approved plans, memberships, eligibility, verified inventory, reservations, decisions, and work state.
2. Advisory artifacts: immutable proposals, observations, draft minutes, and summaries with sources/validation results.
3. Execution ledger: run/step/attempt state, tool calls/results, provider IDs, budgets, checkpoints, and failures.

Agents get versioned snapshots and relevant evidence. Later agents reference earlier artifact IDs rather than rewriting them. Conflicts remain explicit. Refresh affected records before approval/commit; changed preconditions make proposals stale or require revalidation.

### 5.3 Bounded multi-step execution

Initial **untested tuning values**: 3 concurrent agents; 6 inference turns/agent; 12 client calls/agent; 24 client calls/run; 60-second interactive deadline. Every retry/nested call consumes parent limits. Stop at any global cap; delegation cannot multiply the allowance. Long media work needs separately bounded queued jobs.

Also enforce total tokens, monetary reservation, input/result bytes, tool timeouts, and evidence count. Cost ceilings are required release configuration, not agent-selected values. Detect repeated identical calls/failures. Budget exhaustion is incomplete, not successful.

Proposed lifecycle: `queued → running → awaiting_review → approved → applying → succeeded`; separate failed/cancelled/expired/stale outcomes. These are internal application names, not provider statuses. Distinguish successful analysis from successful application of an approved change. Release worker resources during human review; resume from durable state.

### 5.4 Tool permissions, validation, and human approval

Every call passes registered-name, schema, actor/scope, budget, current-version, and audit checks. Tools return typed success/refusal/failure, provenance, and versions. Prompt rules supplement enforcement; they cannot replace it.

Authoritative change sequence:

1. Agent creates an advisory proposal with source IDs, expected versions, and a proposed diff.
2. Deterministic validators check dates, capacity, dependencies, arithmetic, permissions, and policy.
3. Authorized humans review the exact diff, consequences, evidence, and unresolved assumptions.
4. Store approval bound to proposal ID/hash, scope, approver, policy, record versions, and expiry. Model fields or chat claims saying approved are insufficient.
5. A deterministic command handler rechecks conditions transactionally and applies only approved operations using an idempotency key.
6. Record before/after versions and domain events; deliver external notifications through a deduplicated outbox after commit.

Plan changes, volunteer approvals, inventory verification, and work closure follow this boundary. Human approval does not bypass role permissions, quorum, or invalid arithmetic. No agent receives unrestricted database mutation tools.

### 5.5 Failure recovery and traceability

Checkpoint before/after tools and before approval waits. Use worker leases/fencing against duplicate execution after restart. Reads can replay after authorization; writes require idempotency lookup and outcome reconciliation. Missing HTTP responses do not imply rollback.

Trace run/parent/step/attempt IDs; provider/model; prompt/schema/tool versions; source versions; timestamps; usage/cache/cost; latency; retries; validation; approval reference; and domain events. Retain sanitized errors/provider IDs where supplied. Avoid credentials, private reasoning, raw sensitive media, or unnecessary participant details in logs.

On agent failure, preserve successful advisory artifacts and identify missing analysis. The workflow decides whether review can proceed; another agent cannot invent missing evidence. Provider fallback is an explicit attempt with separate history and equivalent validated constraints. Never move opaque Meta reasoning or response IDs to Modal.

### 5.6 Verified historical knowledge

Use permission-filtered internal retrieval. Store source ID/type, scope, verification status, author/verifier, verification date, activity/event date, version, and superseded/deleted state. Distinguish participant claims, machine observations, and human-verified outcomes.

Filter scope/verification before ranking. Combine metadata/text search with embeddings only after selecting/testing an embedding service; no Spark embedding endpoint is established here. Recheck returned IDs/permissions before prompt inclusion. Preserve supporting passages and record links.

Agents cite internal IDs. Validate existence, visibility, freshness, and claim support. Draft/unverified sources retain labels; missing verified evidence produces an explicit gap. Generated summaries never upgrade verification. Reindex invalidated records and invalidate derived summaries after edits/deletions.

## 6. Reasoning and structured-output configuration

**[R]** Separate tool investigation from final schema-constrained proposal generation. This avoids relying on untested combinations, without claiming those features cannot coexist.

This **unexecuted illustrative Meta Responses request** uses documented fields [S02, S04, S06]. Its schema, task, and budget are AroundYou recommendations. It grants no authority.

```json
{
  "model": "muse-spark-1.3",
  "store": false,
  "reasoning": {"effort": "low"},
  "max_output_tokens": 2048,
  "input": "Summarize this proposal: organise a shared reading group. Leave missing information as questions.",
  "text": {
    "format": {
      "type": "json_schema",
      "name": "intake_draft_v1",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {
          "summary": {"type": "string"},
          "questions": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["summary", "questions"],
        "additionalProperties": false
      }
    }
  }
}
```

**[R]** The 2,048-token budget includes reasoning and is an extraction experiment, not production sizing. Validate semantics after parsing. Tool schemas are independently versioned/strict. Never populate authenticated identity, verification, or approval solely from generated fields.

**[D]** Responses supports encrypted client-managed replay and server-managed `previous_response_id`. Storage defaults enabled. Background creation uses `background:true`, cannot combine with `stream:true` on creation, and can later be stream-retrieved. [S02]

**[R]** Prefer explicit `store:false` for ordinary sensitive advisory runs pending retention review. Test stateless replay using `include:["reasoning.encrypted_content"]`; preserve typed-item order, commentary phases, and call/result relationships. Treat replay content as sensitive provider-bound state. `store:false` does not prove contractual zero retention. Review background persistence separately.

## 7. Provider abstraction: Meta API and Modal

**[D]** Modal advertises Spark Open Shared Endpoints, multimodal input, and NVFP4 precision. Setup redirected to login during this review; no account-specific URL or request model string was verified. [S22 library]

**[D]** General Modal endpoint docs support Chat Completions, Responses, and Messages for text-generation models. Shared endpoints require proxy-token Bearer auth as `token_id.token_secret`. Use dashboard examples or endpoint `/v1/models` for model names. Shared billing is per token; Dedicated is compute. `Modal-Routing-Affinity-Key` groups conversations, but scaling/replacement can change routing. [S22 endpoints]

**[R]** Define an internal adapter contract instead of forwarding arbitrary SDK parameters:

| Operation | Normalized result | Provider translation |
| --- | --- | --- |
| Generate proposal | Typed artifact, completion status, usage | Schema subset/location, effort, model |
| Inference turn | Text, proposed calls, opaque continuation | Tool formats, IDs, replay |
| Stream | Draft deltas, completed items, terminal outcome | Events, usage, failure/reconnect |
| Count/check input | Exact count or labelled estimate | Counting support/effective limits |
| Understand media | Source-linked observations | Content blocks, codecs, limits |
| Transcribe/segment | Transcript/geometry artifact | Specialized services/parsers |

Capability profiles record tested provider/endpoint/model/version, protocol, strict-schema behavior, effort levels, effective context/output bounds, tools, search, media formats, streaming, usage, persistence, and processing policy. Untested features default unavailable. Reject unsupported combinations; never silently remove strict output or approval constraints.

**[R]** Meta candidate: fixed base URL, server secret, Spark 1.3 Standard, Responses. Modal candidate: dashboard URL, verified request model, scoped proxy secret, tested capabilities. Do not invent a global Modal inference URL, assume a Hugging Face checkpoint ID is its request model, or reuse Meta credentials.

**[U]** General API compatibility does not establish Spark Open parity for encrypted replay, stored-response semantics, strict schemas, built-in web search, tool-choice behavior, or media combinations. Verify individually. Quantify Dedicated cold starts/capacity and Shared latency/concurrency. Failover requires fresh compatible context and explicit attempt tracking.

## 8. Reliability, security, latency, and cost

### 8.1 Documented commercial snapshot

**[D]** Spark Standard: $1.25/million input tokens; $0.15/million cached input; $4.25/million output. Web grounding: $2.50/1,000 queries. Voice: $0.18/audio hour. SAM: $2.50/1,000 images or $0.20/1,000 frames, with a 50-frame minimum/video request. Spark 1.3 lists 3,000 RPM and 4,000,000 TPM per team; background creation adds a 600/minute team limit. Standard content is not used for training; Contributor content may be. [S20]

**[D]** Modal Spark Open Shared lists $1.25/million prompt, $0.15/million cached prompt, and $4.25/million completion tokens. This does not establish identical tokenization, reasoning accounting, or ancillary costs. [S22 library]

**[R]** Recheck prices and actual account quotas before spending. Default community data to Standard until product/privacy review permits otherwise. No-training and zero-retention are separate properties.

### 8.2 Cost and latency controls

**[R]** Estimate Meta text cost as `(uncached_input × 1.25 + cached_input × 0.15 + output × 4.25) / 1,000,000`. Add search, media services, retries, storage, and infrastructure. Output includes reasoning: do not add it twice. Cached input must not also appear in uncached billing.

Illustrative arithmetic: 10,000 uncached input + 20,000 cached input + 3,000 total output tokens costs **$0.02825**; one paid search adds $0.0025. This is not a measured workflow cost or quote.

Track p50/p95 end-to-end latency, first event/visible token, queue/tool/generation time, accepted proposal rate, correction rate, and tokens/cost per accepted proposal. Separate cold/warm context, effort, media length, and agent count. Streaming cannot remove prefill/reasoning time. Bound parallelism against quota bursts and stale snapshots. Reserve workflow budgets before dispatch.

### 8.3 Security and operational controls

**[R]** Keep secrets server-side, scoped/rotated; redact auth frames/signed URLs. Authenticate users and authorize each record. Validate media type, decoded size, and duration. Define consent, retention, deletion, and access for recordings/derived artifacts.

Treat user text, history, images/OCR, pages, and tool outputs as untrusted data. Embedded instructions cannot change permissions. Avoid general fetch tools; application fetching must restrict destinations and block internal/metadata addresses. Do not expose arbitrary SQL/shell capabilities.

Use durable queues, concurrency limits, circuit breakers, finite retries, idempotent commands, approval expiry, optimistic concurrency, and outbox delivery. Application code owns eligibility, capacity, inventory balances, dependency checks, transitions, quorum/vote arithmetic, and approval verification. Audit history survives model/provider changes.

## 9. Known limitations and unresolved questions

| Issue | Status | Required resolution |
| --- | --- | --- |
| Existing architecture/frontend contract | [U] Unavailable here | Review actual specs/roles/schema/APIs |
| Account/model/region access | [U] No authenticated calls | Verify intended deployment account |
| Reasoning documentation conflicts | [D] Identified above | Probe levels and compare usage/quality |
| Strict schemas with tools/media/streaming | [U] Combinations untested | Contract/failure-path tests |
| Modal endpoint/model | [U] Setup needs login | Inspect dashboard/authorized Models API |
| Modal replay/search/schema parity | [U] Compatibility insufficient | Verify capability profile |
| SDK/runtime versions | [U] No dependencies | Pin versions/contracts |
| AroundYou latency/quality/cost | [U] No benchmark | Representative evaluation/load test |
| Persistence/residency/deletion | [U] No contractual review | Verify terms/account settings |
| Embeddings | [U] No provider selected | Independent selection/evaluation |
| SAM Python parser | [U] Not validated | Official package/version and fixtures |
| Media maximums/combinations | [U] Only ASR bounds established here | Verify selected model schema/boundaries |
| Approval/governance policy | [U] Product rules absent | Define approvers, quorum, expiry, conflicts |

This research does not establish guaranteed truthfulness, managed multi-agent coordination, portable provider state, a Spark embedding endpoint, autonomous inventory verification, or autonomous closure. Do not infer them from coding-agent examples.

## 10. Recommended proof-of-concept tests

**[R] Proposed tests; none executed.** Use an isolated research harness and synthetic/consented fixtures. Record provider/model/SDK, schema/payload versions, expected/actual results, usage, IDs, and dates. Mock domain transitions first; use limited authorized live calls for API contracts. No frontend rewrite or full backend is needed.

| Test | Procedure | Acceptance criterion |
| --- | --- | --- |
| Auth/contracts | Valid/invalid keys; basic Chat/Responses | Correct mapping; no secrets; no auth retry loop |
| Strict schemas | Nested/nullable; invalid required/additional properties; combinators/depth/enums | Invalid schemas fail; complete accepted artifacts validate locally |
| Tool negotiation | Reads, plain reply, multiple calls, bad args/names, tool_choice variants | No assumed forced call; forbidden calls never execute; IDs paired |
| Client-call bounds | Repeated/alternating calls and delegation | Global caps hold across agents/retries |
| Reasoning/replay | Low/medium/high; xhigh/max; encrypted/ID/Chat | Verified levels/usage; no private-reasoning dependence |
| Streaming | Fragmented JSON/args; usage-only chunks; terminal failures; disconnect | No partial execution/success; coherent restart/usage |
| Retry behavior | Inject 400/401/402/403/404/413/429/500/503/504; lost responses | Repair errors stop; Retry-After honored; finite attempts; write reconciliation |
| Context/cache | Token preflight; near limit; stable/volatile prefixes | Overflow prevented; evidence/policy retained; cache-independent correctness |
| Search | Current question, no-search answer, bad citations, injected instructions | Evidence requirement enforced; unsupported current claims withheld |
| History retrieval | Cross-community, drafts, stale/deleted/conflicting records | Zero leakage; verification retained; claim provenance |
| Human approval | Model says approved; wrong actor; changed hash/version; expiry | Zero authoritative writes without valid bound approval |
| Concurrency/crashes | Competing reservations; duplicate workers; crash after commit | No over-reservation; one transition; deduplicated outbox |
| Voice | File bounds; handshake/pacing; partials/reconnect; mixed language | Correct transport; measured error; no inferred identity/approval |
| SAM | Empty matches; sparse frames/IDs; occlusion; corrupt masks | Valid geometry; zero matches accepted; no fabricated verification |
| Spark media | Receipt/photo, audio, video+audio, schema extraction | Provenance/offsets; uncertainty; no automatic verification |
| Meta–Modal parity | Same fixtures; unsupported capabilities; failure | Equivalent constraints or explicit unsupported error; no opaque transfer |
| Load/cost | Representative workflows, effort, cold/warm prefixes | Agreed p95/cost ceilings; functioning budgets/cancellation |
| Product breadth | Reading group, culture, shared equipment, governance, volunteer initiative | Suitable rules across scenarios; no waste-only assumptions |

Later implementation gates: zero forbidden writes/leaks in deterministic fixtures; recorded provider contracts; agreed quality/latency/cost targets based on measurements; visible capability gaps; and reconciliation with actual project specifications. These gates inform implementation and do not imply this research task built the backend.
