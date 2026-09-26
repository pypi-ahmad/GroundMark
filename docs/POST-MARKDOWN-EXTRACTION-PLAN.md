# Plan: field extraction after Markdown generation

Planning date: 2026-09-23
Status: future work; implementation has not started.

## Scope agreed today

GroundMark already converts PDFs into Markdown. Keep the current implementation intact. Build the future field-extraction workflow after the existing Markdown output, as a separate downstream component.

This document records the discussion; it does not authorize implementation, deployment, paid model calls, or publication.

The intended workflow is:

```text
Incoming PDFs
    ↓
Existing GroundMark extraction: all pages → document Markdown
    ↓
New downstream component: document Markdown + permanent extraction prompt
    ↓
Structured field values → validation
    ↓
Database records and processing status
```

No manual page selection is intended for volume ingestion. The existing CLI processes all pages when page-range arguments are omitted. This does not require removing its existing page-selection options.

## Reusable extraction prompt

Maintain a separate, permanent `.md` file describing the fields to extract. Reuse it for each incoming document; do not regenerate it per PDF or change GroundMark's existing parsing prompts.

The future prompt should specify:

- Field names, descriptions, types, and output structure.
- How to handle missing, ambiguous, or conflicting values.
- Rules for dates, amounts, currencies, and repeating records where applicable.
- A requirement to use document evidence and avoid inventing missing values.

The exact fields and prompt path remain undecided. “Permanent” means reusable configuration: deliberate changes should receive a version or content hash so results can be traced to the instructions used.

## Proposed extraction behavior

Read completed Markdown and apply the reusable prompt to produce structured JSON. Validate that JSON against an explicit schema before writing accepted records to the database. A valid JSON shape alone does not prove that field values are correct.

Keep the document content separate from extraction instructions. Treat instructions embedded in documents as document content. Retain supporting excerpts or source references where the available Markdown supports them; do not invent page references.

Preserve links to the original PDF and Markdown. If existing extraction status indicates missing or failed pages, carry that status forward and apply an explicit acceptance or review policy. Markdown alone may not establish that every source page was parsed successfully.

Large documents need a defined context-limit strategy. Do not silently truncate Markdown. Whether to split documents, combine extracted records, or send oversized documents for review remains an implementation decision.

## Model direction

The current PDF-to-Markdown stage uses `gpt-6-sol`; keep it unchanged.

For the new Markdown-to-fields stage, evaluate `gpt-6-luna` first as a candidate for focused extraction at volume. Compare it with `gpt-6-sol` on representative documents and expected field values before choosing a production default. No field-extraction comparison has been run, and Luna has not been approved as the final model.

Select using field accuracy, unsupported-value rate, missing-value handling, latency, and actual provider cost. Automatic escalation to Sol is an option to evaluate, not an agreed requirement. Confirm model availability and pricing with the deployment's provider when implementation begins.

## Deployment and storage direction

Azure Databricks was the proposed deployment environment. The intended design is file arrival or scheduled discovery, processing of new documents, and storage of validated results. GroundMark has not been deployed or load-tested there.

For a Databricks deployment, the proposed storage arrangement is:

| Data | Proposed location |
| --- | --- |
| Original PDFs and generated Markdown | Azure storage exposed through Unity Catalog volumes |
| Reusable extraction prompt | A controlled, versioned file accessible to the job |
| Extracted fields and processing status | Delta tables |
| Source references and extraction provenance | Columns alongside results or related audit tables |

Delta tables were recommended for Databricks ingestion and analytics. SQLite remains an option for a small local deployment; DuckDB suits local analysis. PostgreSQL is an alternative if a separate application database is required. The user has not selected a final database or schema.

The current GroundMark package requires Python 3.14+. Verify the chosen Databricks runtime and dependency compatibility before deciding to install it directly on Databricks. If that requires changes to the existing app, keep GroundMark on a compatible external worker and let the downstream Databricks job consume its completed Markdown. Direct installation must not be assumed to work.

## Volume processing requirements for future work

- Discover completed Markdown inputs and track which documents have been handled.
- Give each document a stable identity, using its source hash where available.
- Record prompt and schema versions, model, timestamps, source paths, and processing outcome.
- Define an extraction identity that distinguishes deliberate new versions from retries.
- Use controlled concurrency and provider-aware rate limits.
- Retry transient failures with bounded attempts; keep failed and review-needed items visible.
- Validate results before database writes and make writes idempotent. For Delta, use a suitable merge key and deduplicate each input batch before `MERGE`.
- Preserve successful work so a restarted batch does not needlessly repeat paid extraction calls.
- Store credentials through deployment secret management, not in prompts, documents, logs, or source control.

Source PDF arrival and PDF-to-Markdown scheduling can be handled by an orchestration wrapper around the existing CLI. The new field extractor's input boundary is completed Markdown plus available source/status metadata. No change to the existing parser, UI, chat, exports, or CLI behavior is planned.

## Decisions needed before implementation

1. Exact fields, descriptions, output schema, and representative PDFs with expected answers.
2. Expected daily document count, page counts, document sizes, and completion-time target.
3. Databricks versus another deployment, including where existing Markdown generation runs.
4. Final database, table layout, and whether outputs serve analytics or an interactive application.
5. Acceptance thresholds, incomplete-document policy, and human review requirements.
6. Handling of repeated records, very large documents, changed prompts, and reprocessing.
7. Retention, access permissions, and approved model endpoint for document content.

## Completion criteria when implementation is authorized

An incoming PDF can pass through the unchanged GroundMark Markdown stage and the new downstream stage without page-selection interaction. The downstream stage reuses the configured prompt, produces validated fields, saves traceable records, and reports failures clearly.

Demonstrate accuracy on agreed examples, safe reruns without duplicate records, restart behavior, bounded retries, partial-document handling, and throughput at the agreed volume. These checks have not been performed.

## References from the planning discussion

- Current behavior: [Runbook](RUNBOOK.md), [Model configuration](MODEL.md), [CLI](../src/cli.py), and [Parser](../src/parse.py).
- [Databricks file arrival triggers](https://docs.databricks.com/aws/en/jobs/file-arrival-triggers).
- [Databricks Python wheel tasks](https://docs.databricks.com/aws/en/jobs/tasks/python-wheel).
- [Azure Databricks Delta MERGE](https://learn.microsoft.com/en-us/azure/databricks/delta/merge).
- [OpenAI model catalog](https://developers.openai.com/api/docs/models).

Recheck platform capabilities, runtime compatibility, model access, and pricing when implementation begins.
