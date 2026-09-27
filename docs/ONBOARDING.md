# Contributor onboarding

Use this guide to get from a fresh checkout to a tested local change. You do not need a provider key or model download.

## First session

1. Install Python 3.14+ and [uv](https://docs.astral.sh/uv/getting-started/installation/). Clone the repository and open its root in PowerShell.
2. Run `uv sync --locked`, then `uv run --locked python -m pytest tests -q --import-mode=importlib`.
3. Read [Developer guide](DEVELOPER-GUIDE.md#trace-one-page) for the page path and [Python API](PYTHON-API.md) for the public boundaries. Keep [Architecture](ARCHITECTURE.md) nearby when a change crosses modules.
4. Make one small change with its nearest test. Run that test first, then the complete offline suite and `git diff --check`.

The suite is designed around fake layouts and fake Sol responses. A missing `OPENAI_API_KEY` is expected for these checks. Never add a real key to a test or a committed file.

## Find the right starting point

| If your change concerns... | Start with... |
| --- | --- |
| Source files, page numbers, image dimensions | `src/preprocess.py`, `tests/test_preprocess.py` |
| ONNX preparation or CPU recovery | `src/layout_detector.py`, `tests/test_layout_detector.py` |
| Contours, hints, matching, or reading order | `src/layout_reconcile.py`, `tests/test_layout_reconcile.py` |
| Sol failures or partial documents | `src/parse.py`, `src/graph.py`, their tests |
| Markdown, HTML, figures, annotated outputs | `src/markdown.py`, `src/figures.py`, `src/annotate.py`, their tests |
| CLI or Streamlit behavior | `src/cli.py`, `src/ui/app.py`, their tests |
| Document chat | `src/chat.py`, `tests/test_chat.py` |

The page raster and V3 result must refer to the same source page. Matched layout geometry is normalized to 0–1 for the application; raw pixel geometry stays in metadata. Sol owns transcription and semantic structure. Review these contracts before changing a schema or a match rule.

## A first contribution

Pick a focused documentation or test gap that you can verify without model calls. For example, add an assertion to an existing renderer test for an escaping case, then run `uv run --locked python -m pytest tests/test_markdown.py -q --import-mode=importlib`. If you change runtime behavior, add a regression test that would fail on the old behavior. Update current docs when the contract changes; leave historical evaluation reports and generated `openwiki/` pages untouched unless that work is explicitly requested.

No branch, commit, PR, or publication is implied by a local implementation request. When contributing through GitHub, follow the requested delivery workflow and check [Contributing](CONTRIBUTING.md) and the [contributor runbook](CONTRIBUTOR-RUNBOOK.md) before submitting.

The [Zero to mastery tutorial](ZERO-TO-MASTERY.md) follows a page through the code with checkpoints.
