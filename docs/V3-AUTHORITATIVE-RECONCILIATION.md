# V3-authoritative reconciliation implementation

Implemented in the local GroundMark checkout on 2026-09-27. No commit, publication, or paid Sol request was made. Prompt 1's existing ONNX runtime work remains intact.

## Delivered behavior

- Full-precision V3 polygon versus Sol rectangle overlap, including concave polygons and disconnected intersections. Missing/unusable contours explicitly fall back to AABB evidence; valid zero-overlap contours do not.
- Deterministic greedy one-to-one assignment by IoU, center distance, then original indices. Split, merge, and many-to-many topology are review flags, not blanket rejection gates.
- Accepted pairs reference existing V3 regions for class, confidence, full contour, AABB, and native order. Sol text, tables, structures, semantic type, IDs, and transcription confidence remain unchanged.
- Unmatched Sol blocks keep their geometry and positions. Unmatched V3 regions remain detector-only metadata.
- Matched native-order sorting uses only their original occupied slots. Missing-order matches and unmatched blocks are fixed anchors; ties are stable and gaps are preserved.
- Explicit compatibility across all 25 V3 classes and both Sol profiles, without detector-driven retyping or header/footer deletion.
- New policy version `v3-authoritative-v1`; old conservative-v1/v2 artifacts remain loadable. Accepted warnings are separate from rejection reasons.
- Reconciliation defects retain the untouched Sol page, paid usage, and detector analysis, with an application-error diagnostic and partial document status. They are not reported as routine detector fallback.
- Both runtime prompts retain whole-page reading, preceding-page context, strict schemas, outside-region content, and duplicate avoidance. They explain Python's final geometry ownership.

The active configurable defaults are score >= 0.80, larger directional coverage >= 0.90, and smaller directional coverage >= 0.25. Significant coverage 0.80 supplies topology warnings only. These defaults were approved as provisional, not calibrated. The runtime detection/mask thresholds were not changed.

See [runtime and policy documentation](LAYOUT-V3.md) for the complete compatibility table, metadata contracts, and configuration.

## Changed files in this implementation

| Area | Files |
|---|---|
| Geometry, assignment, artifacts | `src/layout_reconcile.py`, `src/layout.py` |
| Contour availability at decoder boundary | `src/layout_detector.py` |
| Integration and explicit defect handling | `src/parse.py`, `src/diagnostics.py`, `src/graph.py`, `src/cli.py`, `src/ui/app.py` |
| Offline evaluator artifact/status handling | `scripts/evaluate_prompts.py` |
| Prompts | `prompts/runtime/parse-page.md`, `prompts/runtime/parse-page-structured.md` |
| Tests | `tests/test_layout_reconcile.py`, `tests/test_layout_integration.py`, `tests/test_ui_diagnostics.py` |
| Documentation | `README.md`, `docs/LAYOUT-V3.md`, `docs/RUNBOOK.md`, this report |

Other dirty files predate this implementation and belong to Prompt 1. No dependencies or lockfile entries were added for reconciliation.

## Verification

| Check | Result |
|---|---|
| `uv run --no-sync python -m pytest tests -q --import-mode=importlib` | 373 passed, 26.48 seconds |
| `uv lock --check` | Passed |
| `uv build --out-dir data/validation/v3-authoritative-build` | Wheel and source archive built |
| `uv run --no-sync python scripts/verify_release_artifacts.py data/validation/v3-authoritative-build` | Exact manifests and checkout bytes verified |
| `git diff --check` | Passed; Git emitted line-ending conversion warnings |

Tests cover content preservation, one-to-one assignment, analytic concave overlap in both windings, disconnected intersections, valid-contour no-overlap, explicit AABB fallback, prompt-geometry independence, split/merge leftovers, class compatibility, deterministic ordering, configurable eligibility, artifact tampering, old artifacts, and application-defect containment.

## Saved-response replay

Local V3 analyzed the five saved page PNGs in `data/parse/layout-comparison-20260923`. Each result was reconciled with both saved baseline and candidate Sol responses. These historical responses were not regenerated with the updated prompts.

Auto selected CUDA and completed all five pages, producing 58 detector regions. All ten response replays passed content, geometry ownership, one-to-one reference, and ordering invariants. All overlap candidates used valid full contours; no AABB fallback occurred in this sample.

The comparison below changes only smaller directional coverage from 0.25 to 0.90. It does not reproduce the old conservative algorithm.

| Saved page | Profile | Sol blocks | Provisional matches | Stricter-containment matches |
|---|---|---:|---:|---:|
| Masked Amerigroup_1, page 1 | baseline | 19 | 2 | 1 |
| Masked Amerigroup_1, page 1 | candidate | 21 | 2 | 1 |
| Masked Amerigroup_1, page 2 | baseline | 17 | 0 | 0 |
| Masked Amerigroup_1, page 2 | candidate | 9 | 1 | 1 |
| Masked_Amerigroup_RealSolutions_1, page 1 | baseline | 14 | 0 | 0 |
| Masked_Amerigroup_RealSolutions_1, page 1 | candidate | 14 | 0 | 0 |
| Masked_Amerigroup_RealSolutions_1, page 2 | baseline | 25 | 4 | 2 |
| Masked_Amerigroup_RealSolutions_1, page 2 | candidate | 26 | 1 | 1 |
| Masked_Amerigroup_RealSolutions_2, page 1 | baseline | 29 | 4 | 1 |
| Masked_Amerigroup_RealSolutions_2, page 1 | candidate | 65 | 3 | 0 |
| Total | | 239 | 17 | 7 |

One accepted provisional pair carried a topology warning. All guides fit the existing limits; CUDA guide sizes were 1,638–4,785 bytes.

A separate CPU session analyzed Masked Amerigroup_1 page 1 and replayed both saved responses: 11 regions, 2 accepted matches per response, and all invariants passed. Its guide was 2,730 bytes versus CUDA's 2,773 bytes. This difference is retained; cross-device output equivalence is not claimed.

CUDA preparation took 6.06 seconds and CPU preparation 3.31 seconds in these runs. These are operational observations, not benchmarks. ONNX Runtime warned about CPU-assigned shape nodes and ScatterND duplicate-index semantics.

## Limits and next evidence

No reviewed Sol-to-V3 correspondence labels were found. Available provider-produced text/box references do not establish which geometry assignments are correct. The replay demonstrates execution, preservation, and policy sensitivity. It does not establish matching accuracy, transcription improvement, or calibrated thresholds.

Production calibration still needs reviewed accepted/rejected pairs and unsafe partial-coverage examples, followed by held-out verification. More matches must not be interpreted as better accuracy.

Updated prompts were tested through fake Sol integration, not paid live extraction. Real CUDA execution failure was not induced; bounded recovery and sticky CPU reuse remain covered by injected runtime tests from Prompt 1. CPU replay at this stage covered one real page. The subsequent [completion report](V3-INTEGRATION-COMPLETION.md) adds five-page CPU and CUDA replay, contour annotations, and official-routine parity checks; it does not supply missing accuracy labels.
