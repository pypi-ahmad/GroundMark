---
type: workflow
title: Artifacts and Export Lifecycle
description: How one parsed result becomes collision-safe Markdown, HTML, JSON, annotation, figure, and ZIP outputs while preserving partial work.
tags: [exports, artifacts, annotations, cli]
sources:
  - id: openwiki-source-93e604b70687ec986328477f
    resource: repo://src/annotate.py
  - id: openwiki-source-f22340a3ad65b7791573c494
    resource: repo://src/cli.py
  - id: openwiki-source-3b4939e7f8a641c2af87c413
    resource: repo://src/export.py
  - id: openwiki-source-ec589635490c6cccb15a3034
    resource: repo://src/figures.py
  - id: openwiki-source-91eeb4c49f698320d444439b
    resource: repo://src/graph.py
  - id: openwiki-source-4f6651fd216a7537d3c7ab3e
    resource: repo://src/layout.py
  - id: openwiki-source-5d1c5183da0e8a8407814ed4
    resource: repo://src/output_names.py
  - id: openwiki-source-34632138f005a3756a75f0e6
    resource: repo://src/ui/app.py
generated: { by: "codex", at: "2026-09-26T10:39:39.522Z" }
verified:
  - by: openwiki/0.6.0
    at: 2026-09-26T10:39:39.522Z
---

# Artifacts and Export Lifecycle

GroundMark parses a selected page range once and derives every requested format from the resulting `ParseResult`. These outputs use reconciled boxes/order for accepted V3 matches and retained Sol blocks for misses or V3 fallback. Export work is intentionally independent: a failed annotation or renderer is recorded without deleting artifacts that already completed.

## Run and destination ownership

Default graph calls create an isolated `data/parse/runs/<run-id>/` directory and normally request Markdown, HTML, JSON, annotated PDF, and annotated page images. The Streamlit UI instead places uploaded files and graph outputs in a session-owned temporary directory; tab changes render from the saved in-session result and do not reparse. The graph disables the parser's direct hash-named JSON write and owns the selected export set.

Terminal extraction instead uses the caller's output directory. The CLI validates the API configuration, supported input, inclusive page range, and destination before invoking the graph. The source cannot be inside the destination. A nonempty destination requires `--overwrite`, which permits new outputs but does not erase unrelated existing files. With no format flag, CLI extraction requests Markdown; selected formats all reuse the same parse.

## One collision-safe basename

Every format in a run shares a sanitized source stem plus the UTC extraction start time. Directory components and invalid Windows characters are removed, reserved device names are prefixed, stems are bounded, and empty names become `document`.

`reserve_basename` uses a temporary directory lock and checks the output root, `annotated/`, and `images/` for a case-insensitive collision across the entire artifact family. A collision adds fractional seconds. The lock coordinates concurrent writers and is removed after reservation; completed artifacts retain the chosen basename in graph state so later UI downloads and view changes stay consistent.

## Selected exports

`export_result` can independently write:

- JSON with the complete extraction, per-page diagnostics, and separate V3 layout/reconciliation metadata when available;
- Markdown plus loose figure PNGs;
- self-contained HTML with embedded figures;
- a Markdown ZIP containing its Markdown and figures;
- an annotated PDF;
- annotated page PNGs and, for graph/UI runs, annotation metadata.

JSON is attempted first and may exist even when no pages parsed. Text and annotation formats require at least one successful page. HTML-only and ZIP-only generation can keep crops in memory instead of writing loose images. The returned artifact map lists completed paths, figure warnings, and export errors separately.

## Figures and annotations

Figure crops require the current source hash, a box on the matching page, and valid normalized coordinates. Names derive from page and block position rather than model-provided text or IDs. Crop failures add warnings and leave the transcription and figure caption usable.

Annotations rerasterize exactly the covered page interval, including known failed-page positions, then draw labeled rectangles only for valid normalized boxes. Missing, degenerate, or out-of-range boxes are skipped rather than guessed; retained V3 polygons are not drawn. The optional metadata sidecar records pages and drawn/skipped counts; it is a human inspection aid, not an input to later processing.

## Partial completion and CLI status

Each renderer and the annotation stage has its own exception boundary. Completed outputs remain in place, and `output_paths` reports only successful writes. Partial page parsing likewise exports successful-page content. If every page fails, only requested JSON diagnostics can be written.

The CLI prints completed artifact paths to stdout and safe progress, diagnostics, warnings, and status to stderr. Progress includes V3 readiness's actual device and per-page timing/match counts when available, without model paths or document text. A Sol-successful V3 fallback page remains a success and does not alone trigger exit `3`. The CLI returns `0` for full success, `1` for failed extraction or runtime failure, `2` through argparse for invalid input or configuration, `3` for partial parsing or export/figure problems, and `130` for interruption.

Tests cover concurrent run isolation, filename sanitation and reservation cleanup, cross-folder collisions, selective formats, input/output safety, non-destructive overwrite behavior, retained outputs after individual export failures, partial parsing, and invalid-box annotation behavior.

See [Parsing Pipeline Architecture](../architecture/parsing-pipeline.md) for upstream state, [Layout Model and Rendering](../concepts/layout-and-rendering.md) for renderer semantics, and [V3 Layout Runtime](../concepts/v3-layout-runtime.md) for matching and fallback.
