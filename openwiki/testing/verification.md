---
type: Testing
title: Tests and evaluation boundaries
description: Local test coverage and the separate offline replay needed to assess V3 correspondence, contours, and order.
tags: [testing, evaluation, layout]
verified:
  - by: openwiki/0.6.0
    at: 2026-09-27T09:37:20.794Z
sources:
  - id: openwiki-source-3c3ea4494f0ab77feb5c814c
    resource: repo://docs/V3-INTEGRATION-COMPLETION.md
  - id: openwiki-source-2b2997093155122683b9ef80
    resource: repo://scripts/evaluate_layout.py
  - id: openwiki-source-7ccc14b679ba3c785e22d851
    resource: repo://scripts/evaluate_reconciliation.py
  - id: openwiki-source-f37e7222de1085ae56ad8a6f
    resource: repo://tests/test_layout_detector.py
  - id: openwiki-source-670417a58308fe16c6c4f8f6
    resource: repo://tests/test_layout_integration.py
  - id: openwiki-source-cba7ab9b2e6bf31e068d2235
    resource: repo://tests/test_layout_reconcile.py
  - id: openwiki-source-86f6d90685dff27dc6ee0d30
    resource: repo://tests/test_v3_completion.py
generated: { by: "codex", at: "2026-09-27T09:37:20.794Z" }
---

# Tests and evaluation boundaries

The `tests/` suite uses fake Sol responses and injected layout backends for most behavioral checks. Run it from the checkout with `uv run python -m pytest tests`. Focused tests cover source-to-page identity, sequential context, strict schemas, partial-document behavior, GPU-to-CPU recovery, decode field associations, bounded guides, polygon overlap, one-to-one assignment, annotation overlays, CLI/UI diagnostics, and old artifact loading. These establish code invariants, not detector accuracy.

## Two different evaluations

`scripts/evaluate_layout.py` is a paid baseline-versus-detailed Sol profile comparison. Its token-F1 gate assesses text against its existing references; it does not score V3 correspondence, contour geometry, or reading order. It requires explicit `--live` and is not part of wiki generation.

`scripts/evaluate_reconciliation.py` instead replays saved Sol responses paired with the same page raster and either a saved pinned-ONNX layout artifact or an explicitly requested local V3 run. It makes no Sol calls and does no automatic threshold tuning. Inputs are SHA-256 checked, and page identity and raster dimensions must match. Each report records policy/provenance, content preservation, match counts, failures, and device information. Reviewed optional labels can score acceptable matches, order constraints, and contour overlap. Without such labels, quality measures stay unreviewed or null rather than becoming zero errors.

A real CPU or CUDA smoke run can verify runtime execution and output fields. It cannot establish that a matched region is correct, that the detector's reading order is correct, or that transcription improved. The current confidence and coverage gates are provisional; use representative reviewed flat, multicolumn, skewed, and curved pages, plus held-out examples, before calibrating them. Keep sensitive page rasters and saved model responses out of public fixtures unless cleared for release.

Read [V3 mechanics](../concepts/layout-v3.md) and [operations](../operations/running-and-diagnostics.md) alongside test failures.
