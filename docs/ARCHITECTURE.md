# Architecture

```text
scanned PDF/image -> render pages -> attempt V3 -> Sol transcription -> reconcile -> artifacts
                                      |                                  |
                                      +-- failure: empty hints           +-- failure: retain Sol
```

`src/graph.py` runs the fixed `preprocess -> parse -> END` workflow. The preprocess node validates the source and computes its hash. `src/parse.py` retains the 200-DPI/1,600-pixel raster profile and analyzes each selected page with PP-DocLayoutV3 before sending that same image to Sol. Both prompts receive bounded region hints; Sol still reads all text and tables from the image. After strict validation, conservative one-to-one reconciliation applies accepted geometry and order without changing transcription, tables, or structure. A request can include up to 12,000 characters from earlier successful pages. The graph has no extraction review, correction loop, or second model pass over the full document.

The web interface uses Python and Streamlit. For terminal extraction, the installed `groundmark` command accepts a source file and output directory and runs the same graph. `pypdfium2` renders PDF pages, Pillow handles raster images and annotations, and Pydantic validates the layout response. The page image takes precedence when preceding-page context disagrees with it.

`src/layout.py` defines the document, page, block, table, reading-order, and normalized bounding-box types. Renderers, JSON downloads, and annotations use these types. There is no business-field schema.

Saved `ParseResult` JSON uses `schema_version: 2` and records `extraction_profile` as `legacy` or `detailed`. Separately validated `layout_metadata` retains V3 regions, provenance, and reconciliation evidence; old JSON without it still loads. `run_graph`, `parse_document`, and `parse_page` accept `detailed_layout=False`. The default request uses `LegacyParsePage`; detailed layout uses `ParsePage`. Both strict Sol schemas remain unchanged. The parser converts and reconciles both responses into the same internal result type before exports, crops, annotations, or chat evidence.

Detailed blocks have a nullable `structure` field. It holds the heading level, list items (text, marker, depth, checkbox state), and table-cell metadata (zero-based position, spans, header status). Cell text stays in the table array, and short rows get empty trailing cells. Validation rejects spans that overlap, exceed the table, leave gaps, or cover nonempty cells. It also rejects invalid list nesting. Every model-facing property is required; null indicates unavailable metadata.

| Module | Responsibility |
| --- | --- |
| `src/llm.py` | Configure Sol and invoke structured visual parsing. |
| `src/layout_detector.py` | Lazy process-wide V3 runtime, pinned cache resolution, and verified device preparation. |
| `src/layout_reconcile.py` | Normalize pixel geometry, bound prompt hints, reconcile conservatively, and summarize match evidence. |
| `src/markdown.py` | Render layout blocks into Markdown and self-contained HTML. |
| `src/annotate.py` | Draw valid reconciled block rectangles on source pages. |
| `src/figures.py` | Save source-matched figure crops with the run basename and page/index suffixes. |
| `src/ui/app.py` | Present document outputs and the document chat interface. |
| `src/chat.py` | Answer questions over current parsed pages, check exact evidence, and verify scope and grounding before display. |

Diagnostics identify filtered and failed pages. The app still writes text artifacts for successful pages when another page fails. Annotation errors leave parsed text intact.

The [Python API reference](PYTHON-API.md) describes callable boundaries and schema types. [V3 runtime and matching](LAYOUT-V3.md) defines conversion, matching thresholds, and artifact evidence.

V3 initialization failure uses Sol-only extraction for the run without retrying V3 per page. Individual V3 analysis failures use empty region hints; reconciliation failures retain the validated Sol blocks without a second paid call. Page diagnostics preserve the Sol outcome and usage, with `layout_fallback: true` and a safe layout stage/code. Geometry/order come from V3 only for accepted matches. Split/merge, ambiguous, unmatched, and role/label-mismatched blocks preserve Sol content, boxes, and original positions. Detector labels never retype blocks or hide content in Clean view. Polygon contours remain metadata; matching, crops, and annotations are rectangular. Matching thresholds are not calibrated accuracy guarantees.

