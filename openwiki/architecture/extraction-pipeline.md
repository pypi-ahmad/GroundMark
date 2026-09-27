---
type: Architecture
title: Extraction pipeline
description: How GroundMark validates pages, combines local layout with whole-page Sol transcription, and produces partial-safe exports.
tags: [pipeline, extraction, pages]
verified:
  - by: openwiki/0.6.0
    at: 2026-09-27T09:37:20.794Z
sources:
  - id: openwiki-source-8ee12598dca25a2c6443ae09
    resource: repo://src/diagnostics.py
  - id: openwiki-source-91eeb4c49f698320d444439b
    resource: repo://src/graph.py
  - id: openwiki-source-efa8067f082e9586439b86d3
    resource: repo://src/parse.py
  - id: openwiki-source-dc6b607b77f47425803c062e
    resource: repo://src/preprocess.py
  - id: openwiki-source-c3bd80e13bca0fabc8af5c04
    resource: repo://tests/test_parse.py
generated: { by: "codex", at: "2026-09-27T09:37:20.794Z" }
---

# Extraction pipeline

`run_graph` is the supported application entry point. Its two-node graph first validates and hashes the source, then parses the selected pages and exports the requested artifacts. The CLI and Streamlit app call this same path. A run has its own ID, output directory, usage ledger, and final status (`parsed`, `parsed_partial`, or `parse_failed`).

## Page flow

1. [Preprocessing](../concepts/page-artifacts.md) accepts supported raster images or PDFs, checks source and page-range limits, and yields each selected page as a PNG with the source hash, original page number, and raster dimensions. PDFs render at 200 DPI subject to a 1,600-pixel long-edge cap.
2. `parse_document` prepares the shared [V3 runtime](../concepts/layout-v3.md) once and processes pages in source order. Each successful page contributes bounded text/table context to the next page.
3. For each page, `parse_page` validates the image, attempts V3, and projects a bounded region guide. Sol still sees the complete page image and returns either the legacy or detailed structured page schema. V3 then reconciles eligible blocks without replacing Sol content.
4. Page outcomes and safe diagnostics accumulate even when an individual page fails. The graph exports usable pages and reports partial status when appropriate. The direct parser can also save a `ParseResult` JSON; the graph instead delegates selected outputs to [export](../workflows/render-and-export.md).

V3 initialization, inference, conversion, or guide failures permit Sol transcription without a stale guide. Reconciliation defects are recorded as application errors while preserving the original validated Sol page. Invalid page images and rejected or malformed Sol responses keep page-failure handling; source validation and output setup errors can fail the run.

## Ownership boundaries

The source hash and raster dimensions come from preprocessing. Sol owns transcription, tables, block structure, and IDs. Qualified V3 matches own geometry, class metadata, confidence, and relative reading order. Python owns Markdown, HTML, figure crops, and annotations. No rendering path makes a model call.

See [page data](../concepts/page-artifacts.md) for saved representation and [diagnostics](../operations/running-and-diagnostics.md) for failure interpretation.
