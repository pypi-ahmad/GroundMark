# Data and output boundaries

The app transcribes supplied documents into layout-aware files and lets users ask questions about successfully parsed pages. It does not interpret business meaning, validate arithmetic, infer missing fields, or write records to another system.

The app treats parser and chat responses as untrusted. Pydantic checks their shapes, annotation code checks bounding-box ranges before drawing, and the local renderer escapes document text in HTML. Chat answers need exact excerpts from parsed pages and a separate verification call before display. The parsing prompt tells the model to mark unreadable text instead of guessing.

Uploaded files and generated artifacts stay on the local machine. Model requests transmit document content to the configured OpenAI-compatible endpoint: page images and preceding-page context for parsing; parsed text, the question, accepted history, and the draft answer for chat verification. Chat can include classified headers and footers from available pages, but does not send original files. Clean and Full affect presentation only. The app makes figure crops and ZIP downloads locally from the supplied source. Operators must choose endpoint retention, access, and privacy controls that fit their documents.

Diagnostics show request status and token counts without printing credentials.

The CLI uses the same endpoint and extraction rules as the UI. It saves only selected artifacts in the requested output directory. Environment variables override configuration files; keys are not accepted as command-line arguments or included in release artifacts.
