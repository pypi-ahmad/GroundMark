# Runbook

The [README installation instructions](../README.md#install) cover GitHub wheel installs with `uv tool`, `uv pip`, or pip, as well as manual cloning. You need Python 3.14+. Once installed, the commands work outside the checkout.

Set `OPENAI_API_KEY`, and optionally `OPENAI_BASE_URL`, in the environment or a `.env` file. The launcher reads `.env` from the current folder, or from the UI's `--workspace` folder when provided. `--env-file PATH` selects a specific file. Variables already in the process take priority. After setting Windows User or Machine variables, open a new terminal so GroundMark inherits them.

Blank or unset `OPENAI_BASE_URL` uses the SDK default. A missing explicit environment file produces an error. The endpoint must support Sol parsing and Luna chat; its URL does not select different models.

`groundmark` opens the web UI at `http://127.0.0.1:5805`. Use `--workspace`, `--port`, `--host`, and `--headless` to configure the UI. An occupied port produces an error; the launcher does not terminate another server. `run.cmd` runs `uv run groundmark` from the checkout and forwards arguments.

For terminal extraction, run `groundmark input.pdf output --all`, or `uv run groundmark input.pdf output --all` from the checkout. Without format flags, the command writes Markdown and its figure files. You can combine `--markdown --html --json --annotated-pdf --annotated-images --markdown-zip`, or use `--all` to select every format. UI-only options cannot be combined with a source file.

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

For development, use `uv sync` and `uv run python -m pytest tests`. The explicit `tests` path keeps archived release snapshots under `data/` out of collection. `pyproject.toml` defines runtime dependencies, and `uv.lock` locks the checkout environment. Compatibility requirements files install the local package. Run evaluation scripts from the checkout. The installed distribution uses the `src` Python package.

Build with `uv build`. The wheel bundles runtime code, four Markdown prompts, and the MIT license. The source archive also contains build metadata and README. Neither includes private documents, credentials, tests, evaluation scripts, or generated architecture files.

Publish releases on GitHub. This project does not publish to PyPI. Build from the release tag, attach the wheel, source archive, and `SHA256SUMS`, then test installation from the public asset URL. To upgrade a tool installation, use `uv tool install --force --python 3.14` with the new release's wheel URL. To remove it, use `uv tool uninstall groundmark`. pip and uv pip users install the new wheel URL in the same virtual environment.

Upload a supported PDF or image, choose the first and last pages, and select Parse. You can use Input preview before making a model call. The Markdown, Annotated, HTML, and JSON tabs show the results.

Each UI parse creates `data/parse/runs/<run-id>/`. You can download Markdown, an annotated PDF, HTML, and JSON. Copy controls are available for rendered Markdown, raw Markdown, and JSON.

Clean and Full change the Markdown and HTML views, including copied and downloaded output. Switching views does not call the model again. Clean hides blocks classified as running headers or footers. If the document has figure crops, download the Markdown ZIP to keep its images. HTML embeds them.

The default extraction has no running-header or footer classifications, so Clean and Full show the same blocks for those results. Files written by the graph keep full content; UI downloads use the selected view. Switching views cannot add structure missing from the extraction.

Detailed layout is experimental and off by default because source review found new transcription errors in this mode. Enabling it changes the prompt and response schema and clears the previous result. Select Parse to run it in the UI, or pass `--detailed-layout` to `groundmark` with a source file and output directory. Direct callers can also pass `detailed_layout=True` to `run_graph` or `parse_document`. Read the [layout evaluation](LAYOUT-EVALUATION.md) before using it for work where source values matter.

| Symptom | Check |
| --- | --- |
| Missing API key | Confirm `OPENAI_API_KEY` is present without printing its value. |
| Unsupported model | Parsing accepts Sol; chat uses Luna at medium reasoning. |
| Page parse failure | Review the page diagnostic; successful pages may remain downloadable. |
| No annotation | Blocks need valid normalized bounding boxes; text artifacts remain usable. |
| Slow document | Select a smaller range; pages intentionally run sequentially. |

Run `uv sync`, then `uv run python -m pytest tests` after changing code or prompts. The tests use fake model responses and make no paid calls.

After parsing, open Chat to see which pages are available. Answers use parsed text from those pages and cite them inline. Clear chat starts a new conversation without parsing again. Changing the file, page range, or detailed-layout setting clears the result and requires another parse. Chat is unavailable when no pages were parsed successfully.

Questions can contain up to 2,000 characters. Answers have a 120-word limit, including citations, and the model sees only the last six accepted turns. Requests have a 200 KB serialized UTF-8 limit, with 30 KB reserved before drafting for policies, schemas, and verification. Select a smaller page range if the parsed document is too large. Each call allows 8,192 output tokens, including reasoning. The app does not display rejected or incomplete answers. Both chat calls count toward the session estimate.

The optional live chat check uses synthetic data and makes paid calls: `uv run --no-project --python .venv\Scripts\python.exe -m scripts.evaluate_chat`. It saves results to ignored `data/parse/chat-evaluation.json` and exits with an error if a case fails. Passing these cases does not establish protection against every attack.
