# Modal structured extraction fix and single live verification

2026-11-03. **The additional authorized inference succeeded.** No automatic retry, batch, Spark call, Prompt 8 or frontend work occurred.

## Diagnosis without guessing the previous output

The old implementation already used `apply_chat_template(tokenize=True, add_generation_prompt=True)` and decoded only tokens after the input sequence. Those boundaries were correct. It passed only input IDs to generation, omitted explicit attention mask/PAD/EOS configuration, inherited irrelevant sampling settings, allowed 768 unconstrained output tokens, and attempted `json.loads` without schema/provenance checks in the provider runtime. It retained no generated text or termination metadata. The earlier 422 proves JSON decoding failed after generation, but its exact formatting/content/truncation cause remains unknown.

The corrected path uses the template's returned dictionary (input IDs plus explicit attention mask), disables input truncation and rejects inputs exceeding 4096 tokens, explicitly sets PAD/EOS from the pinned tokenizer, creates a fresh deterministic GenerationConfig (one beam, no sampling), and limits new tokens to 384. It decodes only new tokens with cleanup disabled, records EOS vs length termination, and rejects a length-limited output without EOS. No JSON repair, fence stripping or fabricated defaults are applied.

## Genuine constrained generation

Pinned Qwen model/revision remains `Qwen/Qwen2.5-1.5B-Instruct@989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. Architecture, T4, authentication, maximum one container/input, zero warm containers, 30-second scale-down, 120-second function/request timeout and zero retries are unchanged.

Added `lm-format-enforcer==0.11.3` through its [official Transformers prefix-token integration](https://github.com/noamgat/lm-format-enforcer/blob/v0.11.3/lmformatenforcer/integrations/transformers.py). An offline test found JsonSchemaParser did not accept the escaped quotes needed by our enum excerpts. The final implementation uses its StringParser/UnionParser to constrain the complete finite language of valid serialized JSON candidates instead. This is actual token filtering, not a prompt-only JSON claim.

The compact schema permits exactly one lesson containing `source_id`, a fixed neutral title and an exact source excerpt. The deterministic preprocessor offers bounded existing operational field quotes; the model chooses among those quotes and IDs. Grammar branches bind each quote to its source ID. There is no generated free-form outcome, confidence, plan edit or title claim. This deliberately narrows extraction to **model-selected factual excerpts**, not generalized explanatory lessons. Applicability and existing source classifications remain copied from authorized records and require human review. Both provider-side strict parsing/provenance validation and the existing backend checks remain in place.

See [Transformers 4.49 generation contract](https://huggingface.co/docs/transformers/v4.49.0/en/main_classes/text_generation). The final call's logs contain no previous missing-attention-mask/inherited-sampling warnings. The existing SDPA/sliding-window support warning remains; no claim is made that this was the original failure's cause.

## Private diagnostics

Malformed/schema-invalid generated output now produces a bounded private workspace Dict record containing model/revision, canonical minimized-source digest, character/token counts, EOS/length/unknown finish reason, possible truncation, JSON error/position when applicable, timestamp and at most 320 characters of **irreversibly redacted** text. Every content character is replaced; only JSON punctuation/whitespace remains. The store is capped at 100 records, accessible through authenticated Modal workspace tooling, with no public diagnostics endpoint. HTTP failure returns only an error code and opaque diagnostic ID. Original evidence, personal descriptions, tokens and credentials are not retained in diagnostics. This is diagnostic storage, not an alternative operational memory database.

Redaction and malformed/truncated diagnostic generation were tested offline. This live call succeeded, so the malformed-generation remote persistence branch was not exercised by a real failure; no extra request was made to force one.

## Real result and PostgreSQL state

Same synthetic event: `01b19638-0f30-47ff-af9f-cfc51bde2354`; immutable outcome source `df15bc58-d9be-4334-a4f3-98f7aa73d994`, revision 1. Its original data class remains synthetic. The separate explicit synthetic verification option is used only by the harness; normal extraction does not admit synthetic sources.

- Endpoint: https://khushira2244--aroundyou-memory-extraction-extractor-extract.us-east.modal.run
- Modal call: `fc-01M6G467HA4HRYF65GRJBAN0T2`; exactly one new POST, no redirects/retries.
- HTTP **200**, **45.340 seconds** wall time.
- Input **458 tokens**, output **130 tokens**, **EOS** termination, constrained generation **4.834 seconds**; provider function execution **5.019424 seconds**. This is elapsed generation/function time on T4, not a CUDA kernel-time measurement or total billed GPU occupancy.
- Genuine model chose an exact `actions_attempted` field quotation from the source, containing the existing work/stage IDs. Strict JSON shape, permitted source reference and exact source quotation passed.
- Minimized source digest `8d81e5ebaec0f9b30bef244fda245077683aa21b93ecf94ea55b1dfbf4b77b10` was independently recomputed from PostgreSQL after the call and matched provider metadata. Persisted assertion was rechecked against the genuine response.
- Memory run `4853733d-cb9f-40ee-a86b-023581429f50`: **succeeded**.
- Candidate `0f87d485-5376-4841-994b-967b693a15a6`: **candidate/pending human review**, one exact persisted source link, no review decision, **ineligible for trusted retrieval**.
- An attempted human publish was rejected with `synthetic_memory`. No event was promoted to real, no plan/resource/permission state changed, and no trusted lesson was published.

The new harness flag `--structured-v2` has a separate durable exclusive one-shot marker. The original failed run/marker were preserved. The new run uses the appropriate blocker-recovery extraction purpose so the old failed event-review run is not reset or reused. This is the newly authorized attempt, not an automated retry.

Backend `MODAL_MEMORY_ENABLED` remains **false** as left by the preceding task; endpoint/proxy credentials remain locally configured and ignored. This task verified the provider and candidate pipeline directly without enabling unsolicited future calls. All inference authorization for this task is exhausted. The deployed endpoint remains available, with **zero running containers** confirmed after scale-down.

## Usage and cost observations

Before work, workspace summary showed $0.03245454 cumulative metered and $0 billed. After the successful call it showed **$0.06635581 cumulative metered**, $0.06000000 credit adjustment plus $0.00635581 network allowance, **$0 billed**. Observed incremental metered difference: **$0.03390127**, including this task's build/cold-start/idle/network activity, not merely model token generation. These are asynchronous snapshots, not a guaranteed final invoice.

Daily deployed-app T4 resource cost increased from the previous observed $0.01868326 to $0.03769447; CPU $0.01234514, memory $0.00422448 and egress $0.00618394 were cumulative values. Remaining credit balance/expiry were not exposed. No always-on GPU was provisioned.

## Tests and exact commands

Offline tests first caught the escaped-quote grammar problem; after correction, 15 focused offline tests passed. Then **68 selected tests passed against isolated PostgreSQL**, including new malformed/truncated/unsupported-source/outcome cases proving failed jobs create no memory and have one attempt; original memory, supersession, privacy and manual recovery/consent/activation regressions also passed. One existing dependency deprecation warning remains. Python compilation and `git diff --check` passed (existing CRLF warnings only).

```powershell
$env:TEMP="$PWD/backend/.tmp"; $env:TMP=$env:TEMP
backend/.venv/Scripts/python.exe -m pip install lm-format-enforcer==0.11.3
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_modal_structured.py backend/tests/test_modal_activation.py -q
backend/.venv/Scripts/python.exe -m compileall -q backend/modal_memory
backend/.venv/Scripts/python.exe backend/tools/run_postgres_tests.py tests/test_modal_structured.py tests/test_modal_activation.py tests/test_prompt7_workspace.py tests/test_group1.py tests/test_group5.py tests/test_group5_resume.py -q
# From backend:
$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUTF8='1'
.venv/Scripts/python.exe -m modal deploy modal_memory/app.py
# From repository root:
backend/.venv/Scripts/python.exe backend/tools/verify_modal_memory_live.py --structured-v2
backend/.venv/Scripts/python.exe -m modal function info aroundyou-memory-extraction/Extractor.* --json
backend/.venv/Scripts/python.exe -m modal function logs aroundyou-memory-extraction/Extractor.* --all-variants --tail 12
backend/.venv/Scripts/python.exe -m modal function calls aroundyou-memory-extraction/Extractor.* --all-variants --tail 3 --json
backend/.venv/Scripts/python.exe -m modal billing summary --json
backend/.venv/Scripts/python.exe -m modal billing report --for today --show-resources --json
backend/.venv/Scripts/python.exe -m modal container list --json
git diff --check
```

A cached redeploy confirmed no source changes before the live call; it performed no inference. Changes: `backend/modal_memory/app.py`; added `backend/modal_memory/{__init__,structured}.py`; added `backend/tests/test_modal_structured.py`; updated `backend/tools/verify_modal_memory_live.py` and `backend/pyproject.toml` optional offline-test dependency. Local ignored result/one-shot files preserve the real response and verification metadata. No recovery/persistence rebuild, migration, demo fixture change or frontend change.
