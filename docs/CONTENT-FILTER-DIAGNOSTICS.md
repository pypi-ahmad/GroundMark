# Content-filter diagnostics: September 12, 2026

The model, prompt, test count, and concurrency settings below apply to the September 12 run. The current parser records a diagnostic for each page and keeps successful pages available when another page fails or is filtered. The later [layout comparison](LAYOUT-EVALUATION.md) excluded the filtered BadgeCare page.

Five of the six approved pages parsed. BadgeCare page 1 returned
`finish_reason=content_filter`. Raw-response capture kept metadata that
automatic structured parsing had discarded. The provider still rejected the
page.

## Live evidence

The run saved `data/parse/diagnostics-20260912/manifest.json`, per-page JSON and
rendered images, and an exact prompt snapshot. Earlier runs were preserved.

| Document | Page | Outcome | HTTP | Finish reason |
| --- | --- | --- | --- | --- |
| Masked BadgeCare Plus_1 | 1 | content_filtered | 200 | content_filter |
| Masked_Amerigroup_RealSolutions_1 | 1 | parsed | 200 | stop |
| Masked_Amerigroup_RealSolutions_1 | 2 | parsed | 200 | stop |
| Masked_Amerigroup_RealSolutions_2 | 1 | parsed | 200 | stop |
| Masked Amerigroup_1 | 1 | parsed | 200 | stop |
| Masked Amerigroup_1 | 2 | parsed | 200 | stop |

The evaluator sent each listed page once, with one image per call and SDK retries
set to zero. It captured six distinct request IDs. Internal gateway retries, if
any, were not visible. Model, temperature, reasoning setting, image rendering,
and prompts were unchanged. The layout prompt matches the original baseline
byte for byte.

BadgeCare evidence:

- Request ID: `req_bd16f3fb6b954ec8a7cbbedc6bf4182f`.
- Returned model: the pre-migration default, not the current `gpt-6-sol`.
- Reported tokens: 2,701 input, 2,216 output, 0 cached.
- No recognized prompt/completion filter annotations were returned.
- No rejected completion or refusal text was saved.

The provider returned HTTP 200 with `content_filter`, rather than rejecting the request with HTTP 400. The category and underlying reason are unknown. A provider review would need the request ID and timestamp. No message was sent to the provider.

## Validation and limits

The 82 offline tests passed. They covered SDK calls against an HTTP mock,
strict-schema requests, filtered/refused/truncated/malformed output, HTTP
errors, timeout sanitization, unknown usage, retry disabling, parallel page
isolation, all-failed JSON persistence, and Streamlit diagnostics/stale-output
checks. The UI was tested with Streamlit AppTest; there was no manual browser
review.

The manifest contains GroundTruth scores. These measure reference-token overlap,
not semantic correctness. Two successful pages had ragged tables that
the display padded. The run did not show an accuracy improvement or resolve
those table structures.

## References

- [OpenAI SDK structured parsing behavior](https://github.com/openai/openai-python/blob/main/src/openai/lib/_parsing/_completions.py)
- [Differences between parse and create](https://github.com/openai/openai-python/blob/main/helpers.md#differences-from-create)
- [Azure content filtering and annotations](https://learn.microsoft.com/en-us/azure/foundry-classic/foundry-models/concepts/content-filter)

The Azure documentation describes possible metadata shapes. It does not
identify the filtering service used by this gateway.
