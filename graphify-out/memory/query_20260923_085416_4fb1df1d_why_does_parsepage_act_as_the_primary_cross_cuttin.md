---
type: "query"
date: "2026-09-23T08:54:16.217039+00:00"
question: "Why does ParsePage act as the primary cross-cutting bridge between parsing, layout contracts, evaluation harnesses, and chat evidence?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["ParsePage", "ParseResult", "ParseBlock", "LegacyParsePage", "parse_document()", "document_pages()"]
---

# Q: Why does ParsePage act as the primary cross-cutting bridge between parsing, layout contracts, evaluation harnesses, and chat evidence?

## Answer

Expanded from original query via vocab: ['parse', 'page', 'layout', 'contract', 'evaluation', 'chat', 'evidence', 'result', 'block', 'pipeline']. Traversal revealed ParsePage (src/layout.py#L130) is the foundational atomic schema representing a parsed page. It connects: (1) LLM extraction via ParsePage and LegacyParsePage.to_page(); (2) Layout grounding storing ParseBlock with normalized BBox geometry; (3) Rendering in src/markdown.py for HTML/Markdown generation; (4) Visual annotation in src/annotate.py drawing bounding boxes; (5) Evidence verification in src/chat.py where page block text provides the ground truth for citation checks; and (6) Evaluation harnesses (scripts/evaluate_*.py) comparing baseline and candidate extraction runs.

## Outcome

- Signal: useful

## Source Nodes

- ParsePage
- ParseResult
- ParseBlock
- LegacyParsePage
- parse_document()
- document_pages()