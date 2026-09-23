# Prompt evaluation: September 12, 2026

This report covers the September 12 prompt comparison. The app now uses `prompts/runtime/parse-page.md` by default and offers `parse-page-structured.md` as an experimental opt-in. The candidates tested here are no longer in the app. The later [layout comparison](LAYOUT-EVALUATION.md) records the current decision.

The baseline layout prompt was kept. Both revisions improved form segmentation
and reference-token overlap but introduced wrong values. The corrective version
transposed a facility tax identifier that the baseline read correctly, failing
the source-grounding acceptance check. There was no third tuning round.

Six other runtime prompts were revised during this work. That version kept
reading order and line breaks, escaped table cells, and padded ragged rows for
display. The candidates and results are stored in the ignored local artifact directory
when those files are present in the checkout.

## Live scope and controls

| Document | Pages |
| --- | --- |
| Masked BadgeCare Plus_1 | 1 |
| Masked_Amerigroup_RealSolutions_1 | 1 to 2 |
| Masked_Amerigroup_RealSolutions_2 | 1 |
| Masked Amerigroup_1 | 1 to 2 |

There were 17 page invocations: six baseline, six candidate, and five corrective.
BadgeCare page 1 was content-filtered in the first two rounds and skipped in
the corrective round. The run submitted no other pages and used no content-filter
retry, bypass, model change, or reference-text injection.

These runs used the pre-migration default model and temperature 0, so they do
not validate the current `gpt-6-sol` setup. They used the same reasoning setting
recorded in each manifest, 1600-pixel rendering, one image per request, and a
concurrency cap of 50. The code set the LangChain wrapper's retry field after
creating its SDK client. Later inspection found that the client still allowed
two transient retries; the actual number of HTTP attempts was not recorded.
The evaluator now disables retries on the SDK client itself. Documents ran
sequentially, while pages within each document ran concurrently.

## Measurements

Five pages parsed successfully and received transcription scores. The filtered
sixth page counts toward coverage but has no transcription score.

| Measurement | Baseline | Candidate | Corrective |
| --- | ---: | ---: | ---: |
| Reference token F1, mean across pages | 95.10% | 95.69% | 95.68% |
| Source value spot checks matched | 20/27 | 18/27 | 20/27 |
| Ragged extracted tables | 6 | 0 | 0 |
| Extracted table blocks | 6 | 0 | 0 |
| Invalid bounding boxes | 0 | 0 | 0 |
| Reported input tokens | 13,745 | 17,060 | 17,585 |
| Reported output tokens | 8,643 | 15,674 | 15,733 |
| Mean successful-page latency | 18.03 s | 26.49 s | 27.28 s |

Token overlap ignores punctuation, case, sequence, and field associations, so
it cannot establish extraction accuracy. The spot checks were chosen after
inspection to diagnose errors. They measure whether selected values appear,
not every field association or performance on unseen documents. Filtered
requests returned no usage, so totals include reported tokens only. Timing
comes from single runs and does not establish typical latency.

The candidates represented these form sections as fields, which explains why they produced no ragged tables. The run tells us little about repeated-row tables and has no live measure of true-grid or merged-cell accuracy. Offline tests cover renderer behavior separately.

## Source review findings

- Fax cover: both candidates retained reference text; the corrective candidate
  kept the left recipient fields before the right sender fields. The renderer now
  preserves supplied order instead of interleaving columns by top coordinate.
- Typed RealSolutions form: individual fields and checkbox groups replaced ragged
  tables. A facility identifier remained misread in all three runs.
- Handwritten RealSolutions form: the first candidate introduced new name/code
  errors. The corrective candidate recovered several but still misread other
  handwriting. One requested code improved, while several values remained unsafe
  to treat as verified.
- Amerigroup page 1: section/field separation improved, but member/referring
  identifiers remained incorrect. The corrective candidate introduced the new
  facility-identifier transposition that blocks promotion.
- Amerigroup page 2: dates and handwritten code punctuation still required review.
  The candidates also normalized a marked patient-type line instead of preserving
  its literal mark. Checkbox notation alone does not prove faithful transcription.

LandingAI uses richer table-cell structures and may describe logos or represent
forms differently. When the reference differed, the source image was checked.
The reference was not treated as automatically correct, and these results do
not support a universal accuracy claim.

## Artifacts and checks

The local artifacts are under `data/parse/prompt-eval-20260912/`:

- `comparison.html`: source images, escaped LandingAI Markdown, and all three
  extracted outputs; private document data stays in this ignored local directory.
- `summary.json`: aggregate measurements and the selected source-value checks.
- `baseline/`, `candidate/`, `corrective/`: page JSON/images/Markdown/HTML, manifests,
  and exact prompt snapshots with hashes.
- `baseline-prompts/`: original seven templates for comparison and rollback.

The six non-layout prompt revisions passed offline rendering and composition
tests. The live allowance covered only the listed medical-document pages, so
invoices were not tested. Required numeric fields in the legacy schemas could
not represent missing values; changing prompt wording did not fix that.

At the time of the evaluation, 63 offline tests passed. They covered column
ordering, table escaping, empty/ragged/multiline cells, Unicode and braces in
templates, the exact live allowlist, filtered-page skipping, and partial
failures. After rollback, the runtime layout prompt matched the baseline
snapshot byte for byte.