The runtime loads once per process under a lock and serializes predictions. First preparation downloads the pinned official snapshot only on a cache miss, or verifies an explicit local directory. Auto mode verifies CUDA placement and inference, then probes CPU after CUDA failure. Readiness reports the device actually used. Streamlit prepares only inside a valid Parse click, before graph execution; failure warns and continues with Sol, passing the preparation failure to the parser to avoid another initialization attempt. A second parser preparation reuses the same model without another probe. Ordinary reruns and tab changes read saved results and display-only session status. No second model cache or layout-off control is introduced.

Progress phases are `layout_preparing`, `layout_ready`, and `page_complete`; all retain the existing counters. Only page completion increments them. Page diagnostics add nullable actual device, layout time, and total parsing time. CLI renders these through stderr, while the UI shows readiness and a count-only Layout summary. Raw labels and transcription belong to artifacts, never progress or error messages. Unexpected graph exceptions use fixed messages.

Each UI session uses an isolated temporary directory for uploads and generated artifacts. A successful parse produces Markdown, HTML, and layout JSON. Successful annotation adds a PDF, page PNGs, and annotation metadata. CLI runs persist only the selected formats in their requested output directory.

`src/output_names.py` sanitizes the source filename and reserves one UTC basename for the run's exports. Graph state holds the original filename, extraction start time, and chosen basename. `doc_sha` remains the grounding identifier.

The UI passes the uploaded name separately from its hashed cache path. Rerendering or downloading uses the same basename; a new parse gets a new timestamp. A temporary directory lock coordinates concurrent writers. If the name exists, GroundMark adds fractional seconds.

Figure crops live in the run's `images/` directory. A missing or invalid box leaves a placeholder and a warning; the figure text stays in the extraction. HTML embeds the PNG data. Markdown links to images included in its ZIP download. The CLI JSON renderer loads adjacent crops when available.

Programmatic rendering uses full content by default. The UI opens in Clean view, which hides blocks classified as page headers or footers. A table without identified headers keeps every row as data. A simple table with an identified first header row uses Markdown; complex or headerless tables use generated HTML. Renderers escape source markup, keep list labels and trailing notes, and use the original text when list metadata conflicts with it. Rendering leaves the extraction data unchanged.

The default extraction contract has no page-header/footer roles, so Clean and Full contain the same blocks for default results. Loading older JSON cannot infer heading depth, list nesting, or merged cells. GUI graph exports keep full content; UI downloads follow the selected view. CLI exports use the requested `--view`.

The Chat tab works outside the parse graph. It builds evidence from successful pages' block text and table rows, including classified headers and footers. Clean view and display escaping do not affect that evidence. Luna receives the text with page numbers and a bounded amount of accepted history. Separate Markdown policies govern drafting and verification. Python checks quoted evidence and adds citations before Streamlit displays the approved text. Chat has no tools, filesystem access, or browsing. Session history clears when the upload is removed or replaced, the page range or extraction mode changes, or the document is parsed again.

## Installation and selected exports

`src/cli.py` selects UI startup or file extraction, loads endpoint settings, validates CLI inputs, and reports exit status. `run_graph` accepts optional `output_dir`, `formats`, and `view` arguments. Callers that omit these arguments get the full UI artifact set in a separate directory for each run. The CLI writes Markdown to the supplied output directory by default.

`src/export.py` writes selected formats from one `ParseResult`. The graph calls `parse_document` with `save_json=False` so JSON is saved only when requested; direct parser callers still get JSON by default. Figure extraction can return bytes without saving images. Annotation export can independently save PDF, page PNGs, and metadata. If an export fails, completed artifacts remain available and the error appears in `export_errors`. `output_paths` lists completed artifacts.

Hatchling bundles the runtime package and includes the authored files in `prompts/runtime/*.md` as package resources. The launcher locates the installed app by its absolute path and uses a writable user workspace. GitHub Releases hosts the wheels and source archives.
