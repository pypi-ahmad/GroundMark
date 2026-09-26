# PP-DocLayoutV3 runtime and parsing integration

This checkout attempts local V3 analysis before Sol extraction in both CLI and GUI parsing. Dependencies remain an optional packaging extra. If V3 fails, extraction uses Sol blocks with explicit fallback diagnostics; there is no GUI off-switch. This integration is not part of the published v0.1.1 release.

## Install and predict

Use the existing Python 3.14+ project and lockfile:

```powershell
uv sync --extra layout
uv run --extra layout python -c "from PIL import Image; from src.layout_detector import get_layout_runtime; print(get_layout_runtime().predict(Image.open('tests/fixtures/invoice.png')))"
```

Base installs do not need Torch, torchvision, Transformers, Hugging Face Hub, or OpenCV. Importing the runtime itself does not import these packages, load weights, or contact the network. A missing extra raises an actionable `LayoutModelUnavailable` on preparation or prediction; the active parser catches it and uses Sol. `run.cmd` still runs `uv run groundmark`. Use `uv run --extra layout groundmark` when you want uv to retain the optional dependencies for that invocation.

`get_layout_runtime()` returns one lazy runtime per process. Its configuration is fixed on first access; restart the process to change it. `prepare()` resolves and loads the model and verifies a small complete inference probe; repeated preparation reuses the ready model. Its frozen `LayoutReadiness` reports actual device, safe fallback reason, elapsed preparation seconds, and `reused`. A direct first prediction also prepares lazily. A lock serializes initialization and predictions. Later calls reuse the same model/processor; document images and results are not globally cached.

`predict(image, page_number=1)` accepts one PIL image and returns a runtime-local `LayoutPageResult` with page dimensions, regions, model/revision/engine, actual device, and fallback reason. Each immutable `LayoutRegion` retains class ID, canonical label, score, original pixel XYXY box, polygon points, and native reading-order rank. The runtime produces no transcription. Separate conversion and reconciliation provide normalized boxes and validated artifact metadata.

## Model cache and offline use

The default resolver first looks for the pinned snapshot in Hugging Face's standard user cache. A missing/incomplete snapshot triggers a first-use download of only these files:

- `config.json`
- `preprocessor_config.json`
- `model.safetensors`
- `inference.yml`

