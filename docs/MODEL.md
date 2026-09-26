# Model

Parsing uses `gpt-6-sol`. Each request contains one rasterized page image plus compact PP-DocLayoutV3 region hints and asks for text and layout data in a structured response. V3 analyzes that same image when available; failed analysis supplies empty hints and Sol still reads the full image. The image, not detector labels, supplies transcription. The parser rejects other model identifiers before preprocessing or contacting the API.

The response contains page dimensions, ordered blocks, block types, text, table cells, and optional normalized bounding boxes. Pydantic checks its shape locally. The schema has no domain records or inferred business fields.

Both extraction modes use Sol and attempt local V3 analysis. The default retains the legacy response contract. Detailed layout (experimental) asks for heading levels, list structure, table spans and headers, and running-header/footer roles. Word overlap improved in a five-page comparison before V3 integration, but source review found new errors, so this mode stays off by default. The [layout evaluation](LAYOUT-EVALUATION.md) records those historical findings, not V3-path accuracy. Schema validation checks the response structure; it cannot establish transcription accuracy.

If V3 analysis or reconciliation fails, the validated Sol blocks are retained unchanged and page diagnostics record the fallback. After response validation, local reconciliation can replace confidently matched boxes and order while preserving every Sol text, table, and structure field. Detector labels never retype blocks or decide Clean-view visibility. The strict response schemas remain unchanged; detector geometry and match evidence live in the saved artifact's separate `layout_metadata` field. See [V3 runtime and matching policy](LAYOUT-V3.md) for failure handling and the uncalibrated initial thresholds.

V3 supplies regions/order, not OCR transcription. Its process-wide runtime prepares on Parse, verifies the actual CUDA device or CPU fallback, and reuses weights across subsequent runs. UI and CLI readiness messages report that verified device. Layout summary counts are inspection aids, not quality scores; polygons remain metadata while matching and rendering use rectangles. CPU/GPU smoke tests exercise local inference only and cannot establish Sol transcription quality.

Pages run in source order. Later requests can include up to 12,000 characters from earlier successful pages to help with continued structures. The prompt tells the model to follow the current page image and avoid copying text that appears only in the context.

`src/models.py` sets these local cost estimates in USD per one million tokens. They are not provider billing rates.

| Token class | USD |
| --- | ---: |
| Input | $2.00 |
| Cached input | $0.20 |
| Cache writes | $2.50 |
| Output | $10.00 |

Automated tests use fake model responses. Checking endpoint availability and parsing quality requires separate live tests. The [layout comparison](LAYOUT-EVALUATION.md) records one limited live run and the source errors it found.

Document chat calls `gpt-6-luna` through the Responses API. It uses `reasoning={"effort":"medium"}`, strict JSON schemas, `store=False`, no tools, a 60-second timeout, and no automatic retries. The parser's `REASONING_EFFORT` override does not apply to chat. An accepted answer uses one draft call and one verification call; a rejection can take one call.

`src/models.py` estimates Luna costs at $0.10 for input, $0.01 for cached input, $0.125 for cache writes, and $0.50 for output per million tokens. Session estimates include chat and parsing calls at their respective rates. Gateway billing may differ. The UI marks usage as unknown when it is not reported.
