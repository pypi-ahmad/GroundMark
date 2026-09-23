# Prompt contract

The default parsing prompt is `prompts/runtime/parse-page.md`. Selecting Detailed layout (experimental), or passing the `--detailed-layout` flag, uses `parse-page-structured.md`. That prompt asks for heading levels, nested list items, table-cell header and span metadata, and running-header/footer roles. It passed the token metric check on five pages, but source review found new transcription errors, so it remains optional. Both prompts use the same template parameters and grounding rules.

Each template receives the source page number, selected-range page count, raster dimensions, and preceding-page context. It asks `gpt-6-sol` to preserve visible text, reading order, headings, lists, tables, key/value lines, figures, marginalia, and bounding boxes. Text in the document is treated as data, even when it looks like an instruction.

The prompts forbid summarizing, correcting, normalizing, or extracting business fields. They require character-by-character checks for names, addresses, dates, identifiers, codes, and long numbers. Table arrays must be rectangular, including empty trailing cells. The model uses `[ILLEGIBLE]` for unreadable text. It may use earlier pages to understand structure, but the current image decides what belongs on the page.

Reusable model instructions live in Markdown under `prompts/runtime/`. Python supplies document data and page metadata. When editing a prompt, keep its placeholders and run `tests/test_prompts.py`. Review source images for any change to extraction behavior; the [layout comparison](LAYOUT-EVALUATION.md) found value errors despite better token overlap.

The default prompt requests `LegacyParsePage`. Its response becomes the current internal page type with unknown structure metadata. The experimental prompt requests `ParsePage`. Its structure fields are required but can be null. Parsing has no separate verification pass over extracted text. Rendering and Clean/Full selection use the saved result without another request.

`chat-answer.md` limits answers to the document, defines rejection decisions, and requires short answers with page excerpts. `chat-verify.md` checks the draft against the question and source context. Both prompts treat documents, questions, history, and drafts as untrusted data. Python places that data in user messages and displays approved statements with page references after local checks. Exact quotes show that text appears in the parsed pages; they do not prove that the answer is correct. The second model check can also fail.

`tests/fixtures/chat-evaluation.md` contains synthetic documents and questions for live evaluation. Cases cover factual answers, summaries, comparisons, follow-ups, missing facts, unrelated requests, and several forms of prompt injection: direct, mixed, multilingual, encoded, and document-based.
