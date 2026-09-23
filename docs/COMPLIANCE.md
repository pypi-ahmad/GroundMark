# Data and output boundaries

The app transcribes supplied documents into layout-aware files and lets users ask questions about successfully parsed pages. It does not interpret business meaning, validate arithmetic, infer missing fields, or write records to another system.

The app treats parser and chat responses as untrusted. Pydantic validates their structure. Before drawing annotations, the code checks bounding-box ranges, and the local HTML renderer escapes document text. Chat answers need exact excerpts from parsed pages and a separate verification call before display. The parsing prompt tells the model to mark unreadable text instead of guessing.

Uploaded files and generated artifacts stay on the local machine. Model requests transmit document content to the configured OpenAI-compatible endpoint: page images and preceding-page context for parsing; parsed text, the question, accepted history, and the draft answer for chat verification. Chat can include classified headers and footers from available pages, but does not send original files. Clean and Full affect presentation only. The app makes figure crops and ZIP downloads locally from the supplied source. Operators must choose endpoint retention, access, and privacy controls that fit their documents.

Diagnostics show request status and token counts without printing credentials.

The CLI uses the same endpoint and extraction rules as the UI. It saves only selected artifacts in the requested output directory. The filenames include the source stem and extraction time, while JSON keeps the source hash for grounding. Environment variables inherited by the process take priority over `.env`. The CLI does not accept keys as command-line arguments, and release artifacts contain no keys.
