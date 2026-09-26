"""Active layout-parsing entry point. `parse_document` processes a page range
in source order and calls `parse_page` (V3 analysis, strict Sol transcription,
then conservative reconciliation) once per page. Direct callers
get `<output_dir>/<doc_sha>.json` by default; the graph disables that write
and owns selective exports instead. This is the only unconditionally-called
consumer of src/llm.py's model-call plumbing in the active graph (see
src/graph.py).

Page-call failures become PageDiagnostic entries so later pages can continue.
V3 failures retain validated Sol blocks; invalid images and Sol failures still
fail the page. Source preprocessing and output I/O errors can escape this
module; the graph reports those as a failed run.

Next: src/markdown.py, which renders whatever `ParseResult` this produces.
"""

from __future__ import annotations

import argparse
import base64
import io
from collections.abc import Callable
from itertools import chain
from operator import length_hint
from pathlib import Path
from time import perf_counter

from openai import ContentFilterFinishReasonError
from PIL import Image

from src.llm import _build_llm, _image_message, _invoke_structured
from src.config import max_parse_output_tokens, max_table_cells
from src.preprocess import inspect_source, iter_preprocessed_pages as preprocess_pages
from src.prompts import render_prompt
from src.models import DEFAULT_MODEL
from src.layout import (ParsePage, ParseResult, LegacyParsePage, LayoutPageArtifact,
                        NormalizedLayoutPage, ReconciliationDetails, expanded_table_cells)
from src.layout_detector import LayoutRuntime, LayoutInferenceError, get_layout_runtime
from src.layout_reconcile import LayoutConversionError, convert_layout, given_layout_json, reconcile_page, layout_match_counts
from src.diagnostics import ExtractionCallError, PageDiagnostic, layout_failure_diagnostic

# Pages are parsed in order so each call can use preceding-page context.
MAX_PARALLEL_PAGES = 1


def _layout_error(exc, *, page, stage, diagnostics=None, previous=None):
    diagnostic = layout_failure_diagnostic(exc, page=page, stage=stage,
                                           requested_model=DEFAULT_MODEL, previous=previous)
    if diagnostics is not None:
        if previous is not None and diagnostics and diagnostics[-1] is previous:
            diagnostics[-1] = diagnostic
        else:
            diagnostics.append(diagnostic)
    return ExtractionCallError(diagnostic)


def analyze_page_layout(image_b64: str, mime: str, page_number: int, width_px: int, height_px: int, *,
                        layout_runtime: LayoutRuntime | None = None,
                        diagnostics: list[PageDiagnostic] | None = None,
                        layout_metadata: list[LayoutPageArtifact] | None = None) -> tuple[NormalizedLayoutPage, str]:
    """Analyze the exact image payload, without making any transcription call."""
    stage = "initialization"
    try:
        runtime = layout_runtime if layout_runtime is not None else get_layout_runtime()
        stage = "inference"
        try:
            image_bytes = base64.b64decode(image_b64, validate=True)
            decoded = Image.open(io.BytesIO(image_bytes))
        except Exception:
            raise LayoutInferenceError("invalid_image") from None
        with decoded:
            if decoded.size != (width_px, height_px) or mime != Image.MIME.get(decoded.format):
                raise LayoutInferenceError("invalid_image")
            analysis = runtime.predict(decoded, page_number=page_number)
        stage = "conversion"
        layout = convert_layout(analysis)
        if (layout.page, layout.width_px, layout.height_px) != (page_number, width_px, height_px):
            raise LayoutConversionError("page_mismatch", page=page_number)
        if layout_metadata is not None:
            layout_metadata.append(LayoutPageArtifact(layout=layout))
        stage = "prompt"
        return layout, given_layout_json(layout)
    except Exception as exc:
        raise _layout_error(exc, page=page_number, stage=stage, diagnostics=diagnostics) from None


