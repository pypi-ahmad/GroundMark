# Model

Parsing uses `gpt-6-sol` only. Each parse request contains one rasterized page image and asks for structured text and layout data. Parser entry points reject every other model identifier before preprocessing or API access.

The internal response contains page dimensions, ordered blocks, block types, text, table cells, and optional normalized bounding boxes. Pydantic validates the response shape locally. The response has no domain record or inferred business fields.

Pages run sequentially. Later pages can receive up to 12,000 characters from earlier successful pages to help preserve continued structure. The page image remains authoritative, and the prompt forbids copying context text that is absent from the image.

The configured rates below come from the official [GPT-6 Sol documentation](https://developers.openai.com/api/docs/models/gpt-6-sol). Prices are per one million text tokens.

| Token class | USD |
| --- | ---: |
| Input | $2.00 |
| Cached input | $0.20 |
| Cache writes | $2.50 |
| Output | $10.00 |

The automated tests use fake model responses, so they do not verify live endpoint availability or parsing quality.

Document chat uses `gpt-6-luna` through the Responses API with `reasoning={"effort":"medium"}`, strict JSON schemas, `store=False`, no tools, a 60-second request timeout, and no automatic retries. Chat does not use the parser's `REASONING_EFFORT` override. An accepted answer takes two calls: a draft and a separate verification. A rejection can take one call.

The official [Luna model documentation](https://developers.openai.com/api/docs/models/gpt-6-luna) lists rates per million tokens of $0.10 input, $0.01 cached input, $0.125 cache writes, and $0.50 output. Session accounting includes both chat calls and parser calls using their own model rates. These are standard-processing estimates, not gateway billing records. Unknown usage remains visibly marked.
