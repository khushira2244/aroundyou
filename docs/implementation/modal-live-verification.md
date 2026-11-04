# Modal Event Memory activation verification

2026-11-03. **Deployment succeeded; one real inference ran; extraction validation failed.** No retry, Spark request, batch job or additional model call was made.

## Deployment and authentication

Active CLI profile/workspace: `khushira2244`; environment `main`. Installed Modal SDK **1.6.3**, recorded as an optional backend dependency. The prepared definition imported successfully and deployed as app `ap-AuCTBNaV3Mv6NKsz8EKFHm`, function `fu-H7Cx4zV9s7m0PJGXROOS54`.

Endpoint: https://khushira2244--aroundyou-memory-extraction-extractor-extract.us-east.modal.run

[Deployment dashboard](https://modal.com/apps/khushira2244/main/deployed/aroundyou-memory-extraction).

Provider function info verified T4 x1, 2 CPU, 8192 MiB host memory, maximum one container, one concurrent input, 120-second function timeout, zero retries, 30-second scale-down, no schedule, no mounted persistent volumes. Zero minimum/buffer values are represented as null/default zero in provider info. Container listing was empty before inference and after scale-down. The endpoint requires proxy authentication (`unauthenticated: false`); a dedicated proxy token was saved in ignored `backend/.env`. Meta credentials and existing management tokens were preserved. An initial proxy token whose local save failed was deleted before replacement; no credentials were printed.

Pinned model: `Qwen/Qwen2.5-1.5B-Instruct` at `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`; official [pinned model card](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/blob/989aa7980e4cf806f80c7fef2b1adb7bc71aa306/README.md) declares Apache-2.0. `trust_remote_code=False`, FP16, deterministic generation with 4096 input-token/768 output-token limits. [Modal proxy authentication](https://modal.com/docs/guide/webhook-proxy-auth) uses separate proxy credentials, not CLI management credentials.

First deployment attempt stopped because the Windows console could not encode build progress; the UTF-8 deployment succeeded. This was a deployment retry, not an inference retry. Initial pip installation hit a temporary-directory permission error and succeeded using the workspace temporary directory.

## The single live request

- Synthetic PostgreSQL event: `01b19638-0f30-47ff-af9f-cfc51bde2354`.
- Exact existing recovery outcome revision source: `df15bc58-d9be-4334-a4f3-98f7aa73d994` (revision 1, source digest captured in the run).
- Memory run: `ab2919ed-802e-4204-a928-f3c59fc62dcd`.
- Modal call: `fc-01M6G0BZGXW45XTGGBANDJEH0B`; container `ta-01M6G0C2SBW8B3Q8FPFBW6DE3R`.
- Exactly **one authenticated HTTP POST**, redirects disabled, transport retries zero. A durable exclusive local one-shot marker prevents accidental rerunning of the verification harness.
- HTTP **422**, body `{"detail":"Invalid structured extraction; no retries"}`.
- HTTP wall time **34.549 seconds**. Provider call execution **5.491602 seconds**, cold start **24.522028 seconds**, provider end-to-end **33.41132 seconds**. Execution time occurred on the T4 container; exact CUDA kernel time and total billed GPU occupancy were not exposed by these call metrics.

The deployed method reaches its JSON decode error only after actual model generation. Model load and generation therefore ran, but the generated text did not decode as JSON. The prepared endpoint did not retain or return that raw generated text; its exact formatting/truncation failure cannot be diagnosed from this response. No valid schema output, source-ID validation or excerpt validation can be claimed for this live result. Logs also warn about inherited sampling parameters ignored in greedy mode, the missing attention mask, and SDPA sliding-window support; these are observations, not a proven cause of the JSON failure.

No fabricated fallback candidate was inserted. The real memory run/job failure was persisted in PostgreSQL with zero candidates and one allowed attempt. At the time of this call the adapter classified all non-2xx responses as `extractor_unavailable`; the persisted run retains that historical code. The adapter now classifies 422 as terminal `invalid_model_output`, preventing an availability-retry interpretation. No rerun was made after that correction.

## Provenance and persistence boundary

The normal adapter continues to reject synthetic/unclassified sources. Only the standalone verification harness explicitly opts into synthetic source extraction; this option is not exposed through API or settings. Minimized model input includes `data_class: synthetic` and exact operational source excerpts, not personal descriptions or raw reports. The source/event classification was not changed.

Because the model returned invalid output, **pending-candidate persistence was not achieved or live-verified**. Existing PostgreSQL tests verify the candidate/review/provenance boundary; offline tests verify the explicit synthetic opt-in preserves original source references and default extraction still rejects it. Synthetic lessons remain ineligible for trusted retrieval and human publication is prohibited by the existing provenance guard. No synthetic event was promoted to real.

`MODAL_MEMORY_ENABLED=false` was restored after the failed validation. Endpoint/proxy configuration remains available locally, but the backend will not invoke it while disabled. Deployment remains available and scales to zero; no always-on GPU exists. The user's single inference authorization is exhausted.

## Billing observations

Pre-deployment billing summary reported zero. The first post-test snapshot reported metered **$0.04245454** and credit adjustment **-$0.04000000**. The latest snapshot revised those to **$0.03245454** metered and **-$0.03000000** credits, with network allowance **-$0.00245454** and billed **$0**. These are observed snapshots, not final accounting. Applied credits confirm credits were available to this usage; the CLI summary does not expose the original grant, remaining credit balance or expiry, so a $30 remaining balance is **not verified**.

Resource report for the deployed app showed T4 **$0.01868326**, CPU **$0.00519340**, memory **$0.00207510**, network **$0.00228265** at inspection. Its resource report and workspace summary are asynchronously updated and need not reconcile immediately; the summary also includes image-building/earlier stopped deployment usage. Do not equate the 5.49-second execution metric with all billed GPU time, which can include startup and idle tail.

## Commands and tests

```powershell
backend/.venv/Scripts/python.exe -m pip install modal
backend/.venv/Scripts/python.exe -m modal profile list
backend/.venv/Scripts/python.exe -m modal workspace settings list --json
backend/.venv/Scripts/python.exe -m modal billing summary --json
$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUTF8='1'
backend/.venv/Scripts/python.exe -m modal deploy backend/modal_memory/app.py
backend/.venv/Scripts/python.exe -m modal function info aroundyou-memory-extraction/Extractor.* --json
backend/.venv/Scripts/python.exe backend/tools/verify_modal_memory_live.py
backend/.venv/Scripts/python.exe -m modal function calls aroundyou-memory-extraction/Extractor.* --all-variants --json
backend/.venv/Scripts/python.exe -m modal function stats aroundyou-memory-extraction/Extractor.* --all-variants --json
backend/.venv/Scripts/python.exe -m modal function logs aroundyou-memory-extraction/Extractor.* --all-variants --tail 30
backend/.venv/Scripts/python.exe -m modal billing report --for today --show-resources --json
backend/.venv/Scripts/python.exe -m modal container list --json
$env:TEMP="$PWD/backend/.tmp"; $env:TMP=$env:TEMP
backend/.venv/Scripts/python.exe backend/tools/run_postgres_tests.py tests/test_prompt7_workspace.py tests/test_group5.py tests/test_group5_resume.py -q
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_modal_activation.py -q
git diff --check
```

**21 PostgreSQL regressions passed**, including manual recovery and consent/activation without a live extractor. **2 offline adapter tests passed**. Diff check passed with existing line-ending warnings. No frontend changes, migrations, fixture changes, recovery rebuild or cloud deployment were performed.

Files changed: `backend/app/memory/modal_adapter.py`, `backend/pyproject.toml`; added `backend/tools/verify_modal_memory_live.py`, `backend/tests/test_modal_activation.py`, this report. Ignored environment and one-shot/result artifacts were updated locally. Prepared deployment source was deployed unchanged.

Next smallest corrective step is to capture bounded generated-text diagnostics and constrain/validate JSON generation without manufacturing output. The actual malformed text is unavailable, so blindly stripping formatting is not justified. Any further live inference requires a new explicit authorization. Stop here.
