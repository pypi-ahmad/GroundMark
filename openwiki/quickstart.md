---
type: Guide
title: GroundMark quickstart
description: A task-oriented route into GroundMark's extraction, V3 layout, rendering, chat, operations, and verification knowledge.
tags: [quickstart, navigation, groundmark]
verified:
  - by: openwiki/0.6.0
    at: 2026-09-27T09:37:20.794Z
sources:
  - id: openwiki-source-0b361e5538aca06f3052fb20
    resource: repo://run.cmd
  - id: openwiki-source-2b2997093155122683b9ef80
    resource: repo://scripts/evaluate_layout.py
  - id: openwiki-source-7ccc14b679ba3c785e22d851
    resource: repo://scripts/evaluate_reconciliation.py
  - id: openwiki-source-f22340a3ad65b7791573c494
    resource: repo://src/cli.py
  - id: openwiki-source-3b4939e7f8a641c2af87c413
    resource: repo://src/export.py
  - id: openwiki-source-efa8067f082e9586439b86d3
    resource: repo://src/parse.py
  - id: openwiki-source-670417a58308fe16c6c4f8f6
    resource: repo://tests/test_layout_integration.py
generated: { by: "codex", at: "2026-09-27T09:37:20.794Z" }
---

# GroundMark quickstart

GroundMark turns supported scanned PDFs and images into structured page data and Python-rendered Markdown, HTML, annotations, and JSON. Local PP-DocLayoutV3 ONNX analysis guides layout, while Sol transcribes the complete page. Document chat works from successfully parsed page text.

## Find the right page

| If you need to… | Read |
| --- | --- |
| Trace an input from validation through partial-safe export | [Extraction pipeline](architecture/extraction-pipeline.md) |
| Understand Sol fields, normalized boxes, saved JSON, or diagnostics | [Page data and provenance](concepts/page-artifacts.md) |
| Understand pinned ONNX weights, contour/order decode, matching, or fallback | [V3 detection and reconciliation](concepts/layout-v3.md) |
| Change Markdown, HTML, figure crops, or annotation overlays | [Rendering and export](workflows/render-and-export.md) |
| Understand page-grounded answers and verification | [Document chat](workflows/document-chat.md) |
| Launch, configure, inspect a failed page, or interpret CLI exit codes | [Running and diagnostics](operations/running-and-diagnostics.md) |
| Choose tests or assess what layout replay can prove | [Tests and evaluation boundaries](testing/verification.md) |

## Run locally

Use Python 3.14+ and uv. From the checkout, `uv sync --extra layout` makes the optional local layout dependencies available; `run.cmd` launches `uv run --extra layout groundmark` on Windows. Set `OPENAI_API_KEY` without committing it. `groundmark` starts the loopback Streamlit UI; `groundmark input.pdf output --all` performs terminal extraction and may incur Sol charges. Use `uv run python -m pytest tests` for offline behavior checks.

This wiki is an evidence map, not a substitute for source and tests. V3 match counts and successful smoke runs do not establish document-quality accuracy; see [evaluation boundaries](testing/verification.md).
