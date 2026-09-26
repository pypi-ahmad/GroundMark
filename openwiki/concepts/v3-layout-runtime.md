---
type: concept
title: PP-DocLayoutV3 Runtime and Reconciliation
description: Official local V3 model preparation, page geometry, conservative matching, and Sol fallback.
tags: [layout, pp-doclayoutv3, inference, reconciliation]
verified:
  - by: openwiki/0.6.0
    at: 2026-09-26T10:39:39.522Z
sources:
  - id: openwiki-source-342ef7511cee31b10ea0879a
    resource: repo://src/layout_detector.py
  - id: openwiki-source-02500d4cce7d8b17057d3252
    resource: repo://src/layout_reconcile.py
  - id: openwiki-source-4f6651fd216a7537d3c7ab3e
    resource: repo://src/layout.py
  - id: openwiki-source-efa8067f082e9586439b86d3
    resource: repo://src/parse.py
generated: { by: "codex", at: "2026-09-26T10:39:39.522Z" }
---

# PP-DocLayoutV3 Runtime and Reconciliation

PP-DocLayoutV3 supplies local page regions and reading-order hints. It does not transcribe text or table cells: GPT-6 Sol still reads the complete rendered page image. GroundMark uses the same preprocessed PNG for both. V3 is an optional dependency, but its attempt is part of the normal extraction path when installed; there is no GUI extraction toggle.

## Model preparation

The runtime uses the official `PaddlePaddle/PP-DocLayoutV3_safetensors` snapshot through Hugging Face Transformers and PyTorch, pinned to a revision and SHA-256 hashes for its four required files: `config.json`, `preprocessor_config.json`, `model.safetensors`, and `inference.yml`. It checks the standard Hugging Face user cache first, downloads the pinned files on a miss, and verifies them before loading. `GROUNDMARK_LAYOUT_MODEL_DIR` may point to an existing complete, unchanged snapshot; an invalid override does not silently download elsewhere. Weights stay outside Git.

`GROUNDMARK_LAYOUT_DEVICE=auto` tries CUDA only when available, then verifies placement and a small complete prediction/postprocessing probe. If that fails, it probes CPU. `cpu` skips CUDA. Readiness reports the actual device and whether CPU fallback occurred; both-device failure raises `LayoutModelUnavailable`. A process-wide singleton and prediction lock reuse one initialized model. A later page inference failure is typed and does not trigger a second device probe or paid Sol retry. Model preparation depends on the optional `layout` package extra; base package imports do not load those native packages.

## Region data and coordinates

The official postprocessor yields `scores`, `labels`, `boxes`, `polygon_points`, and `order_seq`. GroundMark retains class ID and raw V3 label, confidence, pixel box, pixel polygon, and native zero-based order. Conversion checks finite, nondegenerate box and polygon geometry, clips to the rendered image, and divides coordinates by that image's width and height to create normalized 0–1 boxes and polygons. Polygons are retained for inspection; annotation and figure crop paths still draw/crop rectangles.

The compact `given_layout` sent to either Sol prompt contains region ID, label, normalized box, score, and order, with a polygon only when useful within the prompt budget. It guides segmentation; Sol may report visible content outside those regions. Empty regions are passed when V3 is unavailable, and the page image remains present.

## Conservative reconciliation

After strict Sol response validation, reconciliation compares boxes in normalized coordinates. Candidate evidence records IoU, both directional coverages, center distance, score, and rejection reasons. A match must be mutual best and unambiguous, have compatible role/label, and pass the current conservative coverage, score, center-distance, and margin policy. Those defaults are **initial rules, not calibrated accuracy thresholds**. Split, merge, many-to-many, weak, distant, ambiguous, and role-disagreement cases are kept for review. Only accepted one-to-one matches replace Sol boxes and reorder matched blocks by V3 order. Other Sol blocks keep their text, table rows, detailed structure, box, and stable slot; unmatched V3 regions remain layout metadata, not empty Markdown blocks.

If V3 initialization, prediction, conversion, or reconciliation fails, GroundMark records safe stage/code diagnostics and uses validated Sol blocks for that page. Invalid images and failed Sol responses still fail a page; other selected pages continue independently. Match counts and decision evidence are persisted separately from the strict Sol schemas in `ParseResult.layout_metadata`. No real-page accuracy or threshold calibration is implied by offline tests.

See [Parsing Pipeline Architecture](../architecture/parsing-pipeline.md), [Layout Model and Rendering](layout-and-rendering.md), and [Development and Testing](../operations/development-and-testing.md).
