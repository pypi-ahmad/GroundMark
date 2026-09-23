# Layout comparison: September 23, 2026

Detailed layout is experimental; the original prompt and schema remain the default. Both modes use the current renderer, figure crops, portable downloads, and legacy JSON loading. They share the 200-DPI/1,600-pixel rendering setting retained after the earlier [resolution comparison](SOL-RESOLUTION-EVALUATION.md).

## Results

The run processed five source pages once with each contract. Both used `gpt-6-sol`, medium reasoning, 200-DPI rendering capped at 1,600 pixels, automatic image detail, an 8,192-token completion cap, and no retries. Neither profile received text from preceding pages, so this run did not test how the app normally carries context between pages.

| Document | Page | Baseline token F1 | Candidate token F1 |
| --- | ---: | ---: | ---: |
| Masked_Amerigroup_RealSolutions_1 | 1 | 100.00% | 100.00% |
| Masked_Amerigroup_RealSolutions_1 | 2 | 99.01% | 99.01% |
| Masked_Amerigroup_RealSolutions_2 | 1 | 93.79% | 94.93% |
| Masked Amerigroup_1 | 1 | 89.32% | 89.32% |
| Masked Amerigroup_1 | 2 | 96.23% | 96.67% |
| Unweighted mean | | **95.67%** | **95.99%** |

All ten requests parsed successfully. Estimated cost was **$0.46442**, within the $2 allowance. The estimate uses repository token prices; it is not a provider bill. The run made no further live requests.

Three pages tied on token F1 and two improved, so the metric check passed. Source review found new errors. On page 2 of Masked Amerigroup_1, the candidate read the handwritten initiation-date month as 10; the source and baseline showed 6. The other handwritten form also had changed contact digits. The higher token score did not establish better field accuracy.

The candidate identified merged cells in the form table and classified running fax headers and footers. The reading view was cleaner, but the source errors kept this prompt from becoming the default. Detailed layout remains opt-in.

## Verification and limits

All **139 offline tests** passed. A replay of saved responses for the first document's two pages ran through the graph and produced Markdown, HTML, JSON, an annotated PDF, two annotated page PNGs, and one source figure crop. Rendering the saved JSON again left its bytes unchanged and reproduced the Markdown. The replay made zero additional API calls.

The offline tests cover strict schemas, legacy artifact loading, headerless and merged tables, nested lists, checkbox states, list labels, escaping, figure crops and ZIP contents, full chat evidence, and Clean/Full controls across reruns. The live responses also exposed list labels missing from list metadata. The renderer now keeps those labels and trailing notes, and uses the original text when metadata cannot represent it.

Streamlit AppTest covered the preview, copy, download, and selection paths. A browser preview was attempted, but the browser tool rejected API-key authentication (`unsupported Codex auth method: apikey`). Browser appearance and clipboard behavior were not verified. Source images were inspected directly. The comparison covers five pages in one run; it does not measure general accuracy or audit every field.

Private prompts, schemas, source hashes, responses, source images, and the shared allowance manifest are in `data/parse/layout-comparison-20260923/` (gitignored). The manifest records `promoted: false` and the failed visual review. The original prompt is retained byte-for-byte.

## Reproduction

Run offline checks through the existing environment:

```powershell
uv run --no-project --python .venv\Scripts\python.exe python -m pytest tests -q
```

The ten-request allowance is exhausted. A new live comparison needs its own allowance and output directory. `scripts.evaluate_layout` runs baseline and candidate stages under one ten-request/$2 estimated allowance. It refuses to rerun a dispatched phase, stops when usage is missing or extraction fails, and reserves estimated cost before each request. Do not dispatch more requests from an incomplete or completed run.

Before promoting detailed layout, review rendered output and confirm that dates, identifiers, and checkbox states match the source without introducing other source errors. This experiment's allowance does not cover further model calls.
