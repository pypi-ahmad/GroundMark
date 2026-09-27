# V3 ONNX integration completion

Verification date: 2026-09-27. This report covers the final integration on top of the existing runtime and authoritative-reconciliation work. No commits, publication, paid Sol requests, or policy calibration were performed.

## Implemented contract

The sole weight repository remains [PaddlePaddle/PP-DocLayoutV3_onnx](https://huggingface.co/PaddlePaddle/PP-DocLayoutV3_onnx/tree/46bbdf188bb0a772c08aed74882ce7e51a8f1ea6), revision `46bbdf188bb0a772c08aed74882ce7e51a8f1ea6`. Both official files are SHA-256 verified in the user cache or explicit offline directory; see [runtime configuration and hashes](LAYOUT-V3.md). No Paddle or safetensors weight substitution occurs. Python remains 3.14+, and the normal `run.cmd` launch includes the locked layout extra.

- Every valid real extraction attempts V3, or carries an explicit preparation failure. CUDA requires actual graph placement and successful execution. Native CUDA page-execution failure permits one CPU preparation/retry, with sticky CPU reuse and bounded failure handling. Invalid inputs and malformed decoded results do not masquerade as GPU failures.
- Both Sol profiles still receive the complete page image, preceding-page context, and bounded region guide. Sol owns text, tables, IDs, transcription confidence, and semantic structure; Python renders output. Updated prompts have synthetic integration coverage, not a new paid quality evaluation.
- Qualified one-to-one matches use V3 class/confidence, original AABB, full validated contour, and native relative order. Unmatched Sol content keeps its geometry; unmatched V3 regions add no transcription. The existing provisional policy is unchanged: confidence 0.8, larger directional coverage 0.9, smaller directional coverage 0.25. These are not calibrated accuracy thresholds.
- PNG and raster-PDF overlays resolve the validated output-index-to-region mapping: blue matched contours, red unmatched Sol boxes, amber detector-only regions. Each detector region appears once. Matched unusable contours use the V3 AABB with an explicit reason. Crops and rectangle consumers retain AABB envelopes.
- Upstream empty/tiny-mask rectangle fallback is now identified as `contour_source: aabb_fallback`, rather than represented as a segmentation-derived contour. Its original returned vertices remain saved; matching and annotation use the floating-point V3 AABB. Legacy artifacts default to `legacy_unknown` without reinterpretation.
- CLI/UI inspection adds actual/configured provenance, safe stage/reason, timings, unmatched counts, and accepted split/merge/many-to-many/contour-fallback counts. Counts are correspondence outcomes, not confirmed detector errors. Failure-only pages remain visible in the layout summary.
- Invalid source images now fail before Sol even when V3 initialization has failed. Runtime/guide failure sends no stale guide and preserves the Sol outcome and usage. Reconciliation defects remain separate application errors, retain the original Sol page and analysis, and make the document partial.

## Graph and official implementation checks

The cached graph was inspected with ONNX 1.23.0 in an isolated `uv --with` environment; ONNX was not added to project dependencies. The opset-17 artifact exposes `image` float32 `[B,3,800,800]`, `im_shape` and `scale_factor` float32 `[B,2]`; outputs are `fetch_name_0` float32 `[N,7]`, `fetch_name_1` int32 `[B]`, and `fetch_name_2` int32 `[N,200,200]`. The checked page returned 300 candidates before score filtering.

Graph tracing confirmed decoded pixel boxes, confidence, and zero-based order ranks are already present. Order uses sigmoid precedence votes, reduction, TopK, and ScatterND before output gathering. Masks pass through sigmoid and `Greater(..., 0.5)` inside the graph and leave as binary int32. GroundMark does not apply a second box/order decode or sigmoid/mask threshold. It selects score `> 0.5`, stably sorts by native rank, and applies identical indices to rows and masks. Gaps and ties are retained.

The source comparison used pinned PaddleX commit `c50f5da858020db473a2285f089bb8c7bbd6afdc` and PaddleDetection commit `65e643573a35e068c796527648f7c2166de09cce`:

| Official source | Git blob verified before comparison |
|---|---|
| [Layout polygon routines](https://github.com/PaddlePaddle/PaddleX/blob/c50f5da858020db473a2285f089bb8c7bbd6afdc/paddlex/inference/models/layout_analysis/processors.py) | `508d472bc5ee3eadcd8d5a9bb5260af2610bbd89` |
| [Detection preprocessing](https://github.com/PaddlePaddle/PaddleX/blob/c50f5da858020db473a2285f089bb8c7bbd6afdc/paddlex/inference/models/object_detection/processors.py) | `9d898d2ea790776a2ecde58b105b3e85843270a5` |
| [Common image processors](https://github.com/PaddlePaddle/PaddleX/blob/c50f5da858020db473a2285f089bb8c7bbd6afdc/paddlex/inference/models/common/vision/processors.py) | `6d137d76a789747bccb542d38851d76c1fe3cfd1` |
| [Image resize functions](https://github.com/PaddlePaddle/PaddleX/blob/c50f5da858020db473a2285f089bb8c7bbd6afdc/paddlex/inference/models/common/vision/funcs.py) | `493fe0ea8b4edc18aa68e0436ace861fbfb9e4dc` |
| [Native detection/order/mask decode](https://github.com/PaddlePaddle/PaddleDetection/blob/65e643573a35e068c796527648f7c2166de09cce/ppdet/modeling/post_process.py) | `78aeacf1c740efd2b29dd0d6c3da0ee8a474195c` |

Selected official preprocessing and polygon functions were executed independently against the same captured ONNX inputs/outputs, without installing PaddleX or loading other weights. This exposed a float32 normalization difference: division by 255 differed from official multiplication by `1/255` by up to `5.960464477539063e-08`. The runtime now multiplies; all three input arrays matched exactly in the final CPU and CUDA checks. Class, score, original AABB, native rank, and returned polygon points matched the independently selected official results exactly on each device.

The real page was the existing first comparison raster, SHA-256 `b4c8fda635c3072b0ec51942cabba505873e1f1d6b4ea51d5cbcbb8ee4996058`. Both sessions returned 11 selected mask-derived contours, including a 12-vertex nonrectangular contour. CPU native ranks were `0,15,73,80,96,119,140,166,168,170,277`; CUDA ranks were `0,16,72,78,96,119,140,165,167,169,276`. These differences remain visible. The comparison checks decode correspondence, not whether those ranks are correct reading order.

This is parity with selected official preprocessing/poly routines on captured ONNX outputs, **not** full PaddleX pipeline equivalence, comparison against native Paddle weights, or quality validation. Optional NMS/merging/expansion and public sequential-order renumbering remain deliberately unapplied. The official largest-external-contour routine loses holes and smaller disconnected components; original masks are not persisted. Raw class/order logits and soft mask probabilities are not exposed. Batch inference, every class, and all distortion types were not validated.

## Live execution and replay evidence

Native Windows 11, CPython 3.14.7, ONNX Runtime 1.30.0, NumPy 2.5.3, OpenCV 5.0.0.93: CPU and auto-selected CUDA both executed real pages. CUDA used the available RTX 4060 Laptop GPU; CPU shape nodes are permitted. ONNX Runtime warned about CPU-assigned shape operations and ScatterND duplicate-index semantics. No cause for the observed CPU/CUDA rank difference was established. A real GPU failure was not induced; recovery and sticky reuse are tested with injected execution failures.

Five existing page rasters were each analyzed once per device and replayed against both historical Sol profiles: ten responses, 239 blocks, per device. All non-geometry content fields were preserved, with zero runtime/guide failures or reconciliation application defects. Each device run yielded 17 assignments, 222 unmatched Sol blocks, 99 unmatched detector-region occurrences across the ten response replays, and one accepted merge warning. The 99 count repeats each page's detector set for both profiles; it is not a count of unique missed regions. Agreement in totals does not establish identical geometry or accuracy. New prompts did not produce these historical responses.

Local evidence (ignored `data/`, not release assets):

- `data/validation/onnx-reference/`: verified source copies, `verify_decode.py`, `cpu-parity.json`, `auto-parity.json`.
- `data/validation/onnx-completion-cpu/` and `onnx-completion-auto/`: hash-bound manifests, policies, per-response layouts/pages, JSON and Markdown reports.
- `data/validation/onnx-completion-overlays/`: real-page annotated PNG, PDF, and inspection metadata. Visual inspection confirmed the source-page mapping and distinct overlays; this was not correspondence adjudication. Dense/overlapping labels can still obscure one another.

These local files can contain document content. Do not publish them as generic fixtures.

## Offline evaluation workflow

`scripts/evaluate_layout.py` is an existing paid Sol-profile/token-F1 comparison. Token F1 does not establish contour, correspondence, or order accuracy. The new `scripts/evaluate_reconciliation.py` makes **no Sol calls**, performs no automatic tuning, and writes only to a new output directory.

```powershell
# Analyze existing saved rasters locally; reuse each result for both saved profiles.
uv run --extra layout python -m scripts.evaluate_reconciliation --saved-comparison data/parse/layout-comparison-20260923 --output data/validation/my-v3-replay --run-v3 --device auto

# Fully offline replay from saved V3 artifacts; no model initialization/download.
uv run python -m scripts.evaluate_reconciliation --manifest path/to/manifest.json --output data/validation/my-reviewed-replay
```

`--run-v3` may download the pinned files on first use if absent from the user cache. Without it, every sample needs a saved layout artifact. Input hashes and page/dimension identity must agree; the person preparing the manifest is responsible for establishing that the saved Sol response and V3 artifact belong to that raster. Hashes prove file identity, not the truth of that pairing.

Manifest version 1 has required `provenance` and `samples`. Each sample contains `image`, `response`, and optional `layout`, each `{ "path": "...", "sha256": "64 lowercase hex digits" }`; paths resolve relative to the manifest. It also needs source `page` and `profile` (`baseline`/`legacy` or `candidate`/`detailed`). `category` defaults to `unreviewed`. Responses may be raw page JSON or the historical `{ "result": ... }` wrapper. A saved layout is a `LayoutPageArtifact` with the pinned ONNX provenance.

Optional `labels` contains a required reviewer/method `provenance` and these independent judgments:

- `acceptable_matches`: original Sol block index to acceptable V3 region indices. An empty list explicitly means no acceptable partner; an absent block is unreviewed.
- `before`: strict `[original_block_index, original_block_index]` constraints. Leave ties unspecified. Cycles and invalid references are rejected.
- `contours`: V3 region index to reviewed normalized polygon vertices. The metric is Pillow binary-mask IoU at the original raster resolution (`x*width`, `y*height`), not exact vector IoU. Unavailable predicted contours yield null, not fabricated rectangles.

Reports count correct/incorrect reviewed assignments, labeled missed assignments, unreviewed assignments, order violations against supplied constraints, contour overlap, content preservation, failures, and application defects. Unreviewed metrics are null, not zero errors. `--policy path/to/policy.json` supplies an explicit `ReconcilePolicy`; the exact policy is saved. No threshold is selected from match totals. Replay timings include local file/validation work and first-use preparation and are not comparable to parser page timings; cached second-profile replay is not a second inference benchmark.

## Tests and remaining quality gaps

Final checks: `uv run --no-sync python -m pytest tests -q` passed **395 tests**; `uv lock --check` passed; `uv build` produced wheel and sdist; the existing release verifier confirmed exact manifests and checkout bytes. `git diff --check` passed with only Windows line-ending notices. Focused tests cover contour PNG/PDF drawing, detector-only uniqueness, invalid mappings, old-artifact loading, rectangle-fallback provenance, invalid images during initialization fallback, runtime recovery, guide bounds, prompts, reconciliation, parser, CLI/UI helpers, and independently labeled evaluator behavior.

No reviewed real-page correspondence, contour, or order labels were supplied. The existing forms/fax raster set does not establish representative coverage of flat, multicolumn, skewed, and curved documents; one visibly skewed form was inspected, but categories were not adjudicated. Real correct/incorrect match rates, contour IoU, reading-order accuracy, and improved transcription quality therefore remain **unmeasured**. Synthetic tests and successful execution do not fill those gaps. Calibration needs reviewed same-raster examples, especially unsafe partial-coverage matches and representative multicolumn/curved pages, followed by held-out evaluation. No threshold change is warranted by these counts alone.

## Changed files in this completion step

- Runtime/provenance: `src/layout_detector.py`, `src/layout_polygons.py`, `src/layout.py`.
- Mapping, annotations, fallbacks, inspection: `src/layout_reconcile.py`, `src/annotate.py`, `src/parse.py`, `src/cli.py`, `src/ui/app.py`.
- Evaluation: `scripts/evaluate_reconciliation.py`, explanatory docstring in `scripts/evaluate_layout.py`.
- Tests: `tests/test_v3_completion.py`, `tests/test_evaluate_reconciliation.py`, `tests/test_layout_detector.py`, `tests/test_layout_integration.py`, `tests/test_ui_diagnostics.py`.
- Human docs: `README.md`, `.env.example`, `docs/LAYOUT-V3.md`, `docs/RUNBOOK.md`, this report, and links from the preceding research/reconciliation reports.

Existing Prompt 1–2 dependency, lockfile, launch, prompt, graph, and other dirty changes were preserved. Generated OpenWiki pages were not edited.
