---
type: architecture
title: Parsing Pipeline Architecture
description: How GroundMark rasterizes selected pages, attempts V3 layout, transcribes with Sol, and exports full or partial results.
tags: [architecture, parsing, langgraph, diagnostics, layout]
verified:
  - by: openwiki/0.6.0
    at: 2026-09-26T10:39:39.522Z
sources:
  - id: openwiki-source-8ee12598dca25a2c6443ae09
    resource: repo://src/diagnostics.py
  - id: openwiki-source-91eeb4c49f698320d444439b
    resource: repo://src/graph.py
  - id: openwiki-source-efa8067f082e9586439b86d3
    resource: repo://src/parse.py
  - id: openwiki-source-dc6b607b77f47425803c062e
    resource: repo://src/preprocess.py
generated: { by: "codex", at: "2026-09-26T10:39:39.522Z" }
---

# Parsing Pipeline Architecture

GroundMark has a deliberately fixed extraction pipeline: `preprocess -> parse -> END`. `run_graph` creates isolated run state, validates the requested model, formats, and rendering view, and streams progress from the compiled LangGraph. There is no extraction review or correction loop.

## Control flow and state ownership

`run_graph` allocates a unique run ID, output directory, usage ledger, UTC start time, original filename, and export settings. The preprocess node verifies the source, computes its SHA-256 grounding identifier, and fills defaults for callers that invoke the compiled graph directly. The parse node then owns parsing and export orchestration; it catches terminal exceptions and returns a status rather than allowing an extraction failure to escape.

The parser is locked to `gpt-6-sol`. Default extraction uses the legacy response schema and `parse-page.md`. The separate, experimental `detailed_layout` option switches to the structured prompt and schema; legacy responses are converted to `ParsePage` before downstream processing. V3 layout runs in either mode when available.

## Preprocessing and page selection

Preprocessing accepts supported raster images or PDFs. Raster input is a one-page document; PDF page counts come from PDFium. Invalid files, unsupported extensions, and invalid one-based inclusive page ranges are rejected before model calls. PDFs render at 200 DPI, then selected pages are capped to a 1,600-pixel long edge and encoded as PNG. The payload carries the source hash plus authoritative page number and pixel dimensions. The same rendered page image is supplied to V3 and Sol; V3 does not change this raster profile.

The graph's first preprocess step establishes identity and run state. `parse_document` then calls `preprocess_pages` for the complete selected range. Direct parser callers save `<doc_sha>.json` by default; graph callers disable that write because the graph's export layer owns the selected artifacts.

## Sequential model calls

Pages are processed in source order. A single V3 runtime is prepared before the range; each page gets one V3 layout attempt before the Sol request. The applicable Markdown prompt receives compact `given_layout` regions (or an empty region list on layout fallback), while Sol receives the full image and remains responsible for transcription and tables. There is no second paid Sol call when V3 fails. Sol's strict legacy or detailed response is validated, then converted to `ParsePage` and conservatively reconciled with V3. Preprocessing remains authoritative for page number and pixel dimensions.

V3 can miss a page region, disagree with Sol, or fail at initialization, inference, conversion, or reconciliation. A rejected region match leaves the original Sol block intact. A page-level V3 failure is recorded as `layout_fallback` with stage/code/device/timing where available; validated Sol blocks still make that page successful. An invalid source image or failed Sol response instead fails that page. Layout metadata is stored separately from the strict Sol response schemas.

Each successful page contributes block text and table rows to context for later pages. The next request receives at most the last 12,000 characters of accumulated successful-page context. Failed pages contribute no context, but they do not stop later pages from being attempted. Progress events report completed, total, successful, and failed counts after every page in source order.

## Diagnostics and outcomes

Every attempted page gets a `PageDiagnostic`. Provider refusals, incomplete responses, HTTP or transport errors, content filtering, and invalid responses are normalized into diagnostic outcomes. Diagnostic sanitization accepts only bounded identifiers and refuses values that resemble URLs, credentials, or configured secret values; malformed token counts are not reported as usage.

`parse_document` returns all successful pages alongside ordered diagnostics, layout metadata, and a separate list of content-filtered page numbers. The graph maps that result into three run statuses:

- `parsed` when pages succeeded without reported page failures;
- `parsed_partial` when at least one page succeeded and another page was filtered or otherwise failed;
- `parse_failed` when no usable pages remain or a pipeline-level exception occurs.

Partial extraction is intentionally useful: successful pages continue to exports, while `parse_error` summarizes omitted pages. A Sol-successful page using layout fallback is retained, not treated as an omitted page; its diagnostic exposes the degraded layout. An all-filtered or fully failed result retains diagnostics but does not produce Markdown or annotations. Usage entries are held in the run-local ledger and survive failures that occur after a provider request. Progress includes preparation/device information and per-page match counts without provider text.

## Verified boundaries

Focused tests prove that page identity and order survive mixed outcomes, only successful content enters subsequent-page context, and all-failed diagnostics persist. Graph tests cover model rejection before preprocessing, isolated concurrent run artifacts and usage ledgers, partial artifact retention, all-filtered failure, and direct compiled-graph initialization.

See [V3 Layout Runtime](../concepts/v3-layout-runtime.md) for model preparation and fallback, [Layout Model and Rendering](../concepts/layout-and-rendering.md) for reconciliation and normalized extraction data, [Artifacts and Export Lifecycle](../workflows/artifacts-and-exports.md) for persistence, and [Grounded Document Chat](../features/document-chat.md) for the separate workflow that consumes successful pages.
