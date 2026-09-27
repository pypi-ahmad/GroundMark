# PP-DocLayoutV3 implementation verification

Date: 2026-09-27. Local work only; no commit or publication.

## Delivered

- Kept the explicitly approved weight source, `PaddlePaddle/PP-DocLayoutV3_onnx`, at revision `46bbdf188bb0a772c08aed74882ce7e51a8f1ea6`. Both files are checksum-verified in the ordinary user cache or an explicit offline directory.
- Replaced the previous Transformers adapter with ONNX Runtime. All three exported outputs are consumed; associated classes, confidence, original AABBs, decoded contours, and zero-based native ranks survive filtering. Gaps and ties are retained.
- Verified CUDA preparation, bounded CPU recovery after native execution failure, sticky CPU reuse, and safe Sol fallback. Invalid input and decode failures do not trigger GPU recovery. Failed CPU preparation is latched until restart.
- Replaced the eight-vertex guide cutoff with full contours when they fit and validated closed-RDP simplification when necessary. The conservative deviation bound includes rounding and cannot exceed one raster pixel. Original metadata geometry is unchanged. The 300-region and 64-KiB limits remain.
- Preserved full-page Sol image requests, both parsing profiles, preceding-page context, strict response schemas, and Python rendering. No layout toggle or fail-closed extraction was added.
- Made `run.cmd` include the layout extra. Python remains >=3.14, with dependencies recorded in `pyproject.toml` and `uv.lock`.

## Checks

| Check | Result |
| --- | --- |
| `uv run --no-sync python -m pytest tests -q --import-mode=importlib` | 361 passed |
| `uv lock --check` | Passed |
| `uv build --out-dir data/validation/v3-onnx-build` | Wheel and sdist built |
| `uv run --no-sync python scripts/verify_release_artifacts.py data/validation/v3-onnx-build` | Exact manifest and checkout bytes verified, including the new decode module and license |
| `run.cmd --version` | GroundMark 1.0.0; launcher includes the extra |
| `git diff --check` | Passed using the repository's normal Windows line-ending configuration |
| Live invoice, explicit CPU | Preparation, inference, conversion, guide projection, and runtime reuse passed |
| Live invoice, auto CUDA | Actual CUDA graph assignment, complete probe, inference, conversion, guide projection, and reuse passed |

The final live fixture produced one region, full contour guide, and native rank 142 on CPU versus 141 on CUDA. The application preserves this difference. These are operational smoke checks, not accuracy, equivalence, or performance benchmarks. ONNX Runtime emitted CPU shape-node assignment and ScatterND duplicate-index warnings.

CUDA execution failure and unsuccessful recovery were tested with injected failures; the physical GPU was not deliberately broken. No paid Sol call or real-document transcription quality evaluation was performed.

## Changed files

- Runtime and geometry: `src/layout_detector.py`, new `src/layout_polygons.py`, `src/layout_reconcile.py`.
- Metadata and integration: `src/layout.py`, `src/diagnostics.py`, `src/parse.py`, `src/cli.py`, `src/ui/app.py`.
- Prompt guide explanation: `prompts/runtime/parse-page.md`, `prompts/runtime/parse-page-structured.md`.
- Dependencies, launch, and packaging: `pyproject.toml`, `uv.lock`, `run.cmd`, `.env.example`, `scripts/verify_release_artifacts.py`, new `LICENSE-PADDLEX`. GroundMark's existing MIT license is unchanged; adapted PaddleX routines retain Apache-2.0 attribution.
- Tests: `tests/conftest.py`, `tests/fake_layout.py`, `tests/test_layout_detector.py`, `tests/test_layout_integration.py`, `tests/test_ui_diagnostics.py`, `tests/test_launcher.py`.
- Documentation: `README.md`, `docs/RUNBOOK.md`, `docs/LAYOUT-V3.md`, this report.

The pre-existing untracked [ONNX research report](PP-DocLayoutV3-ONNX-RESEARCH.md) was preserved unchanged. It describes the earlier research scope; the runtime verification above is separate.

See [runtime contracts and source references](LAYOUT-V3.md) for preprocessing, thresholds, contour decoding, cache configuration, diagnostics, and migration from an old safetensors directory.
