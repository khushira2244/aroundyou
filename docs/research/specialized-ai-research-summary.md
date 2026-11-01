# AroundYou — Specialized AI research summary (Phase 2)

Review date: **27 October 2026 (Asia/Kolkata)**. Research/planning only. No credentials, live inference, paid calls, credit consumption, provisioning, deployments, training jobs, frontend screens, or backend implementation.

Labels: **Documented** = official source verification, not runtime testing; **Recommended** = engineering proposal; **Unverified** = requires tests, account access, or product decisions.

## Package

- [Phase 1 study](meta-ai-technical-study.md): prior fundamentals and agent boundaries, reused rather than repeated.
- [Voice transcription comparison](voice-transcription-comparison.md): Meta/AssemblyAI contracts, Hindi-English, timing, corrections, privacy, pricing, async/Pydantic design.
- [Modal integration](modal-muse-spark-open-integration.md): endpoint/auth discovery, capabilities, credits, operations, and limited Baseten fallback.
- [Provider adapter design](ai-provider-adapter-design.md): internal contracts, normalized events, durable execution, capability gating, and authority separation.

No further product specifications were available. Internal contracts are proposals, not frontend APIs or replacements for existing product rules.

## Findings and implications

**Documented:** Meta multi-turn ASR uses speechComplete for final turn text; partials lack turn IDs and late completions can follow a new turn. Word timestamps/confidence are unavailable. **Recommended:** use a mode-specific reducer and preserve timing precision. [Meta voice schemas](https://dev.meta.ai/docs/api-reference/voice/schemas)

**Documented:** current AssemblyAI models include Hindi-capable Universal-3.5 Pro recorded and Universal-3.6 Pro realtime; older indexed pages refer to earlier six-language models. SpeakerRevision can change attribution after text finality. **Recommended:** pin current model profiles and apply attribution revisions. [Current models](https://www.assemblyai.com/docs/getting-started/models), [speaker revisions](https://www.assemblyai.com/docs/streaming/label-speakers-and-separate-channels)

**Documented:** AssemblyAI streaming bills connection-open duration including idle time. **Recommended:** include silence, termination, reconnection, and add-ons in cost comparisons. [Billing](https://www.assemblyai.com/docs/billing-and-pricing)

**Documented:** Modal plan-included credits exclude Shared usage. **Unverified:** whether the proposed $100 promotion has different terms. **Recommended:** confirm eligibility and spend controls before any evaluation. [Shared Endpoints](https://modal.com/docs/guide/shared-endpoints)

**Documented:** Baseten excludes Spark Open from structured outputs/JSON mode. **Recommended:** limited advisory/read-tool fallback only, not silent strict-output parity. [Model APIs](https://docs.baseten.co/inference/model-apis/overview)

## Architecture decisions

1. **Recommended:** start inference with Meta Model API as required. Add Modal only after access, eligible funding, and contract tests.
2. **Recommended:** separate transcription and inference ports so domain workflows survive provider changes.
3. **Recommended:** distinguish provider-final text, human-reviewed transcript, and domain-approved action. Speaker labels do not authenticate members.
4. **Recommended:** keep immutable source-linked machine artifacts and reviewed revisions. Material corrections invalidate dependent drafts; retranscription cannot overwrite reviewed text.
5. **Recommended:** durable recording workers and bounded asynchronous live queues, with offsets, gaps, cancellation, attempts, and budgets.
6. **Recommended:** deterministic services own authorization, approvals, constraints, scheduling, quantities, transitions, and authoritative records.
7. **Recommended:** retrieve verified outcomes for planning and other agent decisions later. Retrieval is not fine-tuning; transcript review is not outcome verification.

AroundYou retains stage planning, work design, actor requirements, participation advisory, governance, resources, live updates, blockers, replanning, acceleration, and verified learning. Progress/resource/waste multimodal workflows are examples within the wider platform.

## Required gates before implementation

| Gate | Evidence required |
| --- | --- |
| Product contracts | Actual architecture/frontend contracts, roles, approvals, state machine, consent/retention and script preferences |
| Voice accuracy | Matched English/Hindi/Hinglish corpus, explicit WER/CER normalization, names/quantities/negations, diarization, reviewer time |
| Live correctness | Meta overlapping-turn finality, Assembly formatting/revisions, rollover/reconnect, gap/deduplication |
| Provider parity | Modal exact URL/model, effective limits, strict schemas, tools, media, streaming, replay; no opaque-state assumptions |
| Operations | Account quotas, region/privacy, failure taxonomy, p50/p95, cancellation and billed usage |
| Funding | Actual eligible balance, expiry, covered products and overage; no assumed hackathon grants |
| Domain safety | Zero forbidden state changes or cross-community leaks in deterministic fixtures |

**Unverified:** all live provider behavior and AroundYou performance. Tests are proposed in companion documents and were not executed. Reconcile future product specs before implementing; runtime parity must be demonstrated in a separately authorized bounded test stage.

## Concise provider decision matrix

| Provider | Initial use | Later evaluation | Unverified/restricted | Tests required |
| --- | --- | --- | --- | --- |
| Meta Model API | **Recommended inference baseline** | Tune against tasks | Account access, combinations, actual latency/cost | Schemas, tools/replay, streams, budgets, approvals |
| Muse Voice Transcribe | **Recommended first voice candidate** | Compare ASR quality | Hinglish/noise performance; no word timing/confidence | Finality, formats, diarization, rollover, privacy |
| AssemblyAI | Alternative voice candidate | Word timing, long files, quality comparison | Actual account settings/quotas, corpus quality, full cost | Current IDs, switching, revisions, callbacks, deletion |
| Modal Spark Open | No initial dependency | **After access/eligible credits** | Exact feature parity and limits; plan credits exclude Shared | Capability suite, credit eligibility, streams/errors, p95/cost |
| Baseten Spark Open | No initial dependency | Limited backup if needed | Strict output excluded; hackathon grant unverified | Read tools, quality/limits; reject strict workflows |
