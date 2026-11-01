# AroundYou — Modal Muse Spark Open integration (Phase 2)

Review date: **27 October 2026 (Asia/Kolkata)**. Research and planning only; no deployments, GPU provisioning, benchmarks, training jobs, or paid requests. Extends [Phase 1](meta-ai-technical-study.md). Labels: **Documented** = official source; **Recommended** = design proposal; **Unverified** = requires account/API/product verification.

## 1. Adoption sequence and availability

**Recommended:** develop with Meta Model API first. Evaluate Modal after access and eligible credits are confirmed. Do not delay Meta development for promotional credits and do not switch merely because the API shape looks compatible.

**Documented:** Modal's Spark Open library lists an NVFP4 multimodal model, a 1M-token context, and Shared per-token inference. It lists text/image/video/audio. Public setup links require sign-in, so account-specific model names and URLs were not observed. The launch announcement confirms Shared availability. [D1–D2]

**Unverified:** exact enforced context/output cap, strict schema support, per-model protocol differences, media encodings, reasoning levels accepted by Modal, and effective concurrency. An inaccessible supported-models reference and a generic Dedicated statement are insufficient to authorize a specific configuration.

## 2. Shared versus Dedicated

| Aspect | Shared Endpoint | Dedicated Endpoint |
| --- | --- | --- |
| Documented capacity | Modal-managed pool; model-specific workspace-wide in-flight cap; over-limit 429 [D3] | Isolated autoscaling containers, configurable minimum/maximum/buffer [D4] |
| Documented billing | Per token [D1, D3] | Compute resources [D4–D5] |
| Documented placement | Shared requests route through us-west [D3] | Routing and compute placement configurable separately [D4] |
| Documented auth | Proxy token required [D5] | Auth required by default; retain it [D5] |
| Documented monitoring | Endpoint Usage/token rates [D3] | Activity, Responses, Containers, latency/throughput/GPU metrics [D4] |
| Recommended use | First hosted Open evaluation if funded/eligible | Consider only for isolation/control or measured capacity need |
| Unverified | Account entitlement, exact cap, model-specific wire behavior | Current Spark Open recipe/hardware availability, cost, readiness latency |

**Documented tension:** Shared docs say every Shared model is also available Dedicated; the Spark library/announcement prominently document Shared. Treat Dedicated Spark eligibility as requiring current supported-model/dashboard confirmation rather than inventing a create command. [D1–D4]

## 3. Authentication and discovery

**Documented:** use the dashboard-provided endpoint URL/model request value, or retrieve the model through `<endpoint-url>/v1/models`. Proxy credentials combine ID and secret separated by a period and are sent as Bearer. General text endpoints support OpenAI-compatible Chat Completions/Responses and Anthropic-compatible Messages. `Modal-Routing-Affinity-Key` is best-effort conversation routing, not server-side conversation storage. [D5]

**Recommended:** store endpoint base, verified model name, secret reference, allowed protocols, and capability profile in server configuration. Never expose proxy tokens in browser code, logs, examples, or URLs. Scope production/development credentials separately. Do not reuse Meta keys or assume a checkpoint ID is the hosted request model. No key is needed for this research.

Illustrative transport template, not executed:

```text
POST <dashboard-endpoint-url>/v1/chat/completions
Authorization: Bearer <proxy-token-id>.<proxy-token-secret>
Content-Type: application/json
Modal-Routing-Affinity-Key: <opaque-application-run-id>

{"model":"<verified-request-model>","messages":[{"role":"user","content":"Summarize the supplied community proposal."}]}
```

**Recommended Python integration:** a future adapter can use `AsyncOpenAI` with the verified `/v1` base and combined proxy value, or async HTTP. Avoid appending `/v1` twice. That is a transport design, not a tested Modal SDK invocation. Modal's management SDK/CLI is not required in the application path merely to call an existing endpoint. No management/deploy command was run.

Expected Chat projection is choices/message/finish_reason/usage under the documented compatible protocol; exact optional fields and SSE behavior remain **Unverified** until tested. Do not use a fabricated full successful response as evidence.

## 4. Model capability verification plan