The source is [PaddlePaddle/PP-DocLayoutV3_safetensors](https://huggingface.co/PaddlePaddle/PP-DocLayoutV3_safetensors/tree/97d101e6db2642e162a1d05392d1b0231c91033e), revision `97d101e6db2642e162a1d05392d1b0231c91033e`. File SHA-256 checks pin the exact official files, including for local overrides. Weights are not package contents or Git assets. Cache hits work without network access. Existing standard Hub cache configuration is respected.

For offline use, set `GROUNDMARK_LAYOUT_MODEL_DIR` to an existing directory containing those four unmodified files. The resolver does not download, overwrite, or migrate that directory. Invalid paths, missing files, and checksum mismatches fail explicitly; they never silently select another model. Earlier files in ignored `data/models/` are preserved and can be used with this override.

Configuration is validated in `src/config.py` and documented in `.env.example`. Direct Python callers must load their environment themselves; importing the runtime does not discover or load dotenv files.

## Devices and failures

`GROUNDMARK_LAYOUT_DEVICE` accepts:

- `auto` (default): try CUDA, then CPU if CUDA is unavailable or its placement/probe fails.
- `cpu`: skip CUDA entirely and verify CPU inference.

The runtime loads FP32 weights on CPU once, uses `.eval()` and `torch.inference_mode()`, and moves that same model for probing. CUDA success requires model parameters, input tensors, and output tensors on CUDA, plus successful synchronization and official postprocessing. It records the device actually used, not the requested mode. A CPU fallback must pass the same full probe before serving pages. Fallback reasons are `cuda_unavailable` or `cuda_probe_failed`; explicit CPU mode is not a fallback.

`LayoutModelUnavailable` exposes a safe reason code and remediation text for missing dependencies, download failure, invalid model files, model loading failure, or failure of the attempted devices. Device failures also record attempted devices. Raw native/provider exception text is not included in the public message. A later page failure raises `LayoutInferenceError` without silently retrying on a different device.

## Engine and geometry

The implementation uses Transformers 5.17.0 with Torch 2.14.0, torchvision 0.29.0, Hugging Face Hub 1.33.0, and headless OpenCV 5.0.0.93. The checkout lock selects official CUDA 13.2 wheels for Torch/torchvision using an explicit index restricted to those packages. CUDA auto-selection and native Windows CPython 3.14 execution were verified during development. Installed wheels outside this checkout may resolve a different Torch build; successful probing is still required.

The official [V3 ONNX artifact](https://huggingface.co/PaddlePaddle/PP-DocLayoutV3_onnx/tree/46bbdf188bb0a772c08aed74882ce7e51a8f1ea6) exists, but this runtime uses neither it nor Paddle weights. Transformers already supplies V3 preprocessing, model execution, masks, reading order, and postprocessing. There is no custom model-head decoding, alternate model, or second lockfile.

The processor internally resizes to 800×800 with bicubic interpolation, rescales by 1/255, and uses mean 0 / standard deviation 1. The official postprocessor receives the original image's `(height, width)`, returning `scores`, `labels`, `boxes`, `polygon_points`, and `order_seq`. The fixed upstream 0.5 threshold applies to detection and masks, not matching IoU. Native ranks are zero-based over the original queries; filtering leaves gaps and ranks may repeat. Preserve them without renumbering. No application rasterization profile changes.

Canonical labels, IDs 0–24:

```text
abstract algorithm aside_text chart content display_formula doc_title
figure_title footer footer_image footnote formula_number header header_image
image inline_formula number paragraph_title reference reference_content seal
table text vertical_text vision_footnote
```

## Verification

Offline tests inject a snapshot resolver and backend factory into `LayoutRuntime`. They exercise download triggering/cache reuse, missing dependencies, CUDA placement/probe failure, CPU failure, actual-device reporting, serialization, singleton reuse, validation, and base imports without the extra. No test needs model weights or a Sol request.

Run `uv run --extra layout python -m pytest tests`. Real inference checks are separate from this suite. Earlier runtime checks used the local invoice fixture and existing pinned files, with network blocked. The active-path integration is verified with fake runtimes and fake Sol responses, not live paid calls. Runtime support and synthetic tests do not establish layout accuracy or Sol transcription quality. Real-page calibration remains open.

On 2026-09-26, separate native Windows CPython 3.14.7 processes passed preparation, invoice-fixture prediction, geometry conversion, and ready-model reuse with explicit CPU and auto-selected CUDA. Both used the existing pinned local files with network blocked and returned one region on the 900×620 raster. Preparation/prediction elapsed times were 11.274s/1.127s on CPU and 10.312s/0.360s on CUDA; these single-run smoke timings are not benchmarks. Neither check called Sol. CUDA-to-CPU failure recovery is covered by injected offline tests, not by intentionally breaking the installed GPU runtime.

## Active page path and saved artifacts

`parse_document` prepares V3 once before the first Sol request, then processes selected pages in source order. `parse_page` decodes the exact raster payload used in the Sol image request and runs V3 once on that page. The existing 200-DPI/1,600-pixel raster profile is unchanged. Conversion checks page identity and dimensions before normalizing geometry. Both strict Sol prompts receive `given_layout`; the complete image remains the transcription source. An empty successful detection result supplies empty hints and still allows transcription.

`given_layout_json` includes stable original region identifiers, canonical labels, class IDs, outward-rounded six-decimal normalized boxes, four-decimal scores, and native order. It sorts by order then original index. Required hints must fit 300 regions and 64 KiB; exceeding either bound triggers Sol-only fallback instead of dropping regions. Valid nonrectangular polygons with at most eight vertices are included only when the rounded contour and byte budget permit. Matching always uses full-precision geometry, not prompt rounding. Raw labels and full polygons remain in saved metadata.

After strict Sol validation, reconciliation runs before `ParseResult` and every renderer, annotation, crop, export, and chat consumer. The artifact-only `layout_metadata` field contains `LayoutPageArtifact` entries: normalized layout plus nullable reconciliation details. It records all regions, model/device provenance, policy, candidate evidence, and block decisions. Analysis is retained if Sol later fails; there is no reconciliation entry for an unusable page. These frozen, extra-forbidden metadata models validate geometry and references, including accepted boxes against output blocks. Strict `LegacyParsePage` and `ParsePage` schemas remain unchanged. `schema_version: 2` remains valid; older JSON without metadata loads with an empty list.

Parser initialization failure uses Sol-only extraction across the selected range without retrying V3 on each page. Streamlit prepares on each valid Parse click; failure warns, clears stale results, and passes the safe failure to the parser without a second preparation attempt. Reruns do not repeat extraction. Page inference, conversion, or projection failures send empty region hints with the full image. Reconciliation failure retains the validated Sol blocks, without another paid call. Diagnostics retain the Sol outcome, provider metadata, and usage, plus `layout_fallback: true` and safe `layout_stage`/`layout_code` fields. Successful fallback pages feed rendering, exports, annotations, chat, and subsequent context. Invalid source images and Sol validation/content-filter failures still fail the page.

The CLI's existing progress channel now distinguishes preparation, readiness, and page completion; only page completion advances counters. Safe page diagnostics retain `layout_device`, `layout_seconds`, and `page_seconds` (nullable for older files or unattempted work). Document-run timings exclude initial preparation, rasterization, and exports. The shared `layout_match_counts` helper derives accepted, unmatched, and review counts without copying text or raw labels into diagnostics. Inspect them in the UI's Layout summary or the CLI's page status; full evidence remains in JSON. Missing reconciliation produces null counts. Review decisions can overlap accepted matches.

## Offline conversion and reconciliation

### What fallback means

| Situation | Result | Where to inspect it |
| --- | --- | --- |
| V3 misses content or returns no regions | Sol can still transcribe the complete image; unmatched Sol blocks keep their boxes and positions. | `layout_metadata[*].reconciliation.decisions` and candidate evidence |
| V3 region is weak, ambiguous, split/merged, or disagrees with the Sol role | No geometry/order replacement for that block; all Sol fields survive. | Decision `reasons`, accepted `region_index`, and unmatched region indices |
| V3 preparation, prediction, conversion, or hint projection fails | Sol receives the full image and empty hints. | Page diagnostic `layout_fallback`, `layout_stage`, and `layout_code` |
| Reconciliation fails after Sol validation | Validated Sol blocks are retained without another model call. | Page diagnostic plus any retained layout analysis |
| Sol is filtered or returns an invalid response | That page fails; independent later pages continue. | Sol outcome and provider/filter diagnostics |

Rejected or missing matches do **not** set the page-level `layout_fallback` flag: reconciliation succeeded and recorded a conservative decision. A successful Sol fallback also does not make a document partial by itself. Review counts are cases to inspect, not measured errors or an automatic review pass. Unmatched V3 regions remain metadata and never create empty Markdown blocks.

`src.layout_reconcile` consumes already-produced runtime results and Sol pages. It performs no inference, network access, file writes, or environment loading, and works without the layout extra:

```python
from src.layout_reconcile import convert_layout, reconcile_page

layout = convert_layout(runtime_result)  # LayoutPageResult from the reusable runtime
result = reconcile_page(sol_page, layout)  # ParsePage, with the same page number and dimensions
reconciled_page = result.page
review_metadata = result.metadata.model_dump(mode="json")
```

Neither input is mutated. The copied page changes only accepted boxes and the positions of matched blocks. Every Sol ID, type, text, confidence, table cell, and detailed `BlockStructure` field is preserved. The active parser stores the returned evidence separately in `ParseResult.layout_metadata`, never in the strict Sol response schemas.

### Geometry and failures

Conversion retains each region's original index, class ID, raw label, score, pixel XYXY box, pixel polygon, native order, and model/device provenance. Canonical labels and role hints are separate from raw labels; the current runtime supplies canonical labels, but conversion does not rewrite an incoming label.

Boxes are clipped to `[0, width] × [0, height]`, then X coordinates are divided by width and Y coordinates by height. This uses the runtime's original page dimensions, not the model's internal 800×800 input; it does not change rasterization. Polygons use edge/rectangle intersection clipping, not independent vertex clamping. Original vertices and clipped normalized vertices are both retained, with clipping flags. Consecutive duplicate vertices and a repeated closing vertex are removed only from the normalized contour.

Conversion rejects nonfinite values, unsupported class IDs, invalid scores/ranks, nonpositive dimensions, boxes without positive page intersection, and degenerate or self-intersecting polygons. A clipped contour requiring disconnected rings is rejected rather than inventing a connecting shape. Any invalid region fails the conversion with `LayoutConversionError(code, page, region_index)`; no partial converted page is returned. Page identity/dimension mismatch also raises this typed error. Public messages contain safe codes and indices, not transcription or native error details.

Polygons are retained **as metadata only**. Matching, annotations, and figure crops use rectangular `BBox` values. This is not polygon rendering or polygon-based matching. Figure crops must be generated from the reconciled page: filenames depend on block positions, so a pre-reconciliation crop map must not be reused after reordering.

### Initial matching policy (uncalibrated)

`ReconcilePolicy` is a validated Python argument, not an environment variable or GUI switch. New matches use the `conservative-v2` policy (older `conservative-v1` metadata still loads). This policy is an initial evaluation rule, not an accuracy claim:

| Parameter | Initial value | Meaning |
|---|---:|---|
| `min_score` | 0.80 | Minimum detector score |
| `min_coverage` | 0.90 | Minimum intersection/Sol area **and** intersection/V3 area |
| `max_center_distance` | 0.05 | Maximum Euclidean center distance in normalized coordinates, divided by √2 |
| `min_iou_margin` | 0.10 | Minimum best-versus-runner-up IoU advantage on both sides |
| `significant_coverage` | 0.80 | Either directional coverage creates a significant-overlap edge |

Only boxes with positive intersection become candidates. Missing, nonfinite, out-of-range, degenerate, or wrong-page Sol boxes remain unchanged and ineligible; they are never guessed or silently clipped. Candidate ranking is descending IoU, ascending center distance, descending detector score, then original block/region indices. Matching requires mutual best candidates and every threshold above. Exact IoU ties remain ambiguous even if `min_iou_margin` is explicitly set to zero. There is no assumed IoU 0.5 matching threshold; the runtime's independent detection/mask threshold remains unchanged.

Before accepting matches, significant-overlap edges form bipartite components. One Sol block linked to multiple regions is a `split`; multiple Sol blocks linked to one region is a `merge`; larger components are `many_to_many`. All are refused, including nested detections. This guard considers geometry regardless of labels or score, deliberately favoring review over snapping text into incomplete geometry. Weak overlap, low scores, distant centers, non-mutual choices, ambiguity, role disagreement, and raw/canonical label disagreement also preserve the Sol box and original position.

Accepted matches use the V3 box directly, without averaging boxes, splitting text, or merging blocks. Matches with known ranks are sorted by `(rank, original Sol index, region index)` and placed only into their original occupied slots. All other blocks retain their exact positions. Missing ranks allow geometry replacement but no movement; repeated ranks preserve original Sol order. Gapped ranks are not renumbered.

Metadata retains all V3 regions, every positive-overlap candidate's IoU, directional coverages, center distance, score and rejection codes, per-block original/output positions and accepted region index, unmatched region indices, and the effective policy/version. A nonempty decision `reasons` tuple identifies a review case; missing order can accompany an accepted geometry match; role/label disagreements reject the match. No empty transcription blocks are created for unmatched regions. Metadata uses original indices, not extracted IDs, because Sol IDs can repeat.

### Conservative role hints

Hints never retype Sol blocks or change Clean-view visibility. The detector's role hint must equal the Sol block type, and raw/canonical detector labels must agree, before geometry/order can be replaced. Otherwise Sol's block stays unchanged. This deliberately also preserves lists and key/value blocks when V3 only labels them as generic text.

| Role hint | Canonical V3 labels |
|---|---|
| title | `doc_title` |
| heading | `paragraph_title` |
| table | `table` |
| figure | `chart`, `image`, `header_image`, `footer_image`, `seal` |
| page_header | `header` |
| page_footer | `footer` |
| marginalia | `aside_text`, `footnote`, `vision_footnote` |
| text | `abstract`, `algorithm`, `content`, `display_formula`, `figure_title`, `formula_number`, `inline_formula`, `number`, `reference`, `reference_content`, `text`, `vertical_text` |

### Evaluation boundary

`tests/test_layout_reconcile.py` uses synthetic data only: clipping/polygons, two columns, furniture, missing/invalid boxes, split/merge/nested detections, ties and threshold boundaries, no matches, field preservation, base imports, and current rendering/crop compatibility. Run it with `uv run --no-sync python -m pytest tests/test_layout_reconcile.py`; no model weights or Sol request is needed.

Before claiming real-page quality, collect reviewed page pairs covering these cases, label correct one-to-one matches and unsafe snaps, and compare accepted-match precision, retained-text coverage, refusal reasons, and reading order. Use the emitted candidate evidence to sweep policy settings on a calibration set, then verify them on held-out pages. Do not treat synthetic tests or the default thresholds as real-page calibration.
