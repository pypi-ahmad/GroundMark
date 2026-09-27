---
type: Workflow
title: Document-grounded chat
description: How parsed pages become bounded evidence for a locally checked and independently verified chat answer.
tags: [chat, grounding, evidence]
verified:
  - by: openwiki/0.6.0
    at: 2026-09-27T09:37:20.794Z
sources:
  - id: openwiki-source-6fff1fe747c855d3cff9f778
    resource: repo://src/chat.py
  - id: openwiki-source-34632138f005a3756a75f0e6
    resource: repo://src/ui/app.py
  - id: openwiki-source-6265b0ac565c1d474e82b6ec
    resource: repo://tests/test_chat.py
generated: { by: "codex", at: "2026-09-27T09:37:20.794Z" }
---

# Document-grounded chat

Chat is separate from extraction. It consumes text and table rows from successfully parsed source pages in `ParseResult`, including valid Sol-fallback pages. Failed and content-filtered pages are excluded. Layout-only regions never add text to chat, and Clean/Full presentation filtering does not remove evidence.

The UI accepts a document question only after usable pages exist. A question is capped at 2,000 characters, the request context at 200 KB, and history at the last six accepted answers. Changing the uploaded document, page range, or detailed profile clears the prior result and chat history.

For an answer, the chat module asks Luna for structured statements with page-and-quote evidence. Python checks that each quoted span appears in the named parsed page, rejects unsupported style and size, then makes a separate structured verification call. Only approved answers are shown, with page citations. Out-of-scope and not-found decisions use fixed messages; rejected drafts, provider errors, and malformed responses are not displayed. Usage from both calls is recorded even if a later step rejects the answer.

The checks ground the answer in parsed text, not the original document pixels. Extraction errors can therefore affect chat evidence; inspect [page provenance](../concepts/page-artifacts.md) and [rendering](render-and-export.md) when comparing an answer to a source page.
