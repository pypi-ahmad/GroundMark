# Architecture

```text
scanned PDF/image -> render pages -> sequential visual parse -> deterministic artifacts
```

`src/graph.py` runs the fixed `preprocess -> parse -> END` workflow. The preprocess node validates the source and computes its hash. `src/parse.py` uses `src/preprocess.py` to rasterize the selected pages, then sends them to `gpt-6-sol` in source order. A request can include up to 12,000 characters from earlier successful pages. The graph has no extraction review, correction loop, or second model pass over the full document.

The web interface uses Python and Streamlit. For terminal extraction, the installed `groundmark` command accepts a source file and output directory and runs the same graph. `pypdfium2` renders PDF pages, Pillow handles raster images and annotations, and Pydantic validates the layout response. The page image takes precedence when preceding-page context disagrees with it.

`src/layout.py` defines the document, page, block, table, reading-order, and normalized bounding-box types. Renderers, JSON downloads, and annotations use these types. There is no business-field schema.

Saved `ParseResult` JSON uses `schema_version: 2` and records `extraction_profile` as `legacy` or `detailed`. Older files load with unknown structure metadata and are not rewritten. `run_graph`, `parse_document`, and `parse_page` accept `detailed_layout=False`. The default request uses `LegacyParsePage` and the original prompt; detailed layout uses `ParsePage` and the structured prompt. The parser converts both responses to the same internal result type.

Detailed blocks have a nullable `structure` field. It holds the heading level, list items (text, marker, depth, checkbox state), and table-cell metadata (zero-based position, spans, header status). Cell text stays in the table array, and short rows get empty trailing cells. Validation rejects spans that overlap, exceed the table, leave gaps, or cover nonempty cells. It also rejects invalid list nesting. Every model-facing property is required; null indicates unavailable metadata.

| Module | Responsibility |
| --- | --- |
| `src/llm.py` | Configure Sol and invoke structured visual parsing. |
| `src/markdown.py` | Render layout blocks into Markdown and self-contained HTML. |
| `src/annotate.py` | Draw valid model-provided block boxes on source pages. |
| `src/figures.py` | Save source-matched figure crops using deterministic page/index filenames. |
| `src/ui/app.py` | Present document outputs and the document chat interface. |
| `src/chat.py` | Answer questions over current parsed pages, check exact evidence, and verify scope and grounding before display. |

Diagnostics identify filtered and failed pages. The app still writes text artifacts for successful pages when another page fails. Annotation errors leave parsed text intact.

Each UI run writes to `data/parse/runs/<run-id>/`. A successful parse produces Markdown, HTML, and layout JSON. Successful annotation adds a PDF, page PNGs, and annotation metadata.

Figure crops live in the run's `images/` directory. A missing or invalid box leaves a placeholder and a warning; the figure text stays in the extraction. HTML embeds the PNG data. Markdown links to images included in its ZIP download. The CLI JSON renderer loads adjacent crops when available.

Programmatic rendering uses full content by default. The UI opens in Clean view, which hides blocks classified as page headers or footers. Unknown table headers remain ordinary cells. A simple table with an identified first header row uses Markdown; complex or headerless tables use generated HTML. Renderers escape source markup, keep list labels and trailing notes, and use the original text when list metadata conflicts with it. Rendering does not change the extraction data.

The default extraction contract has no page-header/footer roles, so Clean and Full contain the same blocks for default results. Loading older JSON cannot infer heading depth, list nesting, or merged cells. Graph-written Markdown and HTML keep full content; UI downloads follow the selected view.

The Chat tab works outside the parse graph. It builds evidence from successful pages' block text and table rows, including classified headers and footers. Clean view and display escaping do not affect that evidence. Luna receives the text with page numbers and a bounded amount of accepted history. Separate Markdown policies govern drafting and verification. Python checks quoted evidence and adds citations before Streamlit displays the approved text. Chat has no tools, filesystem access, or browsing. Session history clears when the upload is removed or replaced, the page range or extraction mode changes, or the document is parsed again.

## Installation and selected exports

`src/cli.py` selects UI startup or file extraction, loads endpoint settings, validates CLI inputs, and reports exit status. `run_graph` accepts optional `output_dir`, `formats`, and `view` arguments. Callers that omit these arguments get the full UI artifact set in a separate directory for each run. The CLI writes Markdown to the supplied output directory by default.

`src/export.py` writes selected formats from one `ParseResult`. The graph calls `parse_document` with `save_json=False` so JSON is saved only when requested; direct parser callers still get JSON by default. Figure extraction can return bytes without saving images. Annotation export can independently save PDF, page PNGs, and metadata. If an export fails, completed artifacts remain available and the error appears in `export_errors`. `output_paths` lists completed artifacts.

Hatchling bundles the runtime package and includes the authored files in `prompts/runtime/*.md` as package resources. The launcher locates the installed app by its absolute path and uses a writable user workspace. GitHub Releases hosts the wheels and source archives.
