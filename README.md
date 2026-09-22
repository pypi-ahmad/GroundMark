# Agentic Document Parsing

This app turns scanned PDFs and images into layout-aware Markdown with `gpt-6-sol`.

The parser preserves document structure and content without extracting business fields, applying a domain schema, or correcting values. It keeps internal page, block, and bounding-box data for reading order, annotations, and JSON output. After parsing, document chat can answer questions and summarize the parsed pages.

## Outputs

- Input preview shows the selected source pages before processing.
- Markdown has rendered and raw views, plus copy and download controls.
- Annotated shows grounded block overlays and provides a PDF download.
- HTML shows the self-contained rendered output and provides a download.
- JSON shows the internal layout data with copy and download controls.
- Chat answers document questions with `gpt-6-luna` at medium reasoning, using short responses and inline page references.

Each run writes artifacts beneath `data/parse/runs/<run-id>/`.

## How it works

The app sends pages to `gpt-6-sol` in source order. Each request can include up to 12,000 characters from earlier parsed pages to help preserve continued headings, tables, and reading order. Python renders Markdown, HTML, JSON, and annotations from the returned layout blocks.

The pipeline follows the parse-first approach described by [LlamaParse](https://developers.llamaindex.ai/llamaparse/parse/getting_started/) and the grounded Markdown and annotation workflow shown by [LandingAI ADE](https://docs.landing.ai/ade/ade-parse-visualize-sample). The official [GPT-6 Sol page](https://developers.openai.com/api/docs/models/gpt-6-sol) documents the model capabilities and pricing.

## Setup

1. Install `uv` and set `OPENAI_API_KEY`. Optional endpoint settings are listed in `.env.example`.
2. Run `run.cmd`.

The launcher creates `.venv`, installs `requirements.txt` when it changes, and starts Streamlit on port `5805`. If you manage the environment yourself, start the app with `streamlit run src/ui/app.py`.

Supported inputs are PDF, PNG, JPEG, TIFF, and WebP. Parsing accepts only `gpt-6-sol`; chat uses only `gpt-6-luna`.

Chat uses only successfully parsed pages from the current run, never original files or failed pages. It checks source excerpts and independently verifies each answer before display. It refuses unrelated requests and has no tools or browsing. These controls reduce prompt-injection risk but cannot guarantee immunity to every attack. Chat history stays in the browser session and resets when the document, page range, or parse run changes.

For development, install the test dependency and run the suite through uv:

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt
uv run --no-project --python .venv\Scripts\python.exe -m pytest
```

See [Architecture](docs/ARCHITECTURE.md), [Model](docs/MODEL.md), [Prompts](docs/PROMPTS.md), and the [Runbook](docs/RUNBOOK.md).
