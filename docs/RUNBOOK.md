# Runbook

Install `uv`, set `OPENAI_API_KEY`, and run `run.cmd`. The launcher creates `.venv`, installs `requirements.txt` when needed, and starts Streamlit on port `5805`.

The launcher stops an existing process that is listening on port `5805`. To manage the environment and port yourself, install the dependencies and run:

```powershell
uv run --no-project --python .venv\Scripts\python.exe -m streamlit run src/ui/app.py --server.port=5805 --logger.level=info
```

Upload a supported PDF or image, choose an inclusive page range, and select Parse. The Input preview tab works before a model call. Parsed results appear in the Markdown, Annotated, HTML, and JSON tabs.

Every parse creates `data/parse/runs/<run-id>/`. The UI provides downloads for Markdown, annotated PDF, HTML, and JSON. It also provides copy controls for rendered Markdown, raw Markdown, and JSON.

| Symptom | Check |
| --- | --- |
| Missing API key | Confirm `OPENAI_API_KEY` is present without printing its value. |
| Unsupported model | Parsing accepts Sol; chat uses Luna at medium reasoning. |
| Page parse failure | Review the page diagnostic; successful pages may remain downloadable. |
| No annotation | Blocks need valid normalized bounding boxes; text artifacts remain usable. |
| Slow document | Select a smaller range; pages intentionally run sequentially. |

Install `requirements-dev.txt`, then run `uv run --no-project --python .venv\Scripts\python.exe -m pytest` after code or prompt changes. The test suite uses fakes and makes no paid model calls.

After parsing, open Chat. It lists available and unavailable pages. Responses use only available parsed text and cite pages inline. Clear chat resets the conversation without reparsing. Changing the uploaded file or page range invalidates the result and requires another parse. Failed or empty parses cannot be used for chat.

Questions are limited to 2,000 characters and answers to 120 words, including citations. Only the last six accepted turns enter model context. Requests are capped at 200 KB serialized UTF-8 with 30 KB reserved before drafting for policies, schemas, and verification. Oversized documents require a smaller parsed range. Each call allows 8,192 output tokens, including reasoning. Rejected or incomplete candidates are never displayed. Both calls contribute to the session estimate.

The optional live check makes paid calls using synthetic data only: `uv run --no-project --python .venv\Scripts\python.exe -m scripts.evaluate_chat`. Results are saved under ignored `data/parse/chat-evaluation.json`; the command exits nonzero on a failed case. A passing finite evaluation is not proof against all attacks.
