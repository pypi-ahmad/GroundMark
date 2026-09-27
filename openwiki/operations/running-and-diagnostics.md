---
type: Runbook
title: Running and diagnosing GroundMark
description: Windows and uv launch paths, layout preparation, CLI results, safe diagnostics, and partial-output handling.
tags: [operations, windows, diagnostics]
verified:
  - by: openwiki/0.6.0
    at: 2026-09-27T09:37:20.794Z
sources:
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
  - id: openwiki-source-0b361e5538aca06f3052fb20
    resource: repo://run.cmd
  - id: openwiki-source-f22340a3ad65b7791573c494
    resource: repo://src/cli.py
  - id: openwiki-source-d502c275990c6476221bf080
    resource: repo://src/config.py
  - id: openwiki-source-8ee12598dca25a2c6443ae09
    resource: repo://src/diagnostics.py
  - id: openwiki-source-34632138f005a3756a75f0e6
    resource: repo://src/ui/app.py
  - id: openwiki-source-1a4987ab583c7b2ac6c4c14b
    resource: repo://tests/test_cli_extraction.py
  - id: openwiki-source-747ce984286d9a8fb9342632
    resource: repo://tests/test_launcher.py
generated: { by: "codex", at: "2026-09-27T09:37:20.794Z" }
---

# Running and diagnosing GroundMark

GroundMark requires Python 3.14 or newer. From the checkout, `run.cmd` invokes `uv run --extra layout groundmark` and forwards arguments. The layout extra contains the ONNX Runtime, Hugging Face Hub, NumPy, and OpenCV dependencies. Without a file, `groundmark` starts the local Streamlit UI; with a source and destination, it performs CLI extraction. Parsing may make paid Sol calls, so verify the page range first.

## Configuration and preparation

Provide `OPENAI_API_KEY` in the environment or `.env`; the process environment wins over the file. An optional `OPENAI_BASE_URL` must be HTTPS unless it targets loopback HTTP and cannot contain credentials, query, or fragment. UI binding is restricted to loopback. Resource-limit variables require positive integers.

`GROUNDMARK_LAYOUT_DEVICE=auto` is the default; `cpu` skips CUDA. The optional `GROUNDMARK_LAYOUT_MODEL_DIR` must resolve to an existing directory containing the two checksum-verified files from the pinned ONNX snapshot. Otherwise the user cache is used and first preparation may download files. Readiness reports the actual verified device, fallback reason, elapsed preparation time, and whether the runtime was reused. A later CUDA page-execution failure gets bounded CPU recovery and sticks to CPU when successful.

## Inspect a run

The CLI prints output paths to stdout and progress/status to stderr. Exit code 0 means complete success, 1 failure, 2 invalid invocation, 3 partial output or export/figure issues, and 130 interruption. By default, CLI extraction selects Markdown; `--all` or individual format flags select other outputs. A nonempty destination requires `--overwrite`, which does not delete unrelated files.

Inspect `page_diagnostics` and `layout_metadata` in JSON or the UI Layout summary. A layout fallback has a safe stage and code; it does not alone imply a failed Sol page. Null match counts mean no reconciliation was available, not zero matches. Reconciliation application errors are distinct from detector misses and leave the original Sol page and incurred usage available. An unmatched Sol block is a correspondence result, not proof that V3 missed content. Successful pages remain exportable when other pages fail.

Run focused tests with `uv run python -m pytest tests` after code changes. See [V3 mechanics](../concepts/layout-v3.md) and [verification boundaries](../testing/verification.md).
