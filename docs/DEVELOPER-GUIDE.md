# Developer guide

GroundMark's Python package is named `src`. The CLI, Streamlit UI, and direct `run_graph` callers use the same parsing path. This guide is a map for changing that path; [Python API](PYTHON-API.md) lists callable contracts, and the [runbook](RUNBOOK.md) covers installation and operations.

## Set up a checkout

Use Windows PowerShell with Python 3.14+ and uv. From the repository root:

```powershell
uv sync --locked
uv run --locked python -m pytest tests -q --import-mode=importlib
```

The base environment runs offline tests without model weights or an API key. For the normal V3 launch path, install the optional runtime and run the CLI through uv:

```powershell
uv sync --locked --extra layout
uv run --locked --extra layout groundmark --help
```

`run.cmd` includes the layout extra. A real parse can download the pinned ONNX weights and make a paid Sol call; `--help` and the unit tests do neither. The only supported weight repository is `PaddlePaddle/PP-DocLayoutV3_onnx`. Its revision and file hashes are in `src/layout_detector.py`. Do not substitute a similarly named model repository.

## Trace one page

| Boundary | Source | What it owns |
| --- | --- | --- |
| Source inspection and rasterization | `src/preprocess.py` | Source hash, page range, 200-DPI PDF rendering, capped PNG payloads. |
| Run orchestration | `src/graph.py`, `src/parse.py` | Sequential pages, preceding-page context, progress, partial results, safe diagnostics. |
| V3 analysis | `src/layout_detector.py`, `src/layout_polygons.py` | Verified ONNX snapshot, actual CPU/CUDA execution, raw class/score/box/mask contour/native order. |
| Sol request | `src/llm.py`, `src/prompts.py`, `prompts/runtime/` | Whole-page visual transcription with bounded layout hints; default and detailed response profiles. |
| Reconciliation | `src/layout_reconcile.py`, `src/layout.py` | Normalized 0–1 geometry, one-to-one match evidence, V3-owned matched geometry/order, separately validated artifact metadata. |
| Output | `src/markdown.py`, `src/figures.py`, `src/annotate.py`, `src/export.py` | Python-rendered text, crops, selected geometry overlays, JSON, and selected files. |
| Interfaces | `src/cli.py`, `src/ui/app.py`, `src/chat.py` | Terminal/UI behavior and chat over successful parsed pages. |

The page image remains Sol's transcription source. V3 supplies layout evidence; it does not invent text, tables, or semantic heading levels. A qualified match adopts V3 geometry and order while preserving Sol content, block ID, and transcription confidence. Unmatched Sol blocks retain their boxes; unmatched V3 regions stay detector-only. An unavailable runtime or unusable guide sends no partial guide and uses Sol with a safe fallback diagnostic. A reconciliation invariant failure is a partial-document application error, not routine detector fallback. See [layout policy](LAYOUT-V3.md) for thresholds and limitations.

## Change a boundary safely

Start with the nearest source and test. `tests/test_layout_integration.py` exercises V3 plus fake Sol responses; `tests/test_layout_reconcile.py` covers matching; `tests/test_layout_detector.py` covers runtime and device behavior; `tests/test_annotate.py` covers overlays; `tests/test_parse.py` and `tests/test_graph.py` cover page/document failures. UI and CLI have separate tests. The tests use fake responses and must not download weights or call Sol.

For schema work, inspect `LegacyParsePage`, `ParsePage`, `ParseResult`, and `LayoutPageArtifact` in `src/layout.py`. The two Sol-facing page schemas are strict. Layout evidence belongs in the artifact models, not the model response. A Pydantic class docstring can change generated schema descriptions, so keep field documentation in [Python API](PYTHON-API.md) unless a schema change is deliberate. Saved JSON without layout metadata must remain loadable.

For prompt work, edit the authored Markdown files in `prompts/runtime/`, then run `tests/test_prompts.py`, `tests/test_parse.py`, and the prompt-contract tests. For rendering work, check Markdown, HTML, crops, annotations, and both clean/full views. For packaging work, consult [release checks](RUNBOOK.md#development-and-release-checks); `scripts/verify_release_artifacts.py` uses a deliberate file manifest.

Use `uv run --locked python -m pytest tests -q --import-mode=importlib` for the complete offline suite and `git diff --check` before handing off a change. Do not infer native CPU/CUDA success or layout accuracy from fake-runtime tests. The [contributor runbook](CONTRIBUTOR-RUNBOOK.md) gives a change-by-change checklist.
