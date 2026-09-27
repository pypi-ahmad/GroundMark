# Zero to mastery: follow a page through GroundMark

Work through the checkpoints in order. The six numbered steps and capstone use only the checkout and its tests. A real extraction is optional because it can download model weights and make a paid Sol call. Use Windows PowerShell from the repository root.

By the end, you should be able to trace one page from the input raster to its saved outputs, identify which model owns each field, reproduce a fallback in an offline test, and make a small verified change. The [developer guide](DEVELOPER-GUIDE.md) is the module map; this tutorial is the hands-on route through it.

## 1. Prepare an offline environment

GroundMark requires Python 3.14+ and uv. Run:

```powershell
uv sync --locked
uv run --locked python -m pytest tests/test_preprocess.py tests/test_markdown.py -q --import-mode=importlib
```

These tests should pass without `OPENAI_API_KEY`. If they fail, resolve the environment or test failure before moving to a model call. The full offline suite is `uv run --locked python -m pytest tests -q --import-mode=importlib`.

## 2. Inspect and rasterize a source

The checked-in invoice fixture is a PNG, so source inspection should report one page:

```powershell
uv run --locked python -c "from src.preprocess import inspect_source; print(inspect_source('tests/fixtures/invoice.png')['pages'])"
```

Expected output: `1`. `inspect_source` also computes a source hash. `iter_preprocessed_pages` yields PNG bytes encoded as base64 with source page number, width, height, and the same hash. PDF pages use the project's 200-DPI rendering and 1,600-pixel long-edge cap. Read `src/preprocess.py`, then run `tests/test_preprocess.py` alone if you want to see range and failure cases.

Checkpoint: explain why the V3 analyzer and Sol must receive the same rendered page image. The source hash and page number bind results to that image; using another raster would make geometry and annotations unreliable.

## 3. Render a page without any model

Open `uv run --locked python` and enter this Python. It constructs the same internal types the parser hands to the renderers:

```python
from src.layout import BBox, ParseBlock, ParsePage, ParseResult
from src.markdown import parse_to_markdown

block = ParseBlock(
    id="h1", type="heading", text="Invoice", conf=None, table=None,
    bbox=BBox(page=1, xyxy=(0.1, 0.1, 0.5, 0.2)), structure=None,
)
page = ParsePage(page=1, width_px=800, height_px=600, blocks=[block])
result = ParseResult(doc_sha="tutorial", pages=[page])
print(parse_to_markdown(result))
```

Expected Markdown: `## Invoice`. The box is normalized to 0–1; it does not change the text. `src/markdown.py` renders Python-owned Markdown and HTML from validated blocks. `tests/test_markdown.py` covers tables, escaping, and structural metadata.

## 4. Read the two model contracts

The default Sol profile validates a `LegacyParsePage`; the optional detailed profile validates a `ParsePage`. Both are converted to the internal `ParsePage` used above. Sol reads the complete image and supplies text, tables, block IDs, transcription confidence, and semantic structure. `prompts/runtime/` holds the authored prompt templates.

V3 is a separate local ONNX analyzer. `src/layout_detector.py` verifies the pinned official `PaddlePaddle/PP-DocLayoutV3_onnx` files and actual execution device. `src/layout_polygons.py` decodes mask contours. `src/layout_reconcile.py` normalizes geometry, projects bounded region hints into the Sol prompt, and matches validated Sol blocks to V3 regions. The compact prompt contour is not the stored contour used for matching or drawing.

Checkpoint: in [Python API](PYTHON-API.md), locate `NormalizedLayoutRegion`, `MatchEvidence`, and `LayoutPageArtifact`. State which one holds the original detector result, which records a candidate comparison, and which binds detector evidence to a parsed page.

## 5. Trace matching and fallback offline

```powershell
uv run --locked python -m pytest tests/test_layout_detector.py tests/test_layout_reconcile.py tests/test_layout_integration.py -q --import-mode=importlib
```

Start with a test in `tests/test_layout_reconcile.py` that accepts a match, then one that leaves a block or region unmatched. A qualified pair uses V3's AABB and relative order; the full contour, original V3 class, and detector confidence remain in the linked artifact. Sol text, block IDs, semantic type, and transcription confidence stay unchanged. Sol boxes remain for unmatched blocks. Detector-only regions contain no invented text. Unmatched Sol blocks keep their relative order under the documented interleaving rule in [Layout V3](LAYOUT-V3.md).

