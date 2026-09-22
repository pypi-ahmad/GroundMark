# Data and output boundaries

The app transcribes supplied documents into layout-aware artifacts and provides document-only chat over successfully parsed pages. It does not interpret business meaning, validate arithmetic, infer missing fields, or write records to another system.

The app treats parser and chat model output as untrusted input. Pydantic checks response shapes, annotation code checks bounding-box ranges before drawing, and the local renderer escapes document text in HTML. Chat answers also require exact source excerpts and a separate verification call before display. The parsing prompt tells the model to mark unreadable text instead of guessing.

Uploaded files and generated artifacts stay on the local machine. The parser sends page images and context to the configured OpenAI-compatible endpoint. Chat sends parsed page text, the question, accepted history, and the verification candidate; it does not send original files. Operators must choose endpoint retention, access, and privacy controls that fit their documents.

Diagnostics expose model/request status and token counts without printing credentials.
