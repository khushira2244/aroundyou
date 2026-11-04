# Real SAM 3.1 garbage-photo verification

Date: 2026-11-03. Exactly **one new live SAM request**; zero Spark requests, zero retries. The optional `plastic cup` request was unnecessary after positive bag segmentation.

## Outcomes

| Boundary | Result |
|---|---|
| API transport | HTTP 200, model `sam-3.1`, status `completed`, provider error `null` |
| Positive segmentation | 3 object records, 3 nonempty box tokens, 3 nonempty mask records for `garbage bag` |
| Adapter parsing | 3 normalized boxes parsed, matching raw box count |
| Persistence | Original private image and source-linked AI run verified in development PostgreSQL |
| Visual interpretation | Not live tested in this task; no Spark call authorized or made |

The original attached PNG was used without resizing or substitution: **637×424**, **522,363 bytes**. Its SHA-256 is `e94eb8b90244a04949241dc7b4c0eb22e6c304932e38b8969980bc143a9501f8`. The verification checked that the data-URL payload decoded to those exact bytes and that private storage, asset metadata and AI-run source hash all matched.

## Request and raw response

Endpoint: `POST https://api.meta.ai/v1/responses`. Input was one user message containing `input_text: garbage bag` and the actual PNG bytes in an `input_image.image_url` data URL. `model: sam-3.1`, `stream: false`, existing 45-second timeout. It satisfied existing 2 MB/2048-pixel analysis limits.

Relevant raw response shape:

```text
model: sam-3.1
status: completed
error: null
output[]:
  type: message
  content[]:
    type: output_text
    text: <0f>...<|box;...|><|mask;...|>,...
    annotations, logprobs
```

There was no top-level `output_text` field. The adapter correctly read `output[].content[].text` where `type == output_text`. Other top-level fields included id/object, timestamps, usage, incomplete_details, tool settings and sampling settings. No unsupported output content type was encountered. Usage reported `images_processed: 1` and zero token counters; these are provider usage fields, not proof that the request was free.

The private full raw JSON is retained locally at `backend/.tmp/sam-garbage/1-raw.json` and in this verification run's PostgreSQL context. Large mask payloads and input data URLs were not printed or placed in this document.

## Geometry and smallest correction

Returned pixel corners, inclusive:

| Source region | x1 | y1 | x2 | y2 |
|---|---:|---:|---:|---:|
| Right bag | 447 | 113 | 611 | 284 |
| Central bag body | 286 | 190 | 502 | 392 |
| Left bag | 45 | 37 | 240 | 287 |

These regions correspond spatially to the three visible bag areas. They do not establish whether nearby items are contained inside a bag, whether all litter is collected, or whether the area is clean.

There was **no raw-geometry-to-zero-box parser failure**. Inspection did reveal a one-pixel normalization error: SAM's x2/y2 are inclusive, while our widths/heights used subtraction alone. `backend/app/execution/media.py` now uses `(x2-x1+1)/width` and `(y2-y1+1)/height`, validates corners strictly inside the source dimensions, and permits one-pixel regions. The genuine saved response was reparsed locally; no second paid request was used. Previous normalization was retained in run provenance.

Mask wire payloads are preserved, not decoded into raster masks or rendered. Positive mask-record output is verified; mask raster decoding remains outside the current implementation.

## Correct evidence linkage

- Event: `1bae104c-9bbd-42b6-a234-039136ef85ab` (existing synthetic verification event).
- Report: `9c8acd15-29d2-4722-9c0c-9720956c3fba`.
- Evidence: `f36d3e0a-ecc2-45d4-ac92-371eb7c56f18`.
- SAM-only verification run: `42ee9ab0-ae9c-4db7-b4cd-3fdb84aabc57`.

Original bytes were uploaded through existing evidence APIs and stored privately. The run stores evidence ID/revision, report ID/revision, event/plan, exact source hash, requested concept, raw output, normalized geometry and audit references. The report explicitly says this photo is an independent model test, not evidence that the synthetic education work occurred. No work requirement, plan, human review decision or verified progress was changed.

This deliberately invokes the existing `segment()` function independently and saves a SAM-only verification run. The combined production `segmentation-runs` action also invokes Spark, so it was **not** called under SAM-only authorization. Thus the SAM transport → positive geometry → parser → source-linked storage chain is verified; the combined live UI/Spark workflow on this photo is not.

## Spark boundary: code inspection only

The existing integration can receive the original photograph, actual SAM box/mask-count observations, participant report text and actual work requirements. `perform()` supplies the same original image, `report_claim`, `work`, evidence ID/hash and structured SAM observations. It excludes the large raw mask wire from the Spark prompt. It does not automatically accept completion.

For the hypothetical claim “All garbage has been collected and the cleanup task is complete” versus “Collect litter and leave the cleanup area free of exposed waste,” Spark can evaluate the original photograph and uncertainty. SAM bag detections alone cannot validate that claim. No cleanup requirements were injected into the unrelated education plan, and no Spark evaluation was executed in this task.

## Sources and verification

Official documentation reviewed 2026-11-03:

- [SAM segmentation input and non-streaming support](https://dev.meta.ai/docs/sam/segmenting)
- [Segmentation wire grammar and inclusive box corners](https://dev.meta.ai/docs/sam/reading-segmentation)

Files created: `backend/tools/verify_sam_garbage.py`, `backend/tools/replay_sam_garbage.py`, `backend/tests/test_sam_segmentation_parser.py`, this report. Modified: `backend/app/execution/media.py` for inclusive coordinate normalization only. Local raw/results/budget files remain ignored.

Commands:

```powershell
backend/.venv/Scripts/python.exe backend/tools/verify_sam_garbage.py 'garbage bag'
backend/.venv/Scripts/python.exe backend/tools/replay_sam_garbage.py
# From backend, TEMP/TMP pointing at workspace .tmp:
.venv/Scripts/python.exe tools/run_postgres_tests.py tests/test_sam_segmentation_parser.py tests/test_prompt56_media.py tests/test_group4.py -q
git diff --check -- backend/app/execution/media.py backend/tests/test_sam_segmentation_parser.py backend/tools/verify_sam_garbage.py backend/tools/replay_sam_garbage.py
```

Live request and local source/hash replay passed. Focused regression: **26 passed**, zero failures, one existing Starlette/httpx deprecation warning. Tests used isolated real PostgreSQL and covered parser geometry, empty results, invalid coordinates, evidence privacy, transcription correction, idempotency, failed-inference retention and existing Group 4 execution behavior. Diff whitespace check passed. No browser screenshot acceptance was performed; no UI redesign was made.

Stopped after this verification. No recovery, Modal, cloud deployment or other paid inference.
