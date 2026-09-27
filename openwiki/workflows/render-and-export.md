---
type: Workflow
title: Rendering, annotations, and exports
description: How one parsed result produces safe text outputs, figure crops, and V3-aware page overlays.
tags: [rendering, export, annotations]
verified:
  - by: openwiki/0.6.0
    at: 2026-09-27T09:37:20.794Z
sources:
  - id: openwiki-source-93e604b70687ec986328477f
    resource: repo://src/annotate.py
  - id: openwiki-source-3b4939e7f8a641c2af87c413
    resource: repo://src/export.py
  - id: openwiki-source-ec589635490c6cccb15a3034
    resource: repo://src/figures.py
  - id: openwiki-source-512afa7a4c3a55c2dd8c5ac4
    resource: repo://src/markdown.py
  - id: openwiki-source-3dd86567da6844d0756a422c
    resource: repo://tests/test_markdown.py
  - id: openwiki-source-86f6d90685dff27dc6ee0d30
    resource: repo://tests/test_v3_completion.py
generated: { by: "codex", at: "2026-09-27T09:37:20.794Z" }
---

# Rendering, annotations, and exports

Python renders the validated `ParseResult`; it does not ask Sol to format Markdown or HTML. `full` retains all blocks. `clean` hides only blocks explicitly typed as running `page_header` or `page_footer` in presentation, leaving JSON and chat evidence intact. Source markup is escaped in both text formats. Detailed heading, list, and table structure is used when present, with legacy fallbacks when absent.

`export_result` selects Markdown, HTML, JSON, annotated PDF, annotated images, or Markdown ZIP. JSON can be written even when no pages succeeded. Individual rendering or annotation errors are reported without discarding other completed outputs. Figure crops require the same source hash as the parsed result and use each figure block's validated rectangular envelope; count and byte limits can omit crops with warnings.

## Annotation geometry

The annotation path validates the layout artifact and resolves matched output blocks through its block-to-region mapping. A matched block draws the full normalized V3 contour on the page PNG and raster-PDF path. If its contour is unavailable, it draws that region's V3 AABB with an explicit fallback reason. An unmatched block draws its Sol box. Unmatched detector regions appear once as distinct detector-only overlays and never become empty text blocks. Inspection metadata includes geometry choice, class, confidence, native order, device, model, and revision. Page dimensions are checked before coordinate scaling.

This differs from rectangular consumers such as figure crops: the matched block's AABB remains the compatible envelope even when its inspection overlay is a polygon. See [page artifacts](../concepts/page-artifacts.md) and [V3 ownership](../concepts/layout-v3.md).