| Capability | What documentation establishes | What the Modal adapter must verify |
| --- | --- | --- |
| Reasoning effort | Meta Open template has low/medium/high/xhigh, default xhigh [D6] | Accepted request field/levels; output budget includes what; reasoning separation |
| Native function calling | Open is designed for sequential tool use [D1, D6] | Actual function schemas, call IDs/arguments, parallel behavior, replay and finality |
| Structured JSON | No Spark-specific Modal strict-decoding contract established | response_format/text.format acceptance, strict subset, adversarial conformance |
| Multimodal | Library lists image/audio/video/text [D1] | Content block formats, codec/size/duration/frame caps, feature combinations |
| Streaming | General compatible protocols [D5] | SSE events, fragmented tool args, terminal errors, usage/cancellation |
| Context | Library advertises 1M [D1] | Enforced input+output limit and tokenizer/counting method |
| Output limit | No exact Modal Spark cap verified | Maximum accepted generation budget, reasoning/truncation outcome |
| Persistence | No Meta encrypted/response-ID parity established | Storage/retention and continuation semantics |
| Web grounding | No Spark-specific Modal built-in search verified | Mark unavailable until contract proven |

**Documented upstream settings:** Meta Open recommends temperature/top_p 1.0; reasoning strengths low=8, medium=32, high=256, xhigh=512. Runtime Muse parsers are necessary in the self-host recipes. These are checkpoint/runtime facts, not proof that Modal accepts every upstream knob. [D6]

**Recommended:** start Modal experiments with text only and no tools, then single read tool, then strict proposal, then streaming/tools and media combinations. A tool call requests an action; the application validates and dispatches. Prompt-only JSON is not equivalent to provider-enforced schemas. If constrained output is unavailable, prohibit workflows requiring that capability rather than silently downgrading.

## 5. Errors, concurrency, latency, and observability

**Documented:** Shared 429 occurs at model-specific workspace concurrency; retry with exponential backoff/jitter. Dedicated has configurable autoscaling and metrics. Generic Modal cold-start guidance says readiness may take seconds to minutes because initialization/model loading follows container boot. Dedicated benchmark views generate paid traffic. [D3–D4, D7]

**Recommended error policy:** classify validation/auth/permission/capability failures as terminal until corrected; bound retry of provider/transient transport failures. Respect Retry-After when supplied. Exact Modal Spark error bodies/statuses beyond documented 429 remain Unverified. Do not copy Meta's status taxonomy as if it were Modal's.

Keep a provider semaphore and tenant fairness queue. SDK plus worker retries must share a single attempt budget. On interrupted generation, mark draft incomplete; no partially assembled tool may execute. After a lost response, reconcile application tool ledger before repeating inference. Provider failover creates a new attempt and cannot replay opaque Meta IDs/reasoning.

Measure queue time, cold/warm readiness, time to first event and first visible answer, prefill/decode, p50/p95 total latency, effective tokens/sec, successful proposal throughput, cache ratio, 429 rate, and dollars/accepted artifact. Compare identical tasks/context/effort intent against Meta, including quantization quality. Do not present upstream coding benchmark scores as AroundYou throughput evidence.

**Recommended:** separate application logs from raw prompt logging; redact secrets/participant data. Confirm retention and residency contract for the chosen mode before sending sensitive context. Dedicated isolation is not itself a no-retention guarantee. Use synthetic data first.

## 6. Billing and the proposed $100 credit

**Documented:** Spark Shared list prices are $1.25/million input, $0.15/million cached input, $4.25/million output. Shared documentation explicitly says plan-included credits cannot be used for Shared usage. Modal distinguishes gross Workspace usage budget from net spend limit; default spend limit can permit out-of-pocket charges. Environment budgets cover compute, not every workspace charge. [D1, D3, D8]

**Unverified:** whether a specific $100 promotional grant exists for this account, its expiry, eligible products, region/model restrictions, whether Shared is included by exception, and whether a payment method/overage applies. No event-specific promotion terms were supplied or verified publicly. General free compute/plan claims do not resolve this.

**Recommended pre-evaluation gate:** inspect the actual award terms and applicable balance; confirm Shared eligibility and remaining expiry; configure an explicit acceptable spend limit and local per-experiment ceiling; account for retries and all active workloads. No setup or billing change is authorized by this document.

