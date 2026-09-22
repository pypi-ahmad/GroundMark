# Contributing

Keep changes within the document product boundary: scanned PDFs or images become grounded Markdown, HTML, JSON, annotations, and chat over successfully parsed pages. Adding a business-field schema requires an explicit product decision.

Route `gpt-6-sol` calls through `src/llm.py`. Preserve page order and keep the page image authoritative when preceding-page context disagrees with it.

Route document chat through `src/chat.py`. Keep Luna at medium reasoning, retain evidence validation and independent verification, and load every authored model instruction from Markdown. Never stream or persist unverified candidates. The optional live evaluation uses synthetic data: `uv run --no-project --python .venv\Scripts\python.exe -m scripts.evaluate_chat`.

Before submitting a change:

1. Add or update focused tests.
2. Install `requirements-dev.txt`, then run `uv run --no-project --python .venv\Scripts\python.exe -m pytest`.
3. Run `git diff --check`.
4. Update current documentation when behavior changes.

Never commit credentials, uploaded documents, or generated run artifacts.
