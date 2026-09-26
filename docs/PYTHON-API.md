# Python API reference

The installed package is named `src`. These are the current callable and data boundaries, not a promise of a stable third-party SDK. Function signatures and concise docstrings remain in the linked source files. Importing the layout runtime does not import optional ML dependencies or load weights.

## Parsing and orchestration

| Entry point | Contract and side effects |
| --- | --- |
| [`src.preprocess.count_pages`, `inspect_source`](../src/preprocess.py) | Validate the source, count pages, and obtain source identity. PDFs are not rasterized for inspection. Raster inputs count as one page, including TIFF. File/decoder and configured-limit failures propagate. |
| `preprocess`, `preprocess_pages`, `iter_preprocessed_pages` | Return one page, a list, or a lazy iterator of page payloads. Bounds are 1-based and inclusive. Payloads include base64 PNG, MIME, source page, dimensions, and source hash. Defaults preserve 200-DPI PDF rendering and a 1,600-pixel long-edge cap. |
| [`src.parse.parse_page`](../src/parse.py) | Accept one preprocessed image and its identity/dimensions. Attempt V3, render the selected Sol prompt, validate the response, and reconcile. Returns `ParsePage`; optional diagnostic, usage, and layout-metadata lists collect evidence. Makes a paid Sol call; does not write files. Invalid image/Sol response failures raise `ExtractionCallError`. V3 failure retains Sol. |
| `parse_document` | Prepare V3 once and parse the selected range sequentially. Returns `ParseResult` with successful pages and per-page diagnostics. A page-call failure does not discard other pages. By default, writes `<doc_sha>.json` under `output_dir`; use `save_json=False` to suppress it. Source preprocessing and filesystem errors can propagate. |
| `analyze_page_layout`, `reconcile_parsed_page` | Strict lower-level helpers: typed layout failures become `ExtractionCallError`. The active parser catches those for Sol fallback; direct callers and current-template evaluations must handle them themselves. |
| [`src.graph.run_graph`](../src/graph.py) | Runs preprocessing, parsing, and selected exports; returns graph state with `parse_result`, status, diagnostics, usage, and output paths. `formats=None` selects the UI artifact set, otherwise use the six names in `src.export.FORMATS`. Defaults to full rendering and a separate run directory under `data/parse/runs/`. May make paid calls. |
| `GraphState`, `build_graph`, `node_preprocess`, `node_parse` | Internal orchestration contract and nodes. They are not separate extraction services. A UI preparation failure can be carried as `layout_initialization_failure` so the parser does not retry initialization for that run. |
| [`src.cli.main`](../src/cli.py) | Dispatches UI launch or extraction and returns the documented exit status. Loads environment configuration at the entry point; library imports do not discover dotenv files. |

