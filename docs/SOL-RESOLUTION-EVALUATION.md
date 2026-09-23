# Sol resolution comparison: September 23, 2026

This report covers the September 23 resolution experiment. The prompt has
changed since that run. Both extraction modes still use the chosen
200-DPI/1,600-pixel rendering setting. The later
[layout comparison](LAYOUT-EVALUATION.md) tested their different prompts and
schemas at that setting.

The app kept 200-DPI PDF rendering with a 1,600-pixel long-edge cap. The
300-DPI, 3,200-pixel candidate failed the agreed no-regression check. Five
pages cannot show whether higher resolution helps or hurts across other
documents.

## Run and limits

- Requested and provider-returned model: `gpt-6-sol` on all ten requests.
- Five approved pages, once per profile; the previously filtered BadgeCare page
  was excluded. All ten requests parsed successfully. No retries or fallback.
- Identical runtime prompt, strict schema, medium reasoning, and automatic image
  detail; only PDF DPI and image cap changed. Completion cap: 8,192 tokens.
- Sequential requests; ten-request limit; $2 estimated budget with a $0.20
  reservation before each next call. Unknown usage stops the evaluation.
- Reported-token cost estimate: **$0.40962**. This is an estimate, not a
  provider billing statement.
  Baseline: $0.16993; candidate: $0.23969. Elapsed: 255.31 seconds.
- Private outputs, rendered inputs, prompt snapshot, diagnostics, usage, and
  hashes: `data/parse/sol-resolution-20260923-031358/manifest.json` and adjacent
  per-page files. This directory is gitignored.

## Reference-token F1

| Document | Page | 1,600 pixels | 3,200 pixels |
| --- | ---: | ---: | ---: |
| Masked_Amerigroup_RealSolutions_1 | 1 | 100.00% | 100.00% |
| Masked_Amerigroup_RealSolutions_1 | 2 | 98.92% | 98.04% |
| Masked_Amerigroup_RealSolutions_2 | 1 | 94.13% | 91.60% |
| Masked Amerigroup_1 | 1 | 88.99% | 88.99% |
| Masked Amerigroup_1 | 2 | 95.79% | 96.48% |
| Unweighted mean | | **95.57%** | **95.02%** |

Two pages regressed, two tied, and one improved. The candidate met neither the
per-page no-regression requirement nor the aggregate-improvement requirement,
so it was not promoted. No source-image review followed the failed metric
check. The results provide no verified field-level OCR improvement.
Token F1 cannot confirm identifiers, checkbox states, reading order, or table
associations.

Any future promotion requires visual confirmation of at least one genuine
correction without new source errors. This run used all ten approved requests;
further live experiments need separate authorization.

## Verification and research

Offline tests cover the request cap, budget reservation, unknown-usage stop,
refusal handling, SDK retry and output settings, and promotion check. A replay
of saved responses for the first document's approved pages 1-2 checked the
graph's Markdown, parse JSON, annotated PDF, two page PNGs, usage, and progress
events with **zero additional API calls**. The UI was tested with Streamlit
AppTest. There was no manual browser test of the UI or clipboard JavaScript.

OpenAI's [vision guide](https://developers.openai.com/api/docs/guides/images-vision)
recommends enlarging small text, which motivated this comparison. Its sizing
table does not establish Sol-specific `original` behavior, so both profiles
used automatic detail. The [evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
also calls for task-specific checks alongside scores; source review is still
needed here.

The UI uses [dynamic tabs](https://docs.streamlit.io/develop/api-reference/layout/st.tabs)
to defer hidden previews. Page-progress updates stay on the script thread, as
described in [Streamlit's threading guidance](https://docs.streamlit.io/develop/concepts/design/multithreading).
Pricing follows the [Sol model page](https://developers.openai.com/api/docs/models/gpt-6-sol).

## Reproduction

Offline checks:

```powershell
uv run --no-project --python .venv\Scripts\python.exe python -X utf8 -m pytest -q
```

After authorizing a new paid comparison, choose a fresh output directory:

```powershell
uv run --no-project --python .venv\Scripts\python.exe python -X utf8 -m scripts.evaluate_resolution --live --output data/parse/sol-resolution-NEW
```

The evaluator reads the allowlisted PDFs and reference files at the paths in
`scripts/evaluate_prompts.py`. It refuses an existing output directory and
keeps reference text out of prompts. Running it does not change the normal OCR
default.