Next, read a device-recovery test in `tests/test_layout_detector.py` and a Sol-fallback test in `tests/test_layout_integration.py`. CUDA execution failure gets one bounded CPU recovery attempt. A runtime or unusable-guide failure sends an empty guide and records a safe diagnostic. Invalid images or Sol responses remain page failures. A reconciliation invariant defect is an application error and can make the document partial.

Checkpoint: describe why “unmatched Sol block” does not by itself prove “V3 missed text.” Granularity and correspondence rules can also leave it unmatched. Match counts are not accuracy scores.

Read `test_split_merge_nested_and_many_to_many_assign_once` in `tests/test_layout_reconcile.py`. Follow its accepted decision and its leftover Sol blocks or detector regions. Then read `test_header_body_footer_rank_order_preserves_existing_furniture_types`. Native V3 order positions matched blocks, while unmatched Sol blocks retain their relative order. This deterministic placement rule does not establish that the detector found the correct reading order on a real page.

## 6. Follow outputs and inspect evidence

`src/graph.py` runs preprocess then parse; `src/export.py` writes selected formats. Markdown and HTML come from `src/markdown.py`; figures use selected AABB envelopes; `src/annotate.py` draws full matched V3 contours, unmatched Sol boxes, and detector-only overlays. Saved JSON retains page diagnostics and separately validated `layout_metadata`. The [runtime runbook](RUNBOOK.md#diagnostics-and-match-inspection) explains the inspection fields.

Choose one existing fixture-backed test and add a focused assertion for content preservation, one-to-one matching, contour fallback, or an annotation overlay. Run its file, the complete offline suite, and `git diff --check`. Avoid changing a matching threshold merely to raise the match count; [evaluation guidance](V3-INTEGRATION-COMPLETION.md) requires reviewed correspondences and page rasters to measure quality.

## Offline capstone

Start with `test_active_graph_reconciles_before_json_annotations_crops_and_chat` in `tests/test_layout_integration.py`. Compare the fake Sol blocks with the saved parsed blocks, and find the assertions for full-image input, content preservation, artifact serialization, annotations, crops, and chat evidence. Use `test_split_merge_nested_and_many_to_many_assign_once` in `tests/test_layout_reconcile.py` to trace accepted pairs and leftovers. Then read `test_v3_fallback_preserves_every_sol_field_and_full_image` in the integration file: its assertions check that failed V3 inference leaves the Sol page intact and sends an empty guide with the complete image.

Pick one of those contracts and add a focused assertion that the existing tests do not yet make. Run the affected test file. You should be able to explain which assertion proves your claim and which outcomes still need real-page review.

Finish with `uv run --locked python -m pytest tests -q --import-mode=importlib` and `git diff --check`. Record what the tests prove and what they leave open. Fake responses prove local contracts, while a real quality assessment needs paired page rasters, reviewed block correspondences, contours, and order labels. The [contributor runbook](CONTRIBUTOR-RUNBOOK.md) covers the handoff.

## If a checkpoint fails

- `uv sync --locked` fails: check that the selected interpreter meets `requires-python` in `pyproject.toml`, then retry without changing the lockfile.
- The fixture inspection command cannot find its image: run it from the repository root, where `tests/fixtures/invoice.png` is relative to the current directory.
- Offline tests try to load weights or call Sol: stop and inspect the changed test or fixture. The offline suite should use injected backends and fake responses.
- A real extraction reports layout fallback: inspect the saved diagnostic stage and reason before interpreting match counts. The [runtime runbook](RUNBOOK.md#diagnostics-and-match-inspection) lists the fields.

## Optional: one real extraction

Only do this with a configured compatible Sol endpoint, an accepted call budget, and a source you are permitted to send. From the checkout:

```powershell
uv sync --locked --extra layout
uv run --locked --extra layout groundmark path\to\document.pdf path\to\empty-output --json --annotated-images
```

First preparation may download the pinned ONNX files into the user cache. The JSON and stderr diagnostics report the actual layout device, timing, fallback stage, matches, and unmatched counts. A real page verifies that the runtime executes; judging contour, correspondence, and reading-order accuracy needs reviewed page-level ground truth. Never use the checked-in invoice fixture as an accuracy label unless it has been independently annotated.
