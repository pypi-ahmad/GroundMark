# PP-DocLayoutV3 runtime and parsing integration

GroundMark attempts local V3 analysis before Sol extraction in both CLI and GUI parsing. Dependencies remain an optional packaging extra. If V3 fails, extraction uses Sol blocks with explicit fallback diagnostics; there is no GUI off-switch.

## Install and predict

Use the existing Python 3.14+ project and lockfile:

```powershell
uv sync --extra layout
uv run --extra layout python -c "from PIL import Image; from src.layout_detector import get_layout_runtime; print(get_layout_runtime().predict(Image.open('tests/fixtures/invoice.png')))"
```

Base imports do not load ONNX Runtime, Hugging Face Hub, NumPy, or OpenCV through the detector. Missing inference dependencies produce an actionable V3 failure and Sol fallback. The Windows launcher runs `uv run --extra layout groundmark`, so its normal launch includes the extra. Use `uv run --extra layout` for direct checkout commands too.

`get_layout_runtime()` returns one lazy runtime per process. Its configuration is fixed on first access; restart the process to change it. `prepare()` resolves and loads the model and verifies a small complete inference probe; repeated preparation reuses the ready model. Its frozen `LayoutReadiness` reports actual device, safe fallback reason, elapsed preparation seconds, and `reused`. A direct first prediction also prepares lazily. A lock serializes initialization and predictions. Later calls reuse the same prepared session; document images and results are not globally cached.

`predict(image, page_number=1)` accepts one PIL image and returns a runtime-local `LayoutPageResult` with page dimensions, regions, model/revision/engine, actual device, and fallback reason. Each immutable `LayoutRegion` retains class ID, canonical label, score, original pixel XYXY box, polygon points, and native reading-order rank. The runtime produces no transcription. Separate conversion and reconciliation provide normalized boxes and validated artifact metadata.

## Model cache and offline use

The default resolver first looks for the pinned snapshot in Hugging Face's standard user cache. A missing/incomplete snapshot triggers a first-use download of only these files:

- `inference.onnx`
- `inference.yml`

