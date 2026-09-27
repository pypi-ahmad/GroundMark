# Model

Parsing uses `gpt-6-sol`. Each request contains one rasterized page image plus compact PP-DocLayoutV3 region hints and asks for text and layout data in a structured response. V3 analyzes that same image when available; failed analysis supplies empty hints and Sol still reads the full image. The image, not detector labels, supplies transcription. The parser rejects other model identifiers before preprocessing or contacting the API.

The response contains page dimensions, ordered blocks, block types, text, table cells, and optional normalized bounding boxes. Pydantic checks its shape locally. The schema has no domain records or inferred business fields.

Both extraction modes use Sol and attempt local V3 analysis. The default retains the legacy response contract. Detailed layout (experimental) asks for heading levels, list structure, table spans and headers, and running-header/footer roles. Word overlap improved in a five-page comparison before V3 integration, but source review found new errors, so this mode stays off by default. The [layout evaluation](LAYOUT-EVALUATION.md) records those historical findings, not V3-path accuracy. Schema validation checks the response structure; it cannot establish transcription accuracy.

If V3 analysis or the guide fails, Sol receives the complete image with empty region hints and the page diagnostic records the fallback. A reconciliation invariant error retains the original Sol page and V3 analysis, records an application error, and marks the document partial. After response validation, local reconciliation applies qualified V3 AABBs, full contours, class/confidence evidence, and native relative order while preserving Sol text, tables, IDs, transcription confidence, and structure. Detector labels never retype blocks or decide Clean-view visibility. The strict response schemas remain unchanged; detector geometry and match evidence live in the saved artifact's separate `layout_metadata` field. See [V3 runtime and matching policy](LAYOUT-V3.md) for failure handling and the provisional thresholds.

V3 supplies regions/order, not OCR transcription. Its process-wide runtime prepares on Parse, verifies CUDA execution or CPU fallback, and reuses weights across subsequent runs. A native CUDA page failure gets one CPU recovery attempt and page retry; successful recovery retains CPU. UI and CLI messages report the actual device. Layout summary counts are inspection aids, not quality scores. Full contours supply matching evidence and matched annotation overlays; Markdown, HTML, and figure crops use the final blocks and their AABB envelopes. CPU/GPU smoke tests exercise local inference only and cannot establish Sol transcription quality.

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
