---
type: operations
title: Development, Testing, and Evaluation
description: Local setup, packaging, deterministic verification, and the separately authorized live-evaluation harnesses used to maintain GroundMark.
tags: [development, testing, evaluation, packaging]
verified:
  - by: openwiki/0.5.2
    at: 2026-09-23T13:34:05.703Z
sources:
  - id: openwiki-source-000a7add03cfbd0ac1794f3a
    resource: repo://docs/CONTRIBUTING.md
  - id: openwiki-source-51639ec4f9dc3fb84f820c05
    resource: repo://docs/RUNBOOK.md
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
  - id: openwiki-source-63d74031dec3928bfcebce90
    resource: repo://scripts/evaluate_chat.py
  - id: openwiki-source-2b2997093155122683b9ef80
    resource: repo://scripts/evaluate_layout.py
  - id: openwiki-source-905047852ec56afcea78b7b1
    resource: repo://scripts/evaluate_prompts.py
  - id: openwiki-source-74a5e39a1c60ae438602c309
    resource: repo://scripts/evaluate_resolution.py
generated: { by: "codex", at: "2026-09-23T13:34:05.703Z" }
---

# Development, Testing, and Evaluation

GroundMark is a Python 3.14+ project managed with uv. `pyproject.toml` defines the application and its `groundmark` console entry point; `uv.lock` is the reproducible checkout environment. The normal local loop is:

```powershell
uv sync
uv run python -m pytest tests
git diff --check
```

The explicit `tests` path prevents archived artifacts under local data directories from being collected. Unit and integration tests replace model calls with fakes, so the normal suite requires no paid API access. Focused suites cover preprocessing, strict schemas, sequential parsing, diagnostics, renderers, annotations, exports, CLI validation, Streamlit state, chat guardrails, usage, and evaluation-harness limits.

## Runtime prompts and packaging

Authored model instructions live in `prompts/runtime/*.md`; Python loads and substitutes data into them rather than embedding policy prose in application code. Hatchling packages `src` and force-includes those four Markdown resources under `src/_runtime_prompts`, allowing installed wheels to resolve prompts outside the checkout.

Build release artifacts with `uv build`. The wheel contains runtime code, prompt resources, and the license. Tests, evaluation scripts, private documents, credentials, and generated diagrams are not release payloads. Releases are distributed through GitHub because the similarly named PyPI project is unrelated. Packaging or CLI changes should also be exercised from an installed wheel outside the checkout.

## Offline verification versus live evaluation

The test suite is deterministic and safe to run routinely. The scripts under `scripts/evaluate_*.py` are different: they send real requests, write manifests, and require configured credentials and explicit invocation. A recorded evaluation document is historical evidence, not proof that the current checkout was rerun.

The live harnesses impose mechanical bounds:

- prompt evaluation requires `--live`, uses an allowlisted six-page corpus, snapshots prompts, and can skip pages previously content-filtered;
- resolution comparison uses five approved pages, at most ten calls, a USD 2 estimate ceiling with per-request reserve, and stops on unknown usage;
- layout comparison runs baseline before candidate against unchanged source hashes, shares the ten-call/USD 2 allowance, and leaves visual review pending even after its metric gate;
- chat evaluation uses synthetic parsed text and exits nonzero when any case fails, but passing does not establish complete prompt-injection protection.

Resolution promotion requires every candidate page to match or exceed its baseline token F1 and the aggregate improvement to be positive. Layout's metric gate requires all five candidate pages to meet their baseline; source review remains necessary because token overlap does not detect every transcription error. Rejected pages are not retried under another resolution profile.

## Operational discipline

Keep model calls centralized, source pages sequential, older JSON loadable, and presentation filters separate from stored extraction and chat evidence. Add or update focused tests for behavior changes, then run the complete deterministic suite. Never commit API credentials, uploaded documents, local indexes, or generated run artifacts.

For runtime troubleshooting, confirm the API key is present without printing it, remember that the endpoint must support Sol parsing and Luna chat, inspect per-page diagnostics after partial runs, and select a smaller page range when sequential processing or chat context is too large.

See [GroundMark Quickstart](../quickstart.md) for use, [Parsing Pipeline Architecture](../architecture/parsing-pipeline.md) for the runtime graph, and [Grounded Document Chat](../features/document-chat.md) for its verification contract.
