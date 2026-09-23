# Runbook

Use the [README installation instructions](../README.md#install) for GitHub wheel installs with `uv tool`, `uv pip`, or pip, and for manual cloning. Python 3.14+ is required. All installed commands work outside the checkout.

Set `OPENAI_API_KEY`, and optionally `OPENAI_BASE_URL`, in the process environment or a `.env` file. The launcher loads the current folder's `.env`; the UI's `--workspace` changes that default folder. `--env-file PATH` selects an explicit file. Existing environment variables win. Blank or unset `OPENAI_BASE_URL` uses the SDK default. An explicit missing environment file is an error. The endpoint must support Sol parsing and Luna chat; changing its URL does not select different models.

`groundmark` opens the web UI at `http://127.0.0.1:5805`. Use `--workspace`, `--port`, `--host`, and `--headless` to configure the UI. An occupied port produces an error; the launcher does not terminate another server. `run.cmd` runs `uv run groundmark` from the checkout and forwards arguments.

For terminal extraction, run `groundmark input.pdf output --all`, or `uv run groundmark input.pdf output --all` from the checkout. Without format flags, only Markdown and its figure files are written. Formats combine: `--markdown --html --json --annotated-pdf --annotated-images --markdown-zip`. `--all` selects every format. UI-only options cannot be combined with a source file.

The input must be outside the output directory. An existing nonempty output directory requires `--overwrite`; this replaces generated paths and leaves unrelated files alone. Use a fresh directory to avoid mixing artifacts from different runs or page ranges. Arguments, configuration, input readability, and page bounds are checked before model calls. Pages are 1-based and inclusive.

CLI artifacts use these paths, where `<sha>` is the source document hash:

| Selection | Paths |
| --- | --- |
| Markdown | `<sha>.md`, with figure PNGs under `images/` |
| HTML | `<sha>.html`, including embedded figure images |
| JSON | `<sha>.json`, including full page diagnostics |
| Annotated PDF | `annotated/<sha>.pdf` |
| Annotated images | `annotated/<sha>/page_NNN.png` |
| Markdown ZIP | `<sha>.zip`, containing `document.md` and its `images/` |

HTML-only and ZIP-only extraction do not write loose images. JSON-only extraction skips presentation work. CLI annotations do not create a metadata sidecar; the UI retains its existing annotation sidecar. A failed page does not discard successful pages. If all pages fail, only requested JSON diagnostics can be written. Export failures preserve other completed artifacts.

The CLI prints artifact paths to stdout and progress, status, and diagnostics to stderr. Exit codes: `0` success, `1` failed extraction/runtime error, `2` invalid arguments/configuration, `3` partial extraction or export/figure problems, `130` interruption. `--view clean` filters presentation only; default CLI view is `full`, and JSON is always complete.

For development, use `uv sync` and `uv run python -m pytest`. `pyproject.toml` defines runtime dependencies and `uv.lock` locks the checkout environment. Compatibility requirements files install the local package. Evaluation scripts remain checkout-only tools. The installed distribution retains the existing `src` Python package.

Build with `uv build`. The wheel bundles runtime code, four Markdown prompts, and the MIT license. The source archive also contains build metadata and README. Neither includes private documents, credentials, tests, evaluation scripts, or generated architecture files.

Releases are published on GitHub, not PyPI. Build from the release tag, attach the wheel, source archive, and `SHA256SUMS`, then test installation from the public asset URL. To upgrade a tool installation, use `uv tool install --force --python 3.14` with the new release's wheel URL. To remove it, use `uv tool uninstall groundmark`. pip and uv pip users install the new wheel URL in the same virtual environment.

Upload a supported PDF or image, choose the first and last pages, and select Parse. You can use Input preview before making a model call. The Markdown, Annotated, HTML, and JSON tabs show the results.

Each UI parse creates `data/parse/runs/<run-id>/`. You can download Markdown, an annotated PDF, HTML, and JSON. Copy controls are available for rendered Markdown, raw Markdown, and JSON.

Clean and Full change the Markdown and HTML views, including copied and downloaded output. Switching views does not call the model again. Clean hides blocks classified as running headers or footers. If the document has figure crops, download the Markdown ZIP to keep its images. HTML embeds them.

The default extraction has no running-header or footer classifications, so Clean and Full show the same blocks for those results. Files written by the graph keep full content; UI downloads use the selected view. Switching views cannot add structure missing from the extraction.

Detailed layout is experimental and off by default. Source review found new transcription errors in this mode. Enabling it changes the prompt and response schema and clears the previous result. Select Parse to run it. CLI callers can pass `--detailed-layout` to `src.graph` or `src.parse`. Read the [layout evaluation](LAYOUT-EVALUATION.md) before using it for work where source values matter.

| Symptom | Check |
| --- | --- |
| Missing API key | Confirm `OPENAI_API_KEY` is present without printing its value. |
| Unsupported model | Parsing accepts Sol; chat uses Luna at medium reasoning. |
| Page parse failure | Review the page diagnostic; successful pages may remain downloadable. |
| No annotation | Blocks need valid normalized bounding boxes; text artifacts remain usable. |
| Slow document | Select a smaller range; pages intentionally run sequentially. |

Run `uv sync`, then `uv run python -m pytest` after changing code or prompts. The tests use fake model responses and make no paid calls.

After parsing, open Chat to see which pages are available. Answers use parsed text from those pages and cite them inline. Clear chat starts a new conversation without parsing again. Changing the file, page range, or detailed-layout setting clears the result and requires another parse. Chat is unavailable when no pages were parsed successfully.

Questions can contain up to 2,000 characters. Answers have a 120-word limit, including citations, and the model sees only the last six accepted turns. Requests have a 200 KB serialized UTF-8 limit, with 30 KB reserved before drafting for policies, schemas, and verification. Select a smaller page range if the parsed document is too large. Each call allows 8,192 output tokens, including reasoning. The app does not display rejected or incomplete answers. Both chat calls count toward the session estimate.

The optional live chat check uses synthetic data and makes paid calls: `uv run --no-project --python .venv\Scripts\python.exe -m scripts.evaluate_chat`. It saves results to ignored `data/parse/chat-evaluation.json` and exits with an error if a case fails. Passing these cases does not establish protection against every attack.
