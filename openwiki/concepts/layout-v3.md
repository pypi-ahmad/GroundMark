---
type: Concept
title: PP-DocLayoutV3 detection and reconciliation
description: The pinned ONNX layout runtime, contour and order decode, bounded Sol guide, match ownership, and failure paths.
tags: [layout, onnx, reconciliation]
verified:
  - by: openwiki/0.6.0
    at: 2026-09-27T09:37:20.794Z
sources:
  - id: openwiki-source-342ef7511cee31b10ea0879a
    resource: repo://src/layout_detector.py
  - id: openwiki-source-f2c723d662c41481825bdaad
    resource: repo://src/layout_polygons.py
  - id: openwiki-source-02500d4cce7d8b17057d3252
    resource: repo://src/layout_reconcile.py
  - id: openwiki-source-f37e7222de1085ae56ad8a6f
    resource: repo://tests/test_layout_detector.py
  - id: openwiki-source-670417a58308fe16c6c4f8f6
    resource: repo://tests/test_layout_integration.py
  - id: openwiki-source-cba7ab9b2e6bf31e068d2235
    resource: repo://tests/test_layout_reconcile.py
generated: { by: "codex", at: "2026-09-27T09:37:20.794Z" }
---

# PP-DocLayoutV3 detection and reconciliation

GroundMark uses the pinned `PaddlePaddle/PP-DocLayoutV3_onnx` snapshot. It verifies `inference.onnx` and `inference.yml` checksums in the user cache or an explicitly configured local directory. The standalone runtime lazily loads ONNX Runtime, NumPy, and OpenCV; it does not transcribe pages.

## Runtime and decode

In `auto` mode, the runtime verifies CUDA by assigning graph nodes and executing a probe, then uses CPU if CUDA is unavailable or fails preparation. A CUDA execution failure on a real page triggers one bounded CPU preparation and page retry. Successful CPU recovery stays in use for later pages; failed recovery prevents repeated CUDA probing. Invalid input or malformed decoded output is not treated as a CUDA execution failure.

The pinned graph accepts `image`, `im_shape`, and `scale_factor`. Local preprocessing stretches RGB to 800×800, applies the official cubic resize and float normalization, and sends CHW data. The graph returns box rows, a count, and binary 200×200 masks. GroundMark filters selected rows, preserving class ID, confidence, pixel AABB, native order rank (including gaps and ties), and the associated mask. An adapted PaddleX poly-mode decoder derives a contour from each mask, with explicit AABB fallback provenance when a mask contour is unusable. The selected region is converted to normalized 0–1 geometry while retaining raw pixel geometry.

## Sol guide and matching

The V3 guide is a bounded hint to Sol, which still reads the entire image. It includes at most 300 regions and 64 KiB of JSON. A useful contour is sent in full when it fits; validated simplification or omission is recorded if necessary. The saved detector contour and local overlap calculations do not use that rounded prompt projection. An unusable guide is a layout failure, so Sol receives no partial guide.

Reconciliation uses V3 polygon-versus-Sol-box overlap when a valid contour exists, otherwise the V3 AABB. Explicit compatibility covers all 25 detector classes without rewriting Sol's semantic block type. Candidates require confidence and asymmetric coverage gates; a deterministic best-pair assignment allows each Sol block and V3 region at most one partner. Accepted split/merge topology is a review flag, not a rejection. Matched blocks take the V3 AABB and native relative order; full contours remain in the artifact for annotation. Unmatched Sol blocks keep their content and boxes; unmatched V3 regions stay detector-only, with no invented text. The default policy is provisional, not an accuracy calibration.

See [page artifacts](page-artifacts.md) for validation and [running and diagnostics](../operations/running-and-diagnostics.md) for fallback metadata.
