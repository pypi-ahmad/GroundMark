# Contributor runbook

This runbook covers a contributor's work from the first edit through review. The [runtime runbook](RUNBOOK.md) covers installation, extraction, artifacts, and release operations.

## Before editing

Check `git status --short` and preserve unrelated work. Read the nearest source and tests, then identify which contract will change. Use the [developer map](DEVELOPER-GUIDE.md#trace-one-page) if the owner is unclear. Historical evaluation documents record their original runs; change current guidance instead of rewriting past results.

Choose a focused offline test before modifying a parsing boundary. Examples:

```powershell
uv run --locked python -m pytest tests/test_layout_reconcile.py -q --import-mode=importlib
uv run --locked python -m pytest tests/test_parse.py tests/test_graph.py -q --import-mode=importlib
uv run --locked python -m pytest tests/test_markdown.py tests/test_annotate.py -q --import-mode=importlib
```

## Review the result

1. Confirm the changed test exercises the real boundary and does not call a paid model or download weights.
2. Run the complete offline suite: `uv run --locked python -m pytest tests -q --import-mode=importlib`.
3. Run `git diff --check` and review `git diff` for accidental schema, prompt, model-repository, or generated-file changes.
4. Update the [Python API](PYTHON-API.md), [developer guide](DEVELOPER-GUIDE.md), or [runtime runbook](RUNBOOK.md) when their contracts changed. Verify new local links and example commands.
5. Report tests separately from live runtime and measured document quality. A fake-runtime pass does not prove CUDA execution or correspondence accuracy.

## Special cases

- V3 changes: keep `PaddlePaddle/PP-DocLayoutV3_onnx`, its pinned revision/checksums, user-cache behavior, complete contour and order decode, and bounded CPU recovery. Preserve the full-page Sol request. Inspect [V3 runtime and matching](LAYOUT-V3.md) before changing thresholds; current defaults are provisional.
- Schema changes: compare strict Sol-facing schemas and saved-artifact loading. Adding a Pydantic class docstring may change a generated schema description. Keep layout metadata separate from Sol's response.
- Fallback changes: distinguish runtime/guide fallback from an invalid source, rejected Sol response, or reconciliation invariant defect. Preserve already incurred usage and successful pages.
- Rendering changes: test both profiles, clean/full presentation, table content, crops, annotations, and legacy JSON loading as applicable. Presentation must not alter stored extraction or chat evidence.
- Prompt changes: edit the four authored runtime Markdown templates. Do not edit packaged/generated copies by hand.
- Documentation changes: check claims against current source/tests. Do not hand-edit generated `openwiki/` pages.
- Release changes: run the archive checks in [Runbook](RUNBOOK.md#development-and-release-checks). Building or testing does not authorize publishing.

## Handoff

State which files changed, the exact verification command and result, and what remains unverified. Mention a live model run only if one actually executed, with its device and sample provenance. Keep credentials, source documents, and raw provider errors out of reports. Create commits, push, or open a PR only when the task requests those actions.
