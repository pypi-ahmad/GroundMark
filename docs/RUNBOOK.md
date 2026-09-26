# Runbook

## Setup and runtime preparation

The [README installation instructions](../README.md#install) cover GitHub wheel installs with `uv tool`, `uv pip`, or pip, as well as manual cloning. You need Python 3.14+. Once installed, the commands work outside the checkout.

Set `OPENAI_API_KEY`, and optionally `OPENAI_BASE_URL`, in the environment or a `.env` file. The launcher reads `.env` from the current folder, or from the UI's `--workspace` folder when provided. `--env-file PATH` selects a specific file. Variables already in the process take priority. After setting Windows User or Machine variables, open a new terminal so GroundMark inherits them.

Blank or unset `OPENAI_BASE_URL` uses the SDK default. Custom endpoints must use HTTPS, except for HTTP endpoints on localhost or a loopback IP. Credentials, query strings, and fragments are rejected in endpoint URLs. A missing explicit environment file produces an error. The endpoint must support Sol parsing and Luna chat; its URL does not select different models.

`groundmark` opens the web UI at `http://127.0.0.1:5805`. `--host` accepts only localhost or a loopback IP; the UI cannot be exposed to a LAN or public interface. Use `--workspace`, `--port`, and `--headless` to configure the remaining UI settings. An occupied port produces an error; the launcher does not terminate another server. `run.cmd` runs `uv run groundmark` from the checkout and forwards arguments.

This checkout attempts PP-DocLayoutV3 before Sol extraction. Use `uv sync --extra layout` and `uv run --extra layout groundmark` for checkout runs. First preparation resolves the pinned weights in the user cache (or the configured local directory) and probes the actual GPU/CPU engine. Missing dependencies or failed initialization produce actionable diagnostics and use Sol-only extraction for the run. Individual V3 failures use Sol blocks for that page. Successful fallback pages retain the parsed outcome; inspect `layout_fallback`, `layout_stage`, and `layout_code` in JSON diagnostics. Base installs still support imports, saved artifacts, and offline tests. See [V3 configuration and metadata](LAYOUT-V3.md); the published v0.1.1 release predates this integration.

Upload and preview remain lightweight. A valid Streamlit Parse click displays “Preparing PP-DocLayoutV3…” before starting the graph, then shows GPU (CUDA) or CPU. Initialization failure warns and continues with Sol; another Parse click retries V3 after the issue is resolved. Ordinary reruns and tab/view changes neither reload weights nor rerun inference. Model readiness is process-wide; parsed results and status display are session-local. Detailed layout remains a separate experimental Sol option.

The default `GROUNDMARK_LAYOUT_DEVICE=auto` verifies CUDA inference and retries CPU if initialization/probing fails. `cpu` skips CUDA. Set `GROUNDMARK_LAYOUT_MODEL_DIR` for the four pinned local files; otherwise standard Hugging Face user-cache configuration applies. A malformed local override fails rather than downloading elsewhere. Restart the process after changing configuration. No model files belong in Git.

The default limits are 100 MiB per source, 250 selected pages, 50,000,000 pixels per raster image, and 16,384 output tokens per parse call. Override them with the positive-integer variables shown in `.env.example`; invalid or nonpositive values stop the operation.

## CLI extraction and artifacts

For terminal extraction, run `groundmark input.pdf output --all`, or `uv run --extra layout groundmark input.pdf output --all` from the checkout. Without format flags, the command writes Markdown and its figure files. You can combine `--markdown --html --json --annotated-pdf --annotated-images --markdown-zip`, or use `--all` to select every format. UI-only options cannot be combined with a source file.

The input must be outside the output directory. An existing nonempty output directory requires `--overwrite`; this permits another run while keeping existing files. Use a fresh directory to avoid mixing artifacts from different runs or page ranges. Before making model calls, the CLI checks the arguments and configuration, confirms that it can read the input, and validates the page range. Pages are 1-based and inclusive.

CLI artifacts use these paths, where `<basename>` is the sanitized original filename without its extension plus the UTC extraction start time, such as `invoice_20260923_100045Z`:

| Selection | Paths |
| --- | --- |
| Markdown | `<basename>.md`, with `images/<basename>_page_NNN_figure_NNN.png` |
| HTML | `<basename>.html`, including embedded figure images |
| JSON | `<basename>.json`, including full page diagnostics |
| Annotated PDF | `annotated/<basename>.pdf` |
| Annotated images | `annotated/<basename>/<basename>_page_NNN.png` |
| Markdown ZIP | `<basename>.zip`, containing `<basename>.md` and its `images/` |

HTML-only and ZIP-only extraction do not write loose images. JSON-only extraction skips presentation work. CLI annotations do not create a metadata sidecar; UI annotations include one. When a page fails, output from successful pages remains available. If all pages fail, the only possible output is JSON diagnostics, when requested. An export failure also leaves other completed artifacts intact.

Every format and GUI download in a run uses the same basename, including Clean and Full views. If the name exists, GroundMark adds fractional seconds, as in `invoice_20260923_100045_123456Z`. Spaces and Unicode stay intact. GroundMark removes directory components, replaces invalid Windows characters, and caps the original stem at 120 characters. An empty stem becomes `document`; a reserved Windows name gets an underscore prefix.

Figure links and ZIP contents use the same names. The JSON renderer can still load legacy figure filenames.

The CLI prints artifact paths to stdout and progress, status, and diagnostics to stderr. Exit codes: `0` success, `1` failed extraction/runtime error, `2` invalid arguments/configuration, `3` partial extraction or export/figure problems, `130` interruption. `--view clean` filters presentation only; default CLI view is `full`, and JSON is always complete.

## Diagnostics and match inspection

Readiness includes preparation elapsed seconds and whether the model was reused. Each completed page reports its source number, outcome, actual device when known, `layout_seconds`, `page_seconds`, and accepted/review counts when reconciliation exists. In document runs, layout time includes image decoding, V3 inference, conversion, and prompt projection; page time additionally includes Sol and reconciliation. Both exclude initial runtime preparation, rasterization, and exports. Initialization fallback has no verified layout device; unavailable timing fields and those in older JSON can be null. These wall-clock measurements are operational feedback, not benchmarks.

Inspect the UI's Layout summary, or JSON `layout_metadata[*].reconciliation`: count decisions with a non-null `region_index` for accepted matches, null for unmatched Sol blocks, and nonempty `reasons` for review. Review counts can include accepted matches. `unmatched_region_indices` lists unmatched detector regions; `reconciliation: null` means unavailable, not zero matches. Candidate metrics and the effective policy support later calibration. V3 never replaces Sol text/table content; ambiguous matches preserve Sol boxes. Polygons are retained only as metadata—annotations and crops remain rectangles.

Missing or rejected matches are block-level decisions, not runtime failures: they leave `layout_fallback` false and preserve the Sol box and position. An initialization or page-analysis failure sets that flag while retaining the Sol outcome. A parsed Sol fallback page is still successful and does not itself cause exit code `3`. See the [fallback cases](LAYOUT-V3.md#what-fallback-means). Model paths, credentials, raw provider errors, labels, and document text do not belong in status messages.

## Development and release checks

For development, use `uv sync` and `uv run python -m pytest tests`. The explicit `tests` path keeps archived release snapshots under `data/` out of collection. `pyproject.toml` defines runtime dependencies, and `uv.lock` locks the checkout environment. Compatibility requirements files install the local package. Run evaluation scripts from the checkout. The installed distribution uses the `src` Python package; its callable boundaries are described in the [Python API reference](PYTHON-API.md).

Build with `uv build`. The wheel bundles runtime code, four Markdown prompts, and the MIT license. The source archive also contains build metadata and README. Neither includes private documents, credentials, tests, evaluation scripts, or generated architecture files.

Run `uv run python scripts/verify_release_artifacts.py` after building into an empty `dist` directory. It checks an exact file manifest for both archives, rejects duplicate members, and compares runtime code, all four prompts, license, and other included source files with the checkout. New runtime modules must be added to the checker deliberately. CI pins Python 3.14.7, uv 0.12.18, and Hatchling 1.32.4; these pins still need reviewed updates.

Publish releases on GitHub. This project does not publish to PyPI. A matching `v<project-version>` tag runs the release workflow, which tests and builds once, inspects both archives, smoke-tests the installed wheel, creates SHA-256 checksums and attestations, then publishes the draft. Release immutability depends on repository settings, not this workflow alone. To upgrade a tool installation, use `uv tool install --force --python 3.14` with the new release's wheel URL. To remove it, use `uv tool uninstall groundmark`. pip and uv pip users install the new wheel URL in the same virtual environment.

## Streamlit use and local data

Upload a supported PDF or image, choose the first and last pages, and select Parse. You can use Input preview before making a model call. The Markdown, Annotated, HTML, and JSON tabs show the results.

UI uploads and generated artifacts live in a session-specific temporary directory. Upload replacement and removal explicitly clean that directory; disposal of the temporary-directory object also attempts cleanup. Closing a browser tab does not guarantee immediate session disposal, deletion of Streamlit media/download buffers, or cancellation of an in-flight provider request. A crash can leave temporary files behind. Download anything you need to keep. CLI outputs remain in the destination you select. Copy controls are available for rendered Markdown, raw Markdown, and JSON.

The launcher explicitly restricts accepted browser Host headers to localhost and loopback addresses and enables CORS and XSRF protections. These settings apply when launching with `groundmark`; starting Streamlit directly bypasses the launcher policy. This remains a local, single-user application, not an authenticated shared service.

Resource limits in `.env.example` include 10,000 expanded table cells across a document, 128 retained figures, and 32 MiB of retained PNG figure data. Table padding and rendering enforce the cell budget; live extraction reports a page exceeding the remaining budget as `invalid_response`, preserving earlier successful pages. Figure extraction omits remaining crops with a warning when its budget is exhausted. Saved-figure imports reject over-budget collections. Saved JSON inputs use the source-byte limit. HTML/base64 and ZIP generation still make bounded copies of retained figure data. Annotation assembly encodes and imports one PDF page at a time; it retains the encoded PDF document, not every page's decoded pixels. These limits reduce allocation risk, but are not an OS-level memory or CPU sandbox.

## Release provenance

For releases produced by the attestation-enabled workflow, verify the downloaded wheel before installing it. Authenticate `gh` first, replace the tag below with the intended release, and require successful verification:

```powershell
$releaseTag = "v0.1.1"
$releaseWheel = "groundmark-$($releaseTag.Substring(1))-py3-none-any.whl"
gh attestation verify $releaseWheel --repo pypi-ahmad/GroundMark --signer-workflow pypi-ahmad/GroundMark/.github/workflows/release.yml --source-ref "refs/tags/$releaseTag" --deny-self-hosted-runners
if ($LASTEXITCODE -ne 0) { throw "Release provenance verification failed" }
```

Repeat verification for a source archive if using it. Compare `Get-FileHash -Algorithm SHA256` with the release's `SHA256SUMS` as an additional integrity check; a checksum alone does not authenticate the publisher. Older releases may lack attestations. Do not treat a missing attestation as successful verification.

## Views and detailed layout

Clean and Full change the Markdown and HTML views, including copied and downloaded output. Switching views does not call the model again. Clean hides blocks classified as running headers or footers. If the document has figure crops, download the Markdown ZIP to keep its images. HTML embeds them.

The default extraction has no running-header or footer classifications, so Clean and Full show the same blocks for those results. Files written by the graph keep full content; UI downloads use the selected view. Switching views cannot add structure missing from the extraction.

Detailed layout is experimental and off by default because source review found new transcription errors in this mode. Enabling it changes the prompt and response schema and clears the previous result. Select Parse to run it in the UI, or pass `--detailed-layout` to `groundmark` with a source file and output directory. Direct callers can also pass `detailed_layout=True` to `run_graph` or `parse_document`. Read the [layout evaluation](LAYOUT-EVALUATION.md) before using it for work where source values matter.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Missing API key | Confirm `OPENAI_API_KEY` is present without printing its value. |
| Unsupported model | Parsing accepts Sol; chat uses Luna at medium reasoning. |
| Layout unavailable | Extraction continues with Sol. Use `uv run --extra layout`, check the local model override, and inspect the safe stage/code. Auto mode already probes CPU after CUDA failure. |
| V3 misses a block or disagrees with Sol | Inspect reconciliation decisions. Sol text, tables, boxes, and positions survive rejected matches; this is not a failed page. |
| Page parse failure | Review the page diagnostic; successful pages may remain downloadable. |
| No annotation | Blocks need valid normalized bounding boxes; text artifacts remain usable. |
| Slow document | Select a smaller range; pages intentionally run sequentially. |

Run `uv sync`, then `uv run python -m pytest tests` after changing code or prompts. The tests use fake model responses and make no paid calls.

## Document chat

After parsing, open Chat to see which pages are available. Answers use parsed text from those pages and cite them inline. Clear chat starts a new conversation without parsing again. Changing the file, page range, or detailed-layout setting clears the result and requires another parse. Chat is unavailable when no pages were parsed successfully.

Questions can contain up to 2,000 characters. Answers have a 120-word limit, including citations, and the model sees only the last six accepted turns. Requests have a 200 KB serialized UTF-8 limit, with 30 KB reserved before drafting for policies, schemas, and verification. Select a smaller page range if the parsed document is too large. Each call allows 8,192 output tokens, including reasoning. The app does not display rejected or incomplete answers. Both chat calls count toward the session estimate.

The optional live chat check uses synthetic data and makes paid calls: `uv run --no-project --python .venv\Scripts\python.exe -m scripts.evaluate_chat`. It saves results to ignored `data/parse/chat-evaluation.json` and exits with an error if a case fails. Passing these cases does not establish protection against every attack.
