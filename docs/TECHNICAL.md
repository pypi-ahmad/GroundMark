# Technical reference

The application is a Python and Streamlit interface over a small LangGraph pipeline. `pypdfium2` renders PDF pages. Pillow handles raster images and writes annotated output. Pydantic defines the internal layout response. The pipeline saves layout JSON, while local renderers create Markdown, HTML, annotated page PNGs, and an annotated PDF.

Runtime rules:

- Parsing accepts only `gpt-6-sol`; document chat uses only `gpt-6-luna` at medium reasoning.
- Pages are parsed sequentially in source order.
- Preceding context is bounded to 12,000 characters.
- The source image is authoritative.
- Layout JSON is an internal grounding artifact, not a domain schema.
- Table rows are padded with empty trailing cells when needed so saved arrays remain rectangular.
- Missing or invalid bounding boxes are skipped rather than invented.
- Each run has an isolated artifact directory.

Production prompts live in `prompts/runtime/*.md`; no reusable model instruction is stored in Python. `src/layout.py` owns parse response types, `src/llm.py` owns parsing calls, and `src/graph.py` owns parse orchestration. `src/chat.py` owns chat schemas, two-stage answer validation, and Luna calls. Both paths read the server-side `OPENAI_API_KEY` and optional `OPENAI_BASE_URL` from the process environment.