`on_progress` receives `layout_preparing`, `layout_ready`, and `page_complete` dictionaries. Only page completion advances source-order counters. These events contain safe statuses/counts, not source text. See the [runbook](RUNBOOK.md#diagnostics-and-match-inspection) for timing boundaries and exit codes.

## Local layout runtime and pure reconciliation

| API | Contract |
| --- | --- |
| [`get_layout_runtime`, `LayoutRuntime`](../src/layout_detector.py) | Lazy process singleton, configured on first access. `prepare()` resolves pinned files, probes actual device execution, and returns `LayoutReadiness`. `predict(PIL_image, page_number=1)` returns one `LayoutPageResult`; calls are serialized. No transcription occurs here. |
| `LayoutReadiness`, `LayoutRegion`, `LayoutPageResult` | Frozen runtime records for actual device/reuse/timing, original pixel geometry/class/score/order, and page dimensions/model provenance. |
| `LayoutBackend`, `resolve_model_snapshot` | Backend protocol and pinned-file resolver. `LayoutRuntime` accepts a backend factory and snapshot resolver for offline tests; the resolver accepts an injected downloader. Use the existing protocol rather than importing a native engine in tests. |
| `LayoutModelUnavailable`, `LayoutInferenceError` | Safe typed initialization and page-inference failures. The runtime does not silently call Sol or retry an individual page on CPU. The parser owns Sol fallback. |
| [`convert_layout`](../src/layout_reconcile.py) | Validates and clips pixel geometry, then returns `NormalizedLayoutPage`. Invalid geometry raises `LayoutConversionError` with safe page/index/code information; no partially converted page is returned. |
| `given_layout_json` | Produces bounded, compact hints. Complete metadata remains separate. Required hints exceeding 300 regions or 64 KiB raise a conversion error; optional contours may be omitted. |
| `reconcile_page` | Pure deterministic matching of a `ParsePage` and same-sized normalized layout, with an optional `ReconcilePolicy`. Returns `ReconciliationResult(page, metadata)` without changing either input. Only accepted geometry and matched-block positions change. |
| `layout_match_counts` | Derives count-only inspection data from a `LayoutPageArtifact`; missing analysis/reconciliation produces null counts where unavailable. Review and accepted counts can overlap. |

See [V3 runtime and matching](LAYOUT-V3.md) for the pinned model, device probe, cache, geometry validation, conservative-v2 rules, and calibration limits.

## Schema types

These descriptions live here because adding class docstrings to Pydantic models can change the JSON schemas sent to models. Live Sol responses use only `LegacyParsePage` or `ParsePage`; artifact metadata is validated separately.

### Pages and blocks — `src.layout`

| Type | Meaning and validation boundary |
| --- | --- |
| `BBox` | Source page plus four XYXY coordinates, conventionally normalized to 0–1. This model enforces tuple length; it does **not** alone enforce finite, in-range, nondegenerate geometry. Reconciliation and drawing/crop consumers perform their own eligibility checks. |
| `LegacyBlock` | Required ID, role, text, nullable box/confidence/table. Tables are padded with empty trailing cells within the configured cell budget. |
| `ParseBlock` | Legacy fields plus detailed roles and nullable `BlockStructure`. `validate_structure()` rejects incompatible heading/list/table metadata, nesting jumps, uncovered/overlapping spans, and nonempty covered cells. |
| `ListItem`, `TableCell`, `BlockStructure` | List text/marker/depth/checkbox, table position/span/header status, and optional heading/list/table detail. Text remains in the block/table arrays. |
| `ParsePage`, `LegacyParsePage` | Page number, raster dimensions, and ordered blocks for the detailed and default strict responses. `LegacyParsePage.to_page()` adds unknown (`None`) structure without inventing detail. All model-facing fields are required; unavailable values are null. |
| `ParseResult` | Saved document artifact: source hash, schema version, extraction profile, successful pages, diagnostics, content-filtered page numbers, model, and optional layout metadata. `model_validate_json` loads saved JSON; `model_dump_json` serializes it. Legacy artifacts are upgraded in memory, never by relaxing live response validation. |

`expanded_table_cells` counts rectangularized table cells. `check_document_tables` enforces the document-wide budget; schema validation handles malformed shapes. They read the configured resource limit and do not call models.

### Artifact-only layout evidence — `src.layout`

| Type | Retained information |
| --- | --- |
| `NormalizedLayoutRegion` | Original index, class ID, raw/canonical labels, role hint, score, pixel box/polygon, normalized box/polygon, native order, and clipping flags. |
| `NormalizedLayoutPage` | Source page/dimensions, all regions, model/revision/engine, actual device, device-fallback reason, and order base. Region identities and box normalization must agree with the page. |
| `ReconcilePolicy` | Validated initial matching thresholds. This is a Python argument, not a GUI toggle or a calibrated quality guarantee. |
| `MatchEvidence` | Candidate block/region indices, IoU, both directional coverages, normalized center distance, score, and rejection reasons. |
| `BlockDecision` | Original/output block positions, nullable accepted region index, and review reasons. Original indices are used because block IDs can repeat. |
| `ReconciliationDetails` | Policy/version, candidates, decisions, and unmatched region indices. New results use conservative-v2; absent versions load as conservative-v1 for compatibility. |
| `ReconciliationMetadata` | Reconciliation details plus the normalized layout, returned by pure matching. |
| `LayoutPageArtifact` | Normalized layout plus nullable reconciliation. Analysis can survive a later Sol failure. Reference validators enforce one-to-one matches; `check_parsed_page` checks identity/dimensions and accepted boxes against output blocks. |
| `ReconciliationResult` (`src.layout_reconcile`) | Copied output page and its complete reconciliation metadata. |

Metadata models forbid extra fields and nonfinite values and are frozen at the model level. `ParseResult.validate_layout_metadata()` rejects duplicate/unknown layout page identities and inconsistent reconciliation references. Old saved JSON without `layout_metadata` loads with an empty list. Polygons are retained data, not polygon rendering or polygon-based matching.

### Diagnostics and chat

| Type | Purpose |
| --- | --- |
| [`FilterAnnotation`](../src/diagnostics.py) | Allowlisted prompt/completion filtering category and status. |
| `PageDiagnostic` | Sol outcome, safe provider/usage metadata, nullable device/timings, and layout fallback stage/code. Block-level rejected matches are in reconciliation metadata, not this flag. |
| `ExtractionCallError` | Exception carrying a safe `PageDiagnostic`. Local layout helpers also use it at the parser boundary. |
| [`Evidence`, `Statement`, `Draft`, `Verification`](../src/chat.py) | Strict chat response contracts: page quote; text with evidence; answer/not-found/out-of-scope decision with statements; and approval boolean. |
| `ChatResult` | Displayable answer/status with usage and safe diagnostics. Rejected drafts are not returned as approved answers. |

`document_pages` creates nonempty text/table evidence from successful pages, including successful Sol-fallback pages. `answer_document_question` makes a draft call, checks quoted evidence locally, and makes a separate verification call before display. It accepts an injected client for offline tests. Clean view does not filter chat evidence.

## Rendering and exports

- [`parse_to_markdown`, `parse_to_html`, `markdown_bundle`](../src/markdown.py) return text or ZIP bytes without file writes or model calls. `view="full"` is the default; `clean` filters classified running headers/footers only. HTML escapes source text and embeds supplied figure bytes.
- `render_and_save` validates a size-limited saved JSON file, loads adjacent figures, and writes adjacent full-view Markdown. `save_markdown_for_doc` and `save_html_for_doc` write a supplied result under the chosen directory/basename.
- [`extract_figures`](../src/figures.py) verifies source identity and returns PNG bytes plus warnings, optionally writing crops. `load_figures` reads bounded adjacent crops. Run these after reconciliation because crop names use output block indices.
- [`annotate_document`](../src/annotate.py) draws valid block rectangles and can independently save PDF, page PNGs, and metadata. Invalid boxes are skipped; polygons are not drawn.
- [`export_result`](../src/export.py) writes selected artifacts from one `ParseResult` and returns completed paths, figure warnings, and export errors. JSON stays complete regardless of the rendering view. It makes no model calls.
- [`source_stem`, `artifact_name`, `figure_name`, `reserve_basename`](../src/output_names.py) sanitize/validate names and reserve a shared UTC basename. Reservation is a context manager with a filesystem lock; it does not rename the source.

## Configuration, prompts, and evaluation tools

[`src.config`](../src/config.py) validates environment-backed resource limits, loopback hosts, endpoint URLs, and layout configuration; invalid values raise `ConfigError`. `LayoutConfig` carries the device mode and optional local model directory. See [.env.example](../.env.example) for supported names and defaults.

[`render_prompt`](../src/prompts.py) loads the four packaged Markdown templates and formats supplied variables. Missing variables raise a descriptive error. [`src.usage`](../src/usage.py) records usage and aggregates local cost estimates; these are not provider bills.

The Streamlit helpers in [`src/ui/app.py`](../src/ui/app.py) operate on session state and temporary artifacts. They are UI implementation details, not headless library entry points.

Evaluation scripts under [`scripts/`](../scripts/) are checkout tools, not wheel contents. Token scoring and comparison helpers support offline tests, but their live runners can make paid calls. The current-template prompt evaluator requires successful V3 analysis/reconciliation, unlike production fallback. Archived templates retain their historical path. `evaluate_chat` makes paid calls when invoked and has no `--live` safety flag; do not use it as a smoke test. `verify_release_artifacts.main` checks archive manifests and source-byte identity after a build without making model calls.