If—and only if—the entire $100 were eligible for Shared token usage, the illustrative Phase 1 token workload ($0.02825/call) would allow about 3,539 such calls before other charges. This is arithmetic, not an entitlement, benchmark, or commitment. For Dedicated, use `eligible_credit / actual_total_compute_cost_per_hour`; include GPU count, CPU/RAM, loading/warm time, storage/egress, and region multipliers. Do not convert $100 into GPU hours using an unverified GPU price.

## 7. Limited Baseten fallback study

**Documented:** Baseten's launch page provides Spark Open at `https://inference.baseten.co/v1/chat/completions`, model `meta-models/muse-spark-open`, Bearer Baseten key, and text/image/audio/video input. [B1]

Illustrative request, not executed:

```json
{"model":"meta-models/muse-spark-open","messages":[{"role":"user","content":"Summarize this community initiative proposal."}]}
```

**Documented:** Model APIs support tool calling. The overview explicitly excludes Muse Spark Open from both structured outputs and JSON mode. Responses is stateless and requires full history; endpoint limits can differ from model-advertised maxima and even catalog values. Regions can change unless an appropriate policy is confirmed. [B2]

**Documented:** list token rates match $1.25/$0.15/$4.25 per million input/cached/output. Limits depend on account/model; 429 denotes quotas, 529 unavailable serving capacity. Usage/budget controls exist. New-account credits are advertised without a universal amount on the price page. Startup grants require admission and separate Model API credits from Dedicated/Training credits; no hackathon grant for AroundYou was verified. [B3–B5]

**Recommended verdict:** practical backup for advisory text and read-tool experiments, conditional on account access and quality tests. Not a drop-in strict-output provider for the same mandatory schema contract. Do not broaden into Dedicated infrastructure design while Modal remains unevaluated. A later explicitly approved application-validated JSON mode would be a different quality contract, not hidden parity.

**Unverified:** Spark-specific enforced output/context limits, accepted effort levels/media combinations, effective quotas, grant eligibility, and task latency. Before use, test tool replay, reject strict-output-required routing, compare evidence accuracy, inspect retention/region policy, and reconcile billed usage. No Baseten deployment/account action was performed.

## 8. Proof-of-concept gates (not executed)

1. Read-only discovery after access: exact URL/model, modes, limits, credit eligibility; no provisioning inferred.
2. Minimal text request: correct protocol/result/usage and sanitized error handling.
3. Reasoning sweep and truncation: accepted levels and usable final answer under explicit budgets.
4. Strict-schema adversarial tests: either verified enforcement or explicit unsupported status.
5. Tool loop/replay: validated completed calls only; forbidden names/args never execute; finite steps.
6. Stream fragmentation/disconnect: no partial execution; terminal failures surfaced; usage reconciled.
7. Multimodal fixtures: supported media formats/limits and source-linked uncertain observations.
8. Context boundaries/concurrency: measured effective window, 429/backpressure, cold/warm p95.
9. Spending reconciliation: reserved ceiling vs actual usage, including failed/abandoned attempts.
10. Baseten fallback: unavailable strict output blocks that route; no Meta state transferred.

## Official sources (reviewed 2026-10-27)

- D1 [Modal Spark Open library](https://modal.com/library/meta/muse-spark-open)
- D2 [Modal Spark launch](https://modal.com/blog/meta-muse-spark-open-now-available-on-modal)
- D3 [Shared Endpoints](https://modal.com/docs/guide/shared-endpoints)
- D4 [Dedicated Endpoints](https://modal.com/docs/guide/dedicated-endpoints)
- D5 [Endpoints](https://modal.com/docs/guide/endpoints)
- D6 [Meta Open settings](https://dev.meta.ai/docs/muse-spark-open/settings)
- D7 [Cold start performance](https://modal.com/docs/guide/cold-start)
- D8 [Modal budgets/spend limits](https://modal.com/docs/guide/budgets)
- B1 [Baseten Spark launch](https://www.baseten.co/resources/changelog/muse-spark-open-and-nemotron-35-super-vl-available-on-baseten/)
- B2 [Baseten Model APIs](https://docs.baseten.co/inference/model-apis/overview)
- B3 [Baseten pricing](https://www.baseten.co/pricing/)
- B4 [Baseten pricing/limits](https://docs.baseten.co/inference/model-apis/pricing-and-limits)
- B5 [Baseten startup programme](https://www.baseten.co/startup-program/)
