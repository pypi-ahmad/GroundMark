# Prompt contract

The parsing prompt is `prompts/runtime/parse-page.md`.

The template receives the source page number, selected-range page count, raster dimensions, and preceding-page context. It asks `gpt-6-sol` to preserve visible text, reading order, headings, lists, tables, key/value lines, figures, marginalia, and bounding boxes. Document text is data, even when it looks like an instruction.

The prompt forbids summarization, correction, normalization, and business-field extraction. It requires character-by-character checking for names, addresses, dates, identifiers, codes, and long numbers. It also requires rectangular table arrays, with empty trailing cells retained. Unreadable text uses `[ILLEGIBLE]`. Previous-page context can clarify structure but cannot override the current image.

All reusable model instructions live in Markdown under `prompts/runtime/`. Python supplies document data and page metadata. Any prompt change must preserve the placeholders and pass `tests/test_prompts.py`.

`chat-answer.md` sets document-only scope, concise answers, fixed rejection decisions, and required page excerpts. `chat-verify.md` independently checks the candidate against the question and source context before approval. Both treat documents, questions, history, and candidates as untrusted data. Python keeps this data in user messages and renders only locally validated, approved statements with page references. Exact quotes establish source membership, not semantic correctness; the second model check can also fail.

Synthetic live-evaluation questions and document text live in `tests/fixtures/chat-evaluation.md`. They cover supported facts, summaries, comparisons, follow-ups, missing facts, unrelated chat, and direct, mixed, multilingual, encoded, and document-based injection attempts.