def reconcile_parsed_page(page: ParsePage, layout: NormalizedLayoutPage, *,
                          diagnostics: list[PageDiagnostic] | None = None,
                          previous: PageDiagnostic | None = None) -> tuple[ParsePage, LayoutPageArtifact]:
    """Return reconciled blocks and their artifact, or raise ExtractionCallError.

    This helper is strict. The active parser catches layout errors and keeps
    the validated Sol page; the evaluation runner retains its strict failure
    behavior. Optional diagnostics preserve provider metadata from previous.
    """
    try:
        reconciled = reconcile_page(page, layout)
        artifact = LayoutPageArtifact(
            layout=reconciled.metadata.layout,
            reconciliation=ReconciliationDetails.model_validate(reconciled.metadata.model_dump(exclude={"layout"})),
        )
        artifact.check_parsed_page(reconciled.page)
        return reconciled.page, artifact
    except Exception as exc:
        raise _layout_error(exc, page=page.page, stage="reconciliation",
                            diagnostics=diagnostics, previous=previous) from None


def _page_context(page: ParsePage) -> str:
    parts = []
    for block in page.blocks:
        if block.type == "table" and block.table:
            parts.extend(" | ".join(row) for row in block.table)
        elif block.text:
            parts.append(block.text)
    return "\n".join(parts)


def parse_page(
    image_b64: str, mime: str, page_number: int, width_px: int, height_px: int,
    *, diagnostics: list[PageDiagnostic] | None = None, model: str = DEFAULT_MODEL,
    usage_entries: list[dict] | None = None,
    document_context: str = "", total_pages: int = 1,
    detailed_layout: bool = False,
    layout_runtime: LayoutRuntime | None = None,
    layout_metadata: list[LayoutPageArtifact] | None = None,
    layout_initialization_failure: PageDiagnostic | None = None,
) -> ParsePage:
    """Transcribe one base64 page image and apply compatible V3 geometry.

    Page identity and pixel dimensions come from preprocessing. Detailed mode
    selects the structured Sol schema; both modes preserve Sol content. Mutable
    diagnostics, usage_entries, and layout_metadata collect call evidence.
    layout_initialization_failure carries a failed preflight so it is not
    retried. Layout failures use Sol blocks; invalid images and rejected or
    invalid Sol responses raise ExtractionCallError. No files are written.
    """
    if model != DEFAULT_MODEL:
        raise ValueError("Unsupported model")
    diagnostics = diagnostics if diagnostics is not None else []
    diagnostic_start = len(diagnostics)
    started = perf_counter()
    layout_seconds = None
    layout = None
    fallback = layout_initialization_failure
    try:
        artifact_index = len(layout_metadata) if layout_metadata is not None else 0
        given_layout = '{"regions":[]}'
        try:
            if fallback is None:
                layout, given_layout = analyze_page_layout(
                    image_b64, mime, page_number, width_px, height_px, layout_runtime=layout_runtime,
                    layout_metadata=layout_metadata,
                )
        except ExtractionCallError as exc:
            if exc.diagnostic.layout_code == "invalid_image":
                diagnostics.append(exc.diagnostic)
                raise
            fallback = exc.diagnostic
        finally:
            layout_seconds = perf_counter() - started
        try:
            text = render_prompt(
                "parse-page-structured" if detailed_layout else "parse-page", page_number=page_number, total_pages=total_pages,
                width_px=width_px, height_px=height_px, document_context=document_context, given_layout=given_layout,
            )
        except Exception as exc:
            raise _layout_error(exc, page=page_number, stage="prompt", diagnostics=diagnostics) from None
        llm = _build_llm(model=model)
        result = _invoke_structured(
            llm, ParsePage if detailed_layout else LegacyParsePage, [_image_message(text, image_b64, mime)], call_name="parse_page",
            diagnostics=diagnostics, usage_entries=usage_entries,
            max_completion_tokens=max_parse_output_tokens(),
        )
        if isinstance(result, LegacyParsePage):
            result = result.to_page()
        # Preprocessing, not the model, owns page identity and raster dimensions.
        result = result.model_copy(update={"page": page_number, "width_px": width_px, "height_px": height_px})
        if layout is not None:
            try:
                result, artifact = reconcile_parsed_page(result, layout)
                if layout_metadata is not None:
                    layout_metadata[artifact_index] = artifact
            except ExtractionCallError as exc:
                fallback = exc.diagnostic
        return result
    finally:
        if len(diagnostics) == diagnostic_start:
            diagnostics.append(PageDiagnostic(page=page_number, requested_model=model))
        # Mutate the same diagnostic carried by ExtractionCallError, retaining
        # its provider metadata even when reconciliation fails after a paid call.
        diagnostics[-1].layout_seconds = layout_seconds
        diagnostics[-1].page_seconds = perf_counter() - started
        diagnostics[-1].layout_device = layout.device if layout is not None else None
        if fallback is not None:
            diagnostics[-1].layout_fallback = True
            diagnostics[-1].layout_stage = fallback.layout_stage
            diagnostics[-1].layout_code = fallback.layout_code


