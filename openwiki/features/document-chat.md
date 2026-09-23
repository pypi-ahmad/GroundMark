---
type: feature
title: Grounded Document Chat
description: How GroundMark answers document-only questions through structured drafting, deterministic evidence checks, and an independent verification call.
tags: [chat, grounding, verification, security]
verified:
  - by: openwiki/0.5.2
    at: 2026-09-23T13:34:05.703Z
sources:
  - id: openwiki-source-184127c1c45288fad066a874
    resource: repo://prompts/runtime/chat-answer.md
  - id: openwiki-source-958a1cf6c2ebed0319105250
    resource: repo://prompts/runtime/chat-verify.md
  - id: openwiki-source-6fff1fe747c855d3cff9f778
    resource: repo://src/chat.py
  - id: openwiki-source-34632138f005a3756a75f0e6
    resource: repo://src/ui/app.py
  - id: openwiki-source-6265b0ac565c1d474e82b6ec
    resource: repo://tests/test_chat.py
  - id: openwiki-source-880db0e148cafbaf6161b604
    resource: repo://tests/test_ui_diagnostics.py
generated: { by: "codex", at: "2026-09-23T13:34:05.703Z" }
---

# Grounded Document Chat

Document chat is a separate workflow from the extraction graph. It consumes only the current run's successfully parsed layout data; it does not reopen the source file, read failed pages, browse, or call tools. Its boundary is intentionally fail-closed: rejected drafts, provider failures, refusals, and malformed responses never reach the user as model text.

## Evidence preparation

`document_pages` builds a page-numbered text map from successful `ParseResult.pages`. It excludes content-filtered pages and any page whose diagnostic outcome is not `parsed`, skips pages without usable text, preserves all block text including classified headers and footers, and flattens table rows into text. Consequently, the evidence is the parser's output rather than the original image or PDF.

Questions must contain 1 to 2,000 characters. Before any paid request, the application also enforces a 200 KB serialized-context ceiling while reserving space for verification. At most the six most recent `answered` turns are included, and history may resolve references but is not factual evidence.

## Draft, check, verify

An answer follows three gates:

1. `chat-answer.md` asks `gpt-6-luna` for a strict structured `Draft`: `answer`, `not_found`, or `out_of_scope`, with statements tied to exact page excerpts.
2. Python rejects empty or oversized drafts, formatting and links, missing evidence, nonexistent pages, and quotations that are not exact normalized substrings of the parsed page. It adds page references itself and caps the final answer at 120 words and 2,000 characters.
3. Only a locally valid candidate reaches a second Luna call governed by `chat-verify.md`. The independent verifier approves only a fully document-scoped, excerpt-supported answer. The candidate is displayed only when `approved` is true.

`not_found` and `out_of_scope` decisions use fixed application messages and do not need the verifier. If a draft claims either decision while also supplying statements, it remains blocked.

## Request and failure boundaries

Both calls use `gpt-6-luna`, medium reasoning, strict JSON Schema output, `store=False`, and an 8,192-token output ceiling. The request contains no tools. The owned OpenAI client has a 60-second timeout and zero retries; an optional compatible base URL can be supplied by environment. The parser cannot use Luna, so chat and extraction model responsibilities remain separate.

Incomplete responses, refusal parts, unexpected output types, schema failures, provider errors, invalid evidence, verifier rejection, and over-limit content all fail without exposing raw completions, provider messages, or rejected candidates. Usage and sanitized stage diagnostics are still recorded when possible. Missing API configuration and empty documents produce local messages without a request.

## UI lifecycle

History lives only in Streamlit session state and is not shared between browser sessions. It clears when the upload is removed or replaced, the selected page range changes, detailed-layout mode changes, Parse is pressed again, or the user selects Clear chat. The input remains disabled until the current parse has usable pages. Changing Clean/Full rendering does not change chat evidence because chat reads the underlying result rather than a rendered view.

Tests exercise the exact two-call wire contract, exact-quote checks, fixed rejections, verifier vetoes, local no-call limits, accepted-history filtering, failed-page exclusion, refusal and incomplete-response privacy, Luna/parser separation, and UI reset behavior.

See [Parsing Pipeline Architecture](../architecture/parsing-pipeline.md) for page outcomes and [Layout Model and Rendering](../concepts/layout-and-rendering.md) for the underlying data contract.
