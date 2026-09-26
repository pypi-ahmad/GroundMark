---
type: quickstart
title: GroundMark Quickstart
description: Install, configure, and run GroundMark through its Streamlit UI or terminal extractor, with routes into the architecture and contributor documentation.
tags: [quickstart, installation, cli, ui]
sources:
  - id: openwiki-source-51639ec4f9dc3fb84f820c05
    resource: repo://docs/RUNBOOK.md
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
  - id: openwiki-source-f22340a3ad65b7791573c494
    resource: repo://src/cli.py
  - id: openwiki-source-efa8067f082e9586439b86d3
    resource: repo://src/parse.py
  - id: openwiki-source-34632138f005a3756a75f0e6
    resource: repo://src/ui/app.py
generated: { by: "codex", at: "2026-09-26T10:39:39.522Z" }
verified:
  - by: openwiki/0.6.0
    at: 2026-09-26T10:39:39.522Z
---

# GroundMark Quickstart

GroundMark turns scanned PDFs and images into layout-aware Markdown, HTML, JSON, annotations, and document-grounded chat. It requires Python 3.14+ and an endpoint that supports `gpt-6-sol` for parsing and `gpt-6-luna` for chat.

## Install and configure

Install the published GitHub wheel with uv:

```powershell
uv tool install --python 3.14 "https://github.com/pypi-ahmad/GroundMark/releases/download/v0.1.1/groundmark-0.1.1-py3-none-any.whl"
```

Use the GitHub asset rather than PyPI, where the `groundmark` name belongs to another project. The published v0.1.1 wheel predates the V3 integration described below; that behavior is in the current checkout. For checkout development with V3, use `uv sync --extra layout` and prefix commands with `uv run --extra layout`.

Set the API key in the process or a `.env` file:

```powershell
$env:OPENAI_API_KEY = "your-api-key"
$env:OPENAI_BASE_URL = "https://your-compatible-endpoint.example/v1" # optional
```

An unset or blank base URL uses the OpenAI SDK default. Existing process variables take precedence over `.env`. Do not commit credentials.

## Choose a command mode

Running `groundmark` with no positional arguments launches the Streamlit UI at `http://127.0.0.1:5805`:

```powershell
groundmark
groundmark --workspace D:\Documents\GroundMark --port 5806
```

The workspace controls where the launcher reads `.env`; UI uploads and outputs use a per-session temporary directory. Upload a supported PDF, PNG, JPEG, TIFF, or WebP file, choose an inclusive page range, and select Parse. The result tabs expose input preview, Markdown, annotations, HTML, JSON, and chat. Each new parse has isolated artifacts.

Providing both a source and output directory selects terminal extraction instead:

```powershell
groundmark invoice.pdf output
groundmark invoice.pdf output --all
groundmark invoice.pdf output --markdown --html --start-page 2 --end-page 5
```

The CLI writes to the destination you supplied, not the UI workspace. Without a format flag it produces Markdown and usable figure images. Use a new or empty destination unless `--overwrite` is intentional; overwrite mode preserves unrelated existing files. The source must remain outside that destination.

## Understand the result

In the current checkout, selected pages are rasterized once. PP-DocLayoutV3 first proposes regions and reading order from each page image; Sol receives that same image and transcribes text and tables. The checkout downloads pinned V3 weights into the Hugging Face user cache on first use, probes the actual GPU or CPU device, and reuses the model in the process. A V3 miss, mismatch, or failure retains Sol blocks with safe layout diagnostics; a Sol page failure can still produce partial output. Successful pages remain usable when another page fails. Clean and Full are rendering choices: Clean hides only recognized running headers and footers, while JSON and chat retain the underlying successful extraction data. Detailed layout is a separate experimental Sol schema option and remains off by default.

Document chat uses Luna over successfully parsed page text. It makes a structured draft, checks exact cited excerpts locally, and asks a separate verifier before displaying an answer. It cannot browse or answer from the original file or failed pages.

## Where to go next

- [Parsing Pipeline Architecture](architecture/parsing-pipeline.md) traces preprocessing, model calls, state, diagnostics, and partial results.
- [V3 Layout Runtime and Reconciliation](concepts/v3-layout-runtime.md) explains cache, device fallback, geometry, matching, and limits.
- [Layout Model and Rendering](concepts/layout-and-rendering.md) explains schemas, Clean/Full behavior, tables, lists, escaping, and figures.
- [Artifacts and Export Lifecycle](workflows/artifacts-and-exports.md) maps formats, naming, destinations, and degraded output.
- [Grounded Document Chat](features/document-chat.md) documents its evidence and verification boundaries.
- [Development, Testing, and Evaluation](operations/development-and-testing.md) covers uv, tests, packaging, and separately authorized live evaluations.

For contributors, the baseline offline verification is `uv sync`, `uv run python -m pytest tests`, and `git diff --check`. These tests do not prove native V3 CPU/GPU execution or Sol transcription quality.
