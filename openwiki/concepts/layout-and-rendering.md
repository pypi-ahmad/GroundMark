---
type: concept
title: Layout Model and Rendering
description: Sol block schemas, separately validated V3 evidence, conservative reconciliation, and loss-aware rendering.
tags: [layout, reconciliation, rendering, markdown, html]
sources:
  - id: openwiki-source-93e604b70687ec986328477f
    resource: repo://src/annotate.py
  - id: openwiki-source-ec589635490c6cccb15a3034
    resource: repo://src/figures.py
  - id: openwiki-source-02500d4cce7d8b17057d3252
    resource: repo://src/layout_reconcile.py
  - id: openwiki-source-4f6651fd216a7537d3c7ab3e
    resource: repo://src/layout.py
  - id: openwiki-source-512afa7a4c3a55c2dd8c5ac4
    resource: repo://src/markdown.py
  - id: openwiki-source-22823fdb2e93c5de789260d7
    resource: repo://tests/test_layout_structure.py
generated: { by: "codex", at: "2026-09-26T10:39:39.522Z" }
verified:
  - by: openwiki/0.6.0
    at: 2026-09-26T10:39:39.522Z
---

# Layout Model and Rendering

GroundMark separates extraction data from presentation. The parser produces a validated `ParseResult`; Markdown, HTML, annotations, JSON, figures, and chat all consume that result without changing it. These models describe document layout and grounding, not business fields.

## Stable internal contract

A result records the document SHA, schema version, extraction profile, model, successful pages, content-filtered page numbers, page diagnostics, and separately validated `layout_metadata`. Each page has authoritative pixel dimensions and an ordered list of Sol-derived blocks. Blocks carry an ID, semantic type, source text, optional normalized bounding box, optional confidence, optional table rows, and nullable structure metadata. V3 metadata retains its original labels, scores, pixel boxes, polygons, normalized boxes, order, and reconciliation evidence without adding fields to either strict model-facing Sol schema.

Saved JSON is currently schema version 2. When an older artifact has no version, loading adds missing `structure: null` values in memory without rewriting or mutating the input object; absent `layout_metadata` defaults to an empty list. Legacy live extraction uses a smaller strict schema and is explicitly converted to the current page type. Detailed extraction adds heading levels, list items, and table-cell structure while leaving downstream consumers on the same result type.

## Structural invariants

Model-facing schemas forbid extra properties and require every property; unavailable values are nullable instead of omitted. `BBox` itself checks that `xyxy` has exactly four values; it does not alone prove finite, in-range, nondegenerate geometry. V3 conversion validates and clips geometry before normalizing pixels to 0–1, while reconciliation, annotation, and figure cropping reject ineligible boxes. Polygons remain metadata: current annotation and crop paths use rectangles, not polygon drawing. Ragged table rows are padded with trailing empty cells so later consumers receive a rectangle without changing existing cell text.

Detailed metadata is accepted only when internally consistent:

- heading levels range from 1 through 6 and belong only to title or heading blocks;
- list nesting starts at depth zero and can increase only one level at a time;
- table metadata belongs to a nonempty table and must cover every cell exactly once;
- merged cells must remain within bounds, cannot overlap, and may cover only empty continuation cells.

Invalid structure is rejected during model validation rather than repaired speculatively.

## Rendering views and order

Both renderers traverse pages by page number and blocks in the reconciled order. A confident one-to-one V3 match can replace a block's box and order matched blocks by V3 reading order. Unmatched, weak, ambiguous, split/merge, or role-disagreeing Sol blocks retain their text, table, structure, box, and original positional slot; unmatched V3 regions remain metadata rather than empty rendered blocks. Match decisions and candidate evidence are inspectable, and initial thresholds are policy, not calibrated accuracy claims. `full` includes every block. `clean` omits only blocks explicitly classified as `page_header` or `page_footer`; detector labels alone do not reclassify Sol blocks or hide content. Default legacy extraction cannot assign those running-furniture roles, so its Clean and Full output is normally identical.

Rendering is presentation-only. Source HTML and Markdown syntax is escaped, line breaks are preserved, and output generation leaves the serialized extraction unchanged. Headings use detailed levels when available and conservative defaults otherwise. Key-value blocks split only on the first colon.

## Tables and lists

A table becomes a Markdown pipe table only when detailed metadata identifies an unmerged first row as the complete header row. Merged or headerless tables use HTML so spans and data-row semantics are preserved. Legacy tables are treated as headerless because older artifacts did not record header identity. Missing table rows fall back to escaped preformatted source text.

Structured lists are rendered only when the item metadata can be reconciled with the original block text. GroundMark retains surrounding labels and trailing notes, preserves nesting and checkbox state, and falls back to escaped source text if metadata omits or conflicts with source content. Unusual literal markers can use HTML rather than being silently rewritten as Markdown bullets.

## Figures

Figure blocks with valid boxes can be cropped from a source whose SHA matches the result. Crop names derive from page and block position, not model-controlled block IDs. Markdown links to the crop, HTML embeds PNG bytes, and the Markdown bundle includes both. A missing or invalid box produces a warning and leaves the figure caption as a placeholder; it does not discard the rest of the extraction. Existing crops are loaded only after PNG verification.

Focused tests cover schema compatibility, invalid merged-cell and list metadata, Clean/Full behavior, executable-markup escaping, source-preserving list fallbacks, headerless tables, renderer immutability, reading order, figure crop safety, and bundle contents.

See [Parsing Pipeline Architecture](../architecture/parsing-pipeline.md) for how the result is populated, [V3 Layout Runtime](v3-layout-runtime.md) for model preparation, and [Artifacts and Export Lifecycle](../workflows/artifacts-and-exports.md) for persistence and downloads.
