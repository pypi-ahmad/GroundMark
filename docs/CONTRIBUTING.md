# Contributing

GroundMark turns scanned PDFs and images into grounded Markdown, HTML, JSON, annotations, and chat over parsed pages. Keep changes within that scope. A business-field schema requires an explicit product decision.

Send `gpt-6-sol` requests through `src/llm.py`. Keep pages in source order and follow the page image when preceding-page context disagrees with it.

Keep document chat in `src/chat.py`, with Luna at medium reasoning, evidence checks, and separate answer verification. Store authored model instructions in Markdown. Do not stream or save unverified chat drafts. The optional chat evaluation uses synthetic data and makes paid calls: `uv run --no-project --python .venv\Scripts\python.exe -m scripts.evaluate_chat`.

Layout schema changes must keep older JSON loadable. Presentation filters must not change stored extraction or chat evidence. When changing structure or rendering, test how the code handles unknown metadata and whether it preserves the source text.

Keep V3 metadata outside the strict model-facing schemas. Class docstrings on Pydantic models can change generated schema descriptions, so document schema types in the [Python API reference](PYTHON-API.md) unless a schema change is intentional. Public functions use concise docstrings in the existing style.

V3 suggests geometry and order; Sol supplies text and tables. Preserve every Sol field on misses, weak/ambiguous matches, split/merge cases, and label/role disagreement. Runtime or reconciliation failure must retain Sol extraction with safe diagnostics. Test these contracts with injected runtimes and fake Sol responses; ordinary tests must not load weights or make paid calls. New matching policies need old-artifact loading tests and real-page calibration before quality claims.

Detailed layout remains optional because source review found new transcription errors. The [layout evaluation](LAYOUT-EVALUATION.md) records those errors and the word-token scores. That run used the full live-call allowance. A new paid comparison needs a new allowance and output directory. Keep dated reports faithful to their original runs when updating current guidance.

Before submitting a change:

1. Add or update focused tests.
2. Run `uv sync`, then `uv run python -m pytest tests`.
3. Run `git diff --check`.
4. Update current documentation when behavior changes.

Never commit credentials, uploaded documents, or generated run artifacts.

The `layout` extra is optional for imports and offline tests. Use `uv run --extra layout` for local V3 inference, and report CPU/GPU smoke checks separately from unit tests. A cache hit or a passing fake-runtime test does not prove native inference works. See [runtime verification](LAYOUT-V3.md#verification).

For documentation changes, verify claims against source and tests, preserve authored prompts and historical reports, and leave generated `openwiki/` pages to their generator. Update the editable diagram JSON and regenerate its HTML and image artifacts together when a flow changes.

When changing packaging or the CLI, test format selection with fake responses. Build with `uv build`, then verify the installed wheel outside the checkout. Keep `.env`, user documents, local indexes, and generated architecture screenshots out of release artifacts. Review release files before publishing. Use GitHub releases for distribution; the PyPI name belongs to another project. Contributions use the [MIT license](../LICENSE).
