---
type: architecture
title: Parsing Pipeline Architecture
description: How GroundMark validates and rasterizes documents, parses pages sequentially with GPT-6 Sol, records diagnostics, and turns full or partial results into artifacts.
tags: [architecture, parsing, langgraph, diagnostics]
verified:
  - by: openwiki/0.5.2
    at: 2026-09-23T13:34:05.703Z
sources:
  - id: openwiki-source-8ee12598dca25a2c6443ae09
    resource: repo://src/diagnostics.py
  - id: openwiki-source-91eeb4c49f698320d444439b
    resource: repo://src/graph.py
  - id: openwiki-source-efa8067f082e9586439b86d3
    resource: repo://src/parse.py
  - id: openwiki-source-9f96f06bbd9cdd32677cab48
    resource: repo://tests/test_graph.py
  - id: openwiki-source-c3bd80e13bca0fabc8af5c04
    resource: repo://tests/test_parse.py
generated: { by: "codex", at: "2026-09-23T13:34:05.703Z" }
---

# Parsing Pipeline Architecture

GroundMark has a deliberately fixed extraction pipeline: `preprocess -> parse -> END`. `run_graph` creates isolated run state, validates the requested model, formats, and rendering view, and streams progress from the compiled LangGraph. There is no extraction review or correction loop.

## Control flow and state ownership

`run_graph` allocates a unique run ID, output directory, usage ledger, UTC start time, original filename, and export settings. The preprocess node verifies the source, computes its SHA-256 grounding identifier, and fills defaults for callers that invoke the compiled graph directly. The parse node then owns parsing and export orchestration; it catches terminal exceptions and returns a status rather than allowing an extraction failure to escape.

The parser is locked to `gpt-6-sol`. Both the graph boundary and `parse_document` reject another model before extraction proceeds, and the LLM builder has no fallback to a different model. Default extraction uses the legacy response schema and `parse-page.md`. The experimental `detailed_layout` option switches to the structured prompt and schema, but legacy responses are converted into the same `ParsePage` representation, so downstream state always uses one `ParseResult` contract.

## Preprocessing and page selection

Preprocessing accepts supported raster images or PDFs. Raster input is a one-page document; PDF page counts come from PDFium. Invalid files, unsupported extensions, and invalid one-based inclusive page ranges are rejected before model calls. Selected pages are rendered as PNG payloads, capped to a 1,600-pixel long edge, and carry the source hash plus authoritative page number and pixel dimensions.

The graph's first preprocess step establishes identity and run state. `parse_document` then calls `preprocess_pages` for the complete selected range. Direct parser callers save `<doc_sha>.json` by default; graph callers disable that write because the graph's export layer owns the selected artifacts.

## Sequential model calls

Pages are processed in source order with one model call at a time. Before each call, GroundMark renders the applicable Markdown prompt and sends it with the page image through the structured-output client. Page number and geometry returned by the model are discarded in favor of the values established during preprocessing; only the model's layout blocks are trusted.

Each successful page contributes block text and table rows to context for later pages. The next request receives at most the last 12,000 characters of accumulated successful-page context. Failed pages contribute no context, but they do not stop later pages from being attempted. Progress events report completed, total, successful, and failed counts after every page in source order.

## Diagnostics and outcomes

Every attempted page gets a `PageDiagnostic`. Provider refusals, incomplete responses, HTTP or transport errors, content filtering, and invalid responses are normalized into diagnostic outcomes. Diagnostic sanitization accepts only bounded identifiers and refuses values that resemble URLs, credentials, or configured secret values; malformed token counts are not reported as usage.

`parse_document` returns all successful pages alongside the ordered diagnostics and a separate list of content-filtered page numbers. The graph maps that result into three run statuses:

- `parsed` when pages succeeded without reported page failures;
- `parsed_partial` when at least one page succeeded and another page was filtered or otherwise failed;
- `parse_failed` when no usable pages remain or a pipeline-level exception occurs.

Partial extraction is intentionally useful: successful pages continue to exports, while `parse_error` summarizes omitted pages. An all-filtered or fully failed result retains diagnostics but does not produce Markdown or annotations. Usage entries are held in the run-local ledger and survive failures that occur after a provider request.

## Verified boundaries

Focused tests prove that page identity and order survive mixed outcomes, only successful content enters subsequent-page context, and all-failed diagnostics persist. Graph tests cover model rejection before preprocessing, isolated concurrent run artifacts and usage ledgers, partial artifact retention, all-filtered failure, and direct compiled-graph initialization.

See [Layout Model and Rendering](../concepts/layout-and-rendering.md) for the normalized extraction data, [Artifacts and Export Lifecycle](../workflows/artifacts-and-exports.md) for post-parse persistence, and [Grounded Document Chat](../features/document-chat.md) for the separate workflow that consumes successful pages.