The source is [PaddlePaddle/PP-DocLayoutV3_onnx](https://huggingface.co/PaddlePaddle/PP-DocLayoutV3_onnx/tree/46bbdf188bb0a772c08aed74882ce7e51a8f1ea6), revision `46bbdf188bb0a772c08aed74882ce7e51a8f1ea6`. File SHA-256 checks pin the exact official files, including for local overrides. Weights are not package contents or Git assets. Cache hits work without network access. Existing standard Hub cache configuration is respected.

For offline use, set `GROUNDMARK_LAYOUT_MODEL_DIR` to an existing directory containing those two unmodified files. The resolver does not download, overwrite, or migrate that directory. Invalid paths, missing files, and checksum mismatches fail explicitly; they never silently select another model. Existing safetensors snapshots are preserved but incompatible with this backend. The configured override must contain the ONNX files; it is never migrated implicitly.

Configuration is validated in `src/config.py` and documented in `.env.example`. Direct Python callers must load their environment themselves; importing the runtime does not discover or load dotenv files.

## Devices and failures

`GROUNDMARK_LAYOUT_DEVICE` accepts:

- `auto` (default): try CUDA, then CPU if CUDA is unavailable or its placement/probe fails.
- `cpu`: skip CUDA entirely and verify CPU inference.

The runtime uses ONNX Runtime 1.30.0 and the exported FP32 graph. CUDA requires an available CUDA execution provider, actual graph nodes assigned to it, and a successful complete probe. CPU shape operations within a CUDA session are normal; `cuda` does not mean every graph node runs on GPU. Session-run automatic fallback is disabled so device changes remain explicit. CUDA DLLs are loaded from the locked NVIDIA wheel dependencies using `preload_dlls(directory="")`; Torch is not required. CPU fallback creates a fresh CPU-only session and passes the same full probe.

`LayoutModelUnavailable` exposes a safe reason code and remediation text for missing dependencies, download failure, invalid model files, model loading failure, or failure of the attempted devices. Device failures also record attempted devices. Raw native/provider exception text is not included in the public message. In auto mode, an actual native CUDA execution failure gets one bounded recovery: create/probe a CPU session, retry that page once, then retain CPU for subsequent pages. Invalid inputs and malformed decoded results do not trigger recovery. If CPU preparation fails, the runtime caches the failure until process restart; no later CUDA probe occurs. If CPU preparation succeeds but the page retry fails, later pages still get one CPU attempt. Safe per-stage codes distinguish `cuda_execution`, `cpu_preparation`, `cpu_execution`, and `cpu_validation`. Raw native exception text is not saved in artifacts.

## Engine and geometry

The backend is locked to the official [ONNX artifact](https://huggingface.co/PaddlePaddle/PP-DocLayoutV3_onnx/tree/46bbdf188bb0a772c08aed74882ce7e51a8f1ea6), not the Paddle or safetensors repositories. It consumes all three published outputs: seven-column detection rows, detection count, and per-region binary 200×200 masks. The graph itself decodes boxes and zero-based native order; application code must not sigmoid the already-binary masks or recompute order.

Preprocessing follows pinned `inference.yml`: RGB, OpenCV cubic resize to 800×800, scale 1/255, mean 0 / standard deviation 1, contiguous float32 BCHW. `im_shape` is the resized height/width and `scale_factor` is resized/original height/width. The full original page request and rasterization profile sent to Sol are unchanged.

Detection selection remains score **> 0.5**, matching the PaddleX wrapper. The old Transformers processor selected **>= 0.5** and coupled its configurable threshold to mask binarization; this ONNX export fixes mask binarization at 0.5 inside the graph. No threshold was lowered, and none of these thresholds is reconciliation IoU.

A shared selection and stable native-order sort indexes rows and masks together. Gaps and ties remain; no renumbering or order-skipping labels are applied. Original floating-point AABBs are retained. Contour extraction uses rounded box coordinates, cropped masks, nearest-neighbor resizing, largest external contour, and the upstream poly-mode vertex routine. The adapted routines are in `src/layout_polygons.py`, with Apache-2.0 attribution and `LICENSE-PADDLEX`. Source: [pinned PaddleX processors](https://github.com/PaddlePaddle/PaddleX/blob/c50f5da858020db473a2285f089bb8c7bbd6afdc/paddlex/inference/models/layout_analysis/processors.py). The unusual upstream maximum-width expression is retained, not silently corrected.

PaddleX's optional NMS, box merging/expansion, overlap filtering, large-image removal, public sequential order renumbering, and shape modes other than poly are not applied. This is the export's full mask/box/order decode, not a claim of identical results to every PaddleX pipeline configuration. See [artifact research](PP-DocLayoutV3-ONNX-RESEARCH.md) for the inspected graph and upstream behavior.

Pinned SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `inference.onnx` | `45bf71750b00739a41fc209f132eb104a4d6b5bb29483c9078164d8b87cf28ba` |
| `inference.yml` | `506fcfac13b3b546ae40d7886b44126420f392adb694e3f8bb6a6286a1f90fdc` |

Canonical labels, IDs 0–24:

```text
abstract algorithm aside_text chart content display_formula doc_title
figure_title footer footer_image footnote formula_number header header_image
image inline_formula number paragraph_title reference reference_content seal
table text vertical_text vision_footnote
```

## Verification

Offline tests inject a snapshot resolver and backend factory into `LayoutRuntime`. They exercise download triggering/cache reuse, missing dependencies, CUDA placement/probe failure, CPU failure, actual-device reporting, serialization, singleton reuse, validation, and base imports without the extra. No test needs model weights or a Sol request.

Run `uv run --extra layout python -m pytest tests`. Real inference checks are separate from this suite. Live checks used the pinned ONNX files in the standard user cache. The active-path integration is verified with fake runtimes and fake Sol responses, not live paid calls. Runtime support and synthetic tests do not establish layout accuracy or Sol transcription quality. Real-page calibration remains open.

On 2026-09-27, native Windows CPython 3.14.7 passed ONNX preparation, invoice-fixture inference, geometry conversion, bounded guide creation, and ready-session reuse on CPU and auto-selected CUDA (RTX 4060 Laptop). Both returned one region on the 900×620 raster. Initial smoke preparation/page timings were 3.365s/1.157s on CPU and 5.893s/0.226s on CUDA; these are single-run operational observations, not benchmarks. ONNX Runtime warned about CPU-assigned shape nodes and ScatterND duplicate-index semantics. The smoke test does not establish accuracy or cross-device equivalence. No Sol request was made. Actual GPU failure was not induced; bounded recovery is verified with injected failures.

The final smoke check after upstream contour-coordinate rounding retained rank 142 on CPU and rank 141 on CUDA, each with one region and a full contour guide. This observed difference is preserved, not renumbered or hidden; its cause and broader quality implications were not established.

## Active page path and saved artifacts

`parse_document` prepares V3 once before the first Sol request, then processes selected pages in source order. `parse_page` decodes the exact raster payload used in the Sol image request and runs V3 on that page (with one CPU retry only after a qualifying CUDA execution failure). The existing 200-DPI/1,600-pixel raster profile is unchanged. Conversion checks page identity and dimensions before normalizing geometry. Both strict Sol prompts receive `given_layout`; the complete image remains the transcription source. An empty successful detection result supplies empty hints and still allows transcription.

`given_layout_json` includes stable original region identifiers, canonical labels, class IDs, outward-rounded six-decimal normalized boxes, four-decimal scores, and native order. It sorts by order then original index. Required hints must fit 300 regions and 64 KiB; exceeding either bound triggers Sol-only fallback instead of dropping regions. Full nonrectangular contours of any vertex count are included when the six-decimal rounded contour validates and fits. Only when needed, closed RDP simplification tries 0.25, 0.5, then 1 original raster pixel. Topology, winding, bounds, and a conservative bidirectional boundary-deviation bound including rounding must validate; the bound cannot exceed one pixel. Otherwise the contour is omitted, not the region. Base fields and contour statuses are reserved before adding vertices. Guide JSON records `contour: full|simplified|omitted`; artifact `guide_contours` additionally records region index, omission reason, and simplification bound. Redundant box contours are omitted. Guide status never modifies the original contours. Matching always uses full-precision geometry, not prompt rounding. Raw labels and full polygons remain in saved metadata.

After strict Sol validation, reconciliation runs before `ParseResult` and every renderer, annotation, crop, export, and chat consumer. The artifact-only `layout_metadata` field contains `LayoutPageArtifact` entries: normalized layout plus nullable reconciliation details. It records all regions, model/device provenance, policy, candidate evidence, and block decisions. Analysis is retained if Sol later fails; there is no reconciliation entry for an unusable page. These frozen, extra-forbidden metadata models validate geometry and references, including accepted boxes against output blocks. Strict `LegacyParsePage` and `ParsePage` schemas remain unchanged. `schema_version: 2` remains valid; older JSON without metadata loads with an empty list.

Parser initialization failure uses Sol-only extraction across the selected range without retrying V3 on each page. Streamlit prepares on each valid Parse click; failure warns, clears stale results, and passes the safe failure to the parser without a second preparation attempt. Reruns do not repeat extraction. Page inference, conversion, or projection failures send empty region hints with the full image. Runtime/conversion/guide failures retain the Sol outcome, provider metadata, and usage, plus `layout_fallback: true` and safe `layout_stage`/`layout_code` fields. Reconciliation defects instead retain the untouched Sol page and layout analysis, clear reconciliation details, and set `application_error` (`reconciliation_invariant_violation` or `reconciliation_failed`). They leave `layout_fallback` false and make the document `parsed_partial`; no additional paid call is made. Successful fallback pages feed rendering, exports, annotations, chat, and subsequent context. Invalid source images and Sol validation/content-filter failures still fail the page.

The CLI's existing progress channel now distinguishes preparation, readiness, and page completion; only page completion advances counters. Successful CPU recovery records `layout_fallback_reason: cuda_execution_failed` and stage history while leaving `layout_fallback` false. Only Sol-only fallback sets that flag. The parser does not overwrite a recovered page device with initial readiness; the UI carries current CPU status across reruns without inference. Safe page diagnostics retain `layout_device`, `layout_seconds`, and `page_seconds` (nullable for older files or unattempted work). Document-run timings exclude initial preparation, rasterization, and exports. The shared `layout_match_counts` helper derives accepted, unmatched, and review counts without copying text or raw labels into diagnostics. Inspect them in the UI's Layout summary or the CLI's page status; full evidence remains in JSON. Missing reconciliation produces null counts. Review decisions can overlap accepted matches.

If CPU preparation fails during recovery, the affected page records CUDA as its last page-execution device plus both failure stages. Subsequent calls report `recovery_unavailable` with no device: no new inference was attempted. Initial preparation timings are not relabeled as CPU recovery timings in the UI.

## Offline conversion and reconciliation

### What fallback means

| Situation | Result | Where to inspect it |
| --- | --- | --- |
| V3 misses content or returns no regions | Sol can still transcribe the complete image; unmatched Sol blocks keep their boxes and positions. | `layout_metadata[*].reconciliation.decisions` and candidate evidence |
| Candidate fails score, coverage, or class compatibility, or loses one-to-one assignment | Sol geometry and content survive. Split/merge topology alone does not reject. | Decision `reasons`, `review_flags`, and accepted `region_index` |
| V3 preparation, prediction, conversion, or hint projection fails | Sol receives the full image and empty hints. | Page diagnostic `layout_fallback`, `layout_stage`, and `layout_code` |
| Reconciliation violates an invariant or otherwise fails | Original Sol page retained; application defect makes document partial. | `application_error`, retained layout analysis, and null reconciliation |
| Sol is filtered or returns an invalid response | That page fails; independent later pages continue. | Sol outcome and provider/filter diagnostics |

Rejected or missing matches do **not** set the page-level `layout_fallback` flag: reconciliation succeeded and recorded the assignment decision. A successful Sol fallback also does not make a document partial by itself. Review counts are cases to inspect, not measured errors or an automatic review pass. Unmatched V3 regions remain metadata and never create empty Markdown blocks.

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

Invalid AABBs, class IDs, scores, native ranks, or page dimensions still fail conversion with safe codes and indices. Contours have an explicit `contour_status`: valid, missing, or unusable. A missing, degenerate, self-intersecting, or otherwise unusable contour leaves its region available for AABB matching. Finite raw vertices remain unchanged in metadata; nonfinite/malformed raw coordinates are discarded rather than serialized as NaN or invented as a rectangle. A page-clipped contour requiring disconnected rings is unusable because the saved normalized contour represents one simple ring. Page identity disagreement at reconciliation is an application invariant violation.

Matching uses the original full-precision normalized contour against Sol's rectangular box. Sol polygons are never invented. Half-plane clipping and signed area handle concave contours, including disconnected intersections joined by canceling retraced boundary edges. That intermediate boundary walk is used for area only, never saved as a contour. A valid polygon with zero overlap does not fall back to its AABB. Missing/unusable contours explicitly use AABB evidence. Figure crops retain rectangular envelopes; regenerate position-named crops after reconciliation.

### Final annotations and contour provenance

PNG and raster-PDF annotations resolve output block indices through the validated reconciliation artifact. Qualified matches draw the full normalized V3 contour in blue, never a rounded/simplified guide contour. Unmatched Sol blocks retain red Sol boxes. Unmatched detector regions draw amber `V3-only` overlays once, without transcription blocks. Analysis without reconciliation is marked `unreconciled_detector_only`; Sol boxes remain authoritative for that page. Labels show region index, V3 class, score, and native order (`?` when missing). Annotation metadata retains these references, geometry choice, model/revision/device, and explicit geometry-fallback reasons. Original contours stay in `layout_metadata`, not a competing annotation geometry representation.

The upstream poly routine can return a rectangle when mask contour extraction fails. `contour_source: mask|aabb_fallback|legacy_unknown` distinguishes this from a genuine mask-derived rectangle. Raw upstream vertices remain unchanged in `polygon_px`; upstream rectangle fallbacks have no valid normalized segmentation contour and use the original floating-point V3 AABB for matching and drawing. Existing saved artifacts without provenance load as `legacy_unknown`; their historical contours are not retroactively classified. The official largest-external-contour routine does not preserve holes or every disconnected component. Preserving its full output is not lossless mask storage.

The same normalized-to-raster mapping is used for both annotation formats. V3 raster dimensions must match the source annotation raster. Invalid artifact mappings raise an application error rather than silently drawing Sol geometry for a purported match. Crops, chat evidence, and consumers requiring rectangles continue using AABB envelopes.

For the final Windows CPU/CUDA runs, exact official preprocessing comparison, nonrectangular contour comparison, and offline saved-response evaluation, see [completion evidence](V3-INTEGRATION-COMPLETION.md). Float32 normalization multiplies by `1/255`, as upstream does; division is mathematically equivalent but was not bit-identical in the checked implementation.

### Authoritative assignment policy (provisional)

New artifacts use `v3-authoritative-v1`. Older `conservative-v1` and `conservative-v2` artifacts still load without reinterpreting their saved decisions. Sol response schemas and document schema version remain unchanged.

| Parameter | Provisional value | Meaning |
|---|---:|---|
| `min_score` | 0.80 | Minimum V3 confidence |
| `min_coverage` | 0.90 | Minimum of the **larger** directional coverage |
| `min_partial_coverage` | 0.25 | Minimum of the **smaller** directional coverage |
| `significant_coverage` | 0.80 | Either directional coverage creates a topology review edge; not an eligibility gate |

Directional coverage is intersection area divided by Sol-box area or V3-contour area (AABB area only for explicit contour fallback). These user-approved defaults are provisional containment rules, not calibrated accuracy thresholds. Runtime detection selection and mask decoding are unchanged. Historical `max_center_distance` and `min_iou_margin` fields remain readable in old artifacts but are rejected when supplied to the new active policy.

Every positive-overlap pair gets evidence. Invalid/missing Sol boxes remain untouched and ineligible. Qualified pairs must satisfy score, both asymmetric coverage bounds, and explicit class compatibility. Sort eligible pairs by descending IoU, ascending normalized AABB-center distance, then original Sol index and region index. Assign greedily when neither endpoint has been used. Confidence gates eligibility but does not break geometric ties. An eligible pair that loses assignment gets `assignment_conflict`.

Significant-overlap components yield informational `split`, `merge`, or `many_to_many` review flags. They do not reject candidates. One Sol block spanning several regions takes the best eligible region; remaining regions stay V3-only. Several Sol blocks competing for one region leave unassigned blocks unchanged. Accepted pairs retain directional coverage and topology flags so partial text coverage remains visible. No averaged geometry, leftover rectangles, duplicated text, string splitting, or invented transcription is produced.

Accepted pairs reference the original V3 region, retaining its AABB, full contour, class ID/label, confidence, and native order. Only the output block's box and position may change; all Sol content fields, IDs, semantic types, and transcription confidence are preserved. Detector classification and confidence stay in the region artifact, separate from Sol semantics.

Known-rank matched blocks are sorted by `(rank, original Sol index, region index)` into only the slots they originally occupied. Unmatched blocks and matches lacking order remain fixed anchors. Tied ranks preserve original Sol order; gaps are not renumbered. This rule preserves unmatched relative order without inventing a global detector order for them.

Candidate `geometry` is `polygon` or `aabb`, with `geometry_fallback_reason` when applicable. Rejection `reasons` are separate from informational `review_flags` (topology, missing order, label alias, or contour fallback). Accepted decisions have empty rejection reasons and may carry warnings. Artifacts validate references, one-to-one assignment, accepted thresholds, class compatibility, and output geometry. Runtime boundary checks additionally verify content ownership, unmatched geometry, detector ownership, and the interleaving permutation.

Configure through the existing Python entry points, without a GUI toggle:

```python
from src.layout import ReconcilePolicy
from src.graph import run_graph

# Illustrative stricter coverage, not an accuracy recommendation.
policy = ReconcilePolicy(min_partial_coverage=0.90)
state = run_graph("page.png", reconcile_policy=policy)
```

`parse_document`, `parse_page`, and `reconcile_parsed_page` also accept `reconcile_policy`; direct `reconcile_page` accepts `policy`. Normal parsing remains enabled by default.

### Explicit class compatibility

This mapping covers all 25 V3 classes and both Sol profiles. It gates geometry assignment only; it never rewrites Sol types, tables, heading levels, or visibility. Broad text classes can match every textual Sol type, including detailed-profile furniture. Legacy prompts do not gain new types. Existing role hints remain historical metadata, not an equality gate.

| V3 classes | Compatible Sol types |
|---|---|
| text, content, abstract, algorithm, reference_content, vertical_text | title, heading, text, list, key_value, marginalia, other, page_header, page_footer |
| doc_title, paragraph_title | title, heading, text, other |
| display_formula, inline_formula, formula_number, number | text, key_value, other |
| figure_title, reference | text, heading, other |
| aside_text, footnote, vision_footnote | marginalia, text, list, key_value, other |
| header | page_header, text, marginalia, key_value, other |
| footer | page_footer, text, marginalia, key_value, other |
| chart, image, header_image, footer_image, seal | figure |
| table | table |

No detector-driven header/footer deletion is added. Existing Clean view still follows Sol's furniture types.

### Evaluation boundary

`tests/test_layout_reconcile.py` uses synthetic data only: clipping/polygons, two columns, furniture, missing/invalid boxes, split/merge/nested detections, ties and threshold boundaries, no matches, field preservation, base imports, and current rendering/crop compatibility. Run it with `uv run --no-sync python -m pytest tests/test_layout_reconcile.py`; no model weights or Sol request is needed.

Before claiming real-page quality, collect reviewed page pairs covering these cases, label correct one-to-one matches and unsafe snaps, and compare accepted-match precision, retained-text coverage, refusal reasons, and reading order. Use the emitted candidate evidence to sweep policy settings on a calibration set, then verify them on held-out pages. Do not treat synthetic tests or the default thresholds as real-page calibration.
