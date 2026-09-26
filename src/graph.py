"""Defines and runs the pipeline: `preprocess -> parse -> END`.
`build_graph`/`run_graph` are the only
supported entry points for running a document through this project --
src/ui/app.py and this module's own `_main` both go through `run_graph`.

Next: src/parse.py, where the actual per-page work happens.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict
from uuid import uuid4

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from src import usage
from src.models import DEFAULT_MODEL
from src.export import DEFAULT_FORMATS, FORMATS, export_result
from src.parse import parse_document
from src.preprocess import inspect_source as preprocess
from src.layout import ParseResult
from src.diagnostics import PageDiagnostic, layout_failure_summary
from src.output_names import reserve_basename

# This graph only parses source pages into grounded layout data and Markdown.


class GraphState(TypedDict, total=False):
    """Run inputs, parser diagnostics, usage ledger, and selected artifact paths."""
    layout_initialization_failure: PageDiagnostic | None
    image_path: str
    start_page: int
    end_page: int | None
    model: str
    doc_sha: str
    parse_result: ParseResult | None
    markdown: str | None
    parse_error: str | None
    annotated_pdf_path: str | None
    status: str
    run_id: str
    output_dir: str
    token_usage: list[dict]
    parse_json_path: str | None
    markdown_path: str | None
    html_path: str | None
    annotated_page_paths: list[str]
    figure_warnings: list[str]
    detailed_layout: bool
    formats: set[str]
    view: str
    annotation_metadata: bool
    export_errors: list[str]
    output_paths: list[str]
    markdown_zip_path: str | None
    original_filename: str
    started_at: str
    output_basename: str


def node_preprocess(state: GraphState) -> dict:
    """Validate/hash the input and establish run identity and export ownership.

    Accept GraphState and return its initial metadata updates. Source validation
    and filesystem errors propagate to the graph caller.
    """
    started_at = state.get("started_at") or datetime.now(UTC).isoformat()
    print("[ADE] preprocess: validating document")
    result = preprocess(state["image_path"])
    # Preserve direct build_graph().invoke(...) callers as well as run_graph.
    run_id = state.get("run_id") or uuid4().hex
    return {
        "doc_sha": result["doc_sha256"],
        "run_id": run_id,
        "output_dir": state.get("output_dir", str(Path("data/parse/runs") / run_id)),
        "token_usage": state.get("token_usage", []),
        "model": state.get("model", DEFAULT_MODEL),
        "original_filename": state.get("original_filename", Path(state["image_path"]).name),
        "started_at": started_at,
    }


def node_parse(state: GraphState) -> dict:
    # Best-effort: a parse failure is reported, not raised -- the caller can
    # still see doc_sha/status even if layout parsing didn't work.
    """Parse selected pages and export them into GraphState updates.

    Preserve usable partial pages and paid-call usage. Unexpected exceptions
    become a fixed parse_failed message without raw document/provider text.
    """
    try:
        result = parse_document(
            state["image_path"],
            start_page=state.get("start_page", 1),
            end_page=state.get("end_page"),
            model=state.get("model", DEFAULT_MODEL),
            usage_entries=state["token_usage"],
            on_progress=get_stream_writer(),
            output_dir=state["output_dir"],
            detailed_layout=state.get("detailed_layout", False),
            save_json=False,
            layout_initialization_failure=state.get("layout_initialization_failure"),
        )
        filtered_pages = ", ".join(str(page) for page in result.content_filtered_pages)
        parse_error = (
            f"Pages rejected by content filter: {filtered_pages}"
            if result.content_filtered_pages
            else None
        )
        other_failures = [d for d in result.page_diagnostics if d.outcome not in ("parsed", "content_filtered")]
        if other_failures:
            summary = "; ".join(layout_failure_summary(d) if d.layout_stage else f"Page {d.page}: {d.outcome}"
                                for d in other_failures)
            parse_error = f"{parse_error}; {summary}" if parse_error else summary
        with reserve_basename(state["original_filename"], datetime.fromisoformat(state["started_at"]),
                              state["output_dir"]) as basename:
            artifacts = export_result(
                state["image_path"], result, state["output_dir"],
                formats=set(state.get("formats", DEFAULT_FORMATS)),
                view=state.get("view", "full"),
                annotation_metadata=state.get("annotation_metadata", True),
                output_basename=basename,
            )
        return {
            **artifacts,
            "output_basename": basename,
            "parse_result": result,
            "parse_error": parse_error,
            "status": ("parse_failed" if not result.pages else
                       "parsed_partial" if parse_error else "parsed"),
        }
    except Exception:
        message = "Unable to complete document parsing or exports. Check the input and output access."
        print(f"[ADE] parse: {message}")
        return {
            "parse_result": None,
            "markdown": None,
            "parse_error": message,
            "annotated_pdf_path": None,
            "status": "parse_failed",
        }


def build_graph():
    """Return the compiled preprocess-to-parse graph; construction makes no calls."""
    graph = StateGraph(GraphState)
    graph.add_node("preprocess", node_preprocess)
    graph.add_node("parse", node_parse)

    graph.add_edge(START, "preprocess")
    graph.add_edge("preprocess", "parse")
    graph.add_edge("parse", END)

    return graph.compile()


def run_graph(image_path: str, *, start_page: int = 1, end_page: int | None = None,
              model: str = DEFAULT_MODEL,
              detailed_layout: bool = False,
              on_progress: Callable[[dict], None] | None = None,
              output_dir: str | Path | None = None,
              formats: set[str] | None = None, view: str = "full",
              original_filename: str | None = None,
              layout_initialization_failure: PageDiagnostic | None = None) -> dict:
    """Run extraction and return final state with diagnostics and artifact paths.

    Page bounds are 1-based/inclusive. formats=None selects the UI artifact set;
    view controls presentation only. on_progress receives safe local events.
    An optional initialization diagnostic carries a UI preflight failure without
    retrying V3. Unsupported model, format, or view raises ValueError; source
    preprocessing errors may propagate. This function may make paid Sol calls.
    """
    if model != DEFAULT_MODEL:
        raise ValueError("Unsupported model")
    if formats is not None and (not formats or not formats <= FORMATS):
        raise ValueError("Unsupported output formats")
    if view not in {"full", "clean"}:
        raise ValueError("Unsupported rendering view")
    entries: list[dict] = []
    run_id = uuid4().hex
    app = build_graph()
    initial_state: GraphState = {
        "layout_initialization_failure": layout_initialization_failure,
        "image_path": image_path,
        "original_filename": original_filename or Path(image_path).name,
        "started_at": datetime.now(UTC).isoformat(),
        "start_page": start_page,
        "end_page": end_page,
        "model": model,
        "detailed_layout": detailed_layout,
        "run_id": run_id,
        "output_dir": str(output_dir if output_dir is not None else Path("data/parse/runs") / run_id),
        "formats": set(DEFAULT_FORMATS if formats is None else formats),
        "view": view,
        "annotation_metadata": formats is None,
        "token_usage": entries,
    }
    result = dict(initial_state)
    for kind, payload in app.stream(initial_state, stream_mode=["custom", "values"]):
        if kind == "values":
            result = payload
        elif on_progress:
            on_progress(payload)
    result["token_usage"] = entries
    return result


def _main() -> None:
    parser = argparse.ArgumentParser(description="Parse a document into Markdown + an annotated PDF.")
    parser.add_argument("--path", required=True, help="Path to a document image or PDF")
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--end-page", type=int, default=None, help="Omit for through the last page")
    parser.add_argument("--detailed-layout", action="store_true", help="Opt into experimental structure extraction")
    args = parser.parse_args()

    result = run_graph(args.path, start_page=args.start_page, end_page=args.end_page, detailed_layout=args.detailed_layout)

    print(f"status: {result.get('status')}")
    print(f"doc_sha: {result.get('doc_sha')}")
    if result.get("parse_error"):
        print(f"parse_error: {result['parse_error']}")
    totals = usage.totals(result.get("token_usage", []))
    print(
        f"tokens: input={totals['input_tokens']} cached={totals['cached_tokens']} "
        f"cache_write={totals['cache_write_tokens']} output={totals['output_tokens']}"
    )


if __name__ == "__main__":
    _main()