def parse_document(
    path: str | Path, *, start_page: int = 1, end_page: int | None = None,
    model: str = DEFAULT_MODEL,
    usage_entries: list[dict] | None = None,
    on_progress: Callable[[dict], None] | None = None,
    output_dir: str | Path = "data/parse",
    detailed_layout: bool = False,
    save_json: bool = True,
    layout_runtime: LayoutRuntime | None = None,
    layout_initialization_failure: PageDiagnostic | None = None,
) -> ParseResult:
    """Layout-parse every page in [start_page, end_page] (1-based, inclusive;
    end_page=None means through the last page, subject to the configured cap).

    Pages are parsed sequentially. Each successful page contributes bounded
    context to the next page so headings and continued structures remain
    coherent across the document.

    Return a ParseResult containing successful pages and per-page diagnostics.
    V3 initialization failure uses Sol for the range; failed page analysis or
    reconciliation retains Sol blocks. on_progress receives safe preparation
    and source-order completion events. save_json writes doc_sha.json beneath
    output_dir. Source/range validation and output I/O errors may propagate;
    unsupported model identifiers raise ValueError before processing.
    """
    if model != DEFAULT_MODEL:
        raise ValueError("Unsupported model")
    pages_payload = iter(preprocess_pages(path, start_page=start_page, end_page=end_page))
    try:
        first_payload = next(pages_payload)
    except StopIteration as exc:
        raise ValueError("Page range contains no pages") from exc
    remaining = length_hint(pages_payload)
    if end_page is None and remaining == 0:
        total_selected = inspect_source(path)["pages"] - start_page + 1
    else:
        total_selected = remaining + 1 if end_page is None else end_page - start_page + 1
    doc_sha = first_payload["doc_sha256"]

    document_context = ""
    layout_metadata = []
    initialization_failure = layout_initialization_failure
    readiness = None
    if on_progress:
        on_progress(dict(phase="layout_preparing", completed=0, total=total_selected, successful=0, failed=0))
    try:
        if initialization_failure is None:
            layout_runtime = layout_runtime if layout_runtime is not None else get_layout_runtime()
            readiness = layout_runtime.prepare()
    except Exception as exc:
        initialization_failure = layout_failure_diagnostic(
            exc, page=first_payload["page"], stage="initialization", requested_model=model,
        )
    if on_progress and readiness is not None:
        on_progress(dict(phase="layout_ready", completed=0, total=total_selected, successful=0, failed=0,
                         device=readiness.device, fallback_reason=readiness.fallback_reason,
                         preparation_seconds=readiness.preparation_seconds, reused=readiness.reused))

    def parse_payload(payload: dict) -> tuple[ParsePage | None, PageDiagnostic]:
        diagnostics = []
        try:
            page = parse_page(
                payload["base64"],
                payload["mime"],
                payload["page"],
                payload["width"],
                payload["height"],
                diagnostics=diagnostics,
                model=model,
                usage_entries=usage_entries,
                document_context=document_context,
                total_pages=total_selected,
                detailed_layout=detailed_layout,
                layout_runtime=layout_runtime,
                layout_metadata=layout_metadata,
                layout_initialization_failure=initialization_failure,
            )
            diagnostic = diagnostics[-1] if diagnostics else PageDiagnostic(outcome="parsed")
            return page, diagnostic.model_copy(update={"page": payload["page"]})
        except ExtractionCallError as exc:
            return None, exc.diagnostic.model_copy(update={"page": payload["page"]})
        except ContentFilterFinishReasonError:
            return None, PageDiagnostic(page=payload["page"], outcome="content_filtered", requested_model=model)
        except Exception:
            diagnostic = diagnostics[-1] if diagnostics else PageDiagnostic(requested_model=model)
            return None, diagnostic.model_copy(update={"page": payload["page"], "outcome": "invalid_response"})

    outcomes = []
    successful = 0
    table_cells = 0
    selected = chain((first_payload,), pages_payload)
    for payload in selected:
        outcome = parse_payload(payload)
        if readiness is not None:
            outcome[1].layout_device = readiness.device
        if outcome[0] is not None:
            added_cells = sum(expanded_table_cells(block.table or []) for block in outcome[0].blocks)
            if table_cells + added_cells > max_table_cells():
                outcome = (None, outcome[1].model_copy(update={"outcome": "invalid_response"}))
            else:
                table_cells += added_cells
        outcomes.append(outcome)
        if outcome[0] is None and layout_metadata and layout_metadata[-1].layout.page == payload["page"]:
            layout_metadata[-1] = layout_metadata[-1].model_copy(update={"reconciliation": None})
        if outcome[0] is not None:
            successful += 1
            page_context = _page_context(outcome[0])
            document_context = (document_context + ("\n\n" if document_context else "") + page_context)[-12000:]
        if on_progress:
            artifact = layout_metadata[-1] if layout_metadata and layout_metadata[-1].layout.page == payload["page"] else None
            on_progress({"phase": "page_complete", "completed": len(outcomes), "total": total_selected,
                         "successful": successful, "failed": len(outcomes) - successful,
                         "page": payload["page"], "outcome": outcome[1].outcome,
                         "layout_fallback": outcome[1].layout_fallback,
                         "device": outcome[1].layout_device, "layout_seconds": outcome[1].layout_seconds,
                         "page_seconds": outcome[1].page_seconds, **layout_match_counts(artifact)})

    pages = [page for page, _ in outcomes if page is not None]
    content_filtered_pages = [
        diagnostic.page for _, diagnostic in outcomes if diagnostic.outcome == "content_filtered"
    ]
    result = ParseResult(
        doc_sha=doc_sha,
        extraction_profile="detailed" if detailed_layout else "legacy",
        pages=pages,
        content_filtered_pages=content_filtered_pages,
        page_diagnostics=[diagnostic for _, diagnostic in outcomes],
        layout_metadata=layout_metadata,
    )

    if save_json:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{doc_sha}.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")

    return result


def _main() -> None:
    parser = argparse.ArgumentParser(description="Parse a document's pages into layout blocks.")
    parser.add_argument("--path", required=True, help="Path to a scanned image or PDF")
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--end-page", type=int, default=None, help="Omit for through the last page")
    parser.add_argument("--detailed-layout", action="store_true", help="Experimental structure extraction; has not passed source-fidelity review")
    args = parser.parse_args()

    result = parse_document(args.path, start_page=args.start_page, end_page=args.end_page, detailed_layout=args.detailed_layout)
    print(f"doc_sha: {result.doc_sha}")
    print(f"pages parsed: {len(result.pages)}")
    print(f"written to data/parse/{result.doc_sha}.json")


if __name__ == "__main__":
    _main()
