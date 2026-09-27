---
type: Concept
title: Page data and provenance
description: GroundMark's Sol page schemas, normalized boxes, V3 metadata, validation, and safe per-page diagnostics.
tags: [schema, artifacts, diagnostics]
verified:
  - by: openwiki/0.6.0
    at: 2026-09-27T09:37:20.794Z
sources:
  - id: openwiki-source-8ee12598dca25a2c6443ae09
    resource: repo://src/diagnostics.py
  - id: openwiki-source-4f6651fd216a7537d3c7ab3e
    resource: repo://src/layout.py
  - id: openwiki-source-efa8067f082e9586439b86d3
    resource: repo://src/parse.py
  - id: openwiki-source-9dfb4747e2b4fc606f263438
    resource: repo://tests/test_diagnostics.py
  - id: openwiki-source-22823fdb2e93c5de789260d7
    resource: repo://tests/test_layout_structure.py
generated: { by: "codex", at: "2026-09-27T09:37:20.794Z" }
---

# Page data and provenance

`ParseResult` is the saved document artifact. It contains successful `ParsePage` entries, an extraction profile, content-filtered page numbers, per-page diagnostics, and optional validated V3 layout artifacts. Page numbers are 1-based. `BBox.xyxy` is a four-value normalized 0–1 rectangle; source pixel dimensions are stored separately.

## Content and structure

Sol returns block IDs, types, text, rectangular boxes, transcription confidence, and optional table rows. The default legacy profile is converted to the common page type with `structure: null`; the opt-in detailed profile can add heading levels, nested list items, and table cell spans. The model-facing strict schemas are separate from artifact-only V3 models. Python validates table shapes, nesting, and expanded cell limits before downstream rendering.

For a qualified match, the block keeps all Sol content fields while its compatible envelope box changes to the V3 AABB. Full detector contour, class ID and label, confidence, native order, raw pixel geometry, normalized geometry, guide-contour status, candidate evidence, and block-to-region decisions live in the layout artifact. Unmatched detector regions have no transcription block. Saved artifacts validate one-to-one region references, page dimensions, and policy-specific evidence. Older JSON without `schema_version` is upgraded on load, without changing the live Sol response schema.

## Diagnostics

`PageDiagnostic` separates Sol outcome from layout stage/code, CPU fallback and execution failures, and reconciliation application errors. It records actual device and timing when known. Its fields are bounded codes, counts, or allowlisted identifiers; raw provider text and request bodies are not persisted. Usage already incurred is retained when a later stage fails. A document can therefore contain successful pages alongside failure diagnostics rather than dropping all work.

Read [extraction flow](../architecture/extraction-pipeline.md), [V3 reconciliation](layout-v3.md), and [rendering](../workflows/render-and-export.md) for consumers of these fields.
