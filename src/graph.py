"""Defines and runs the pipeline: `preprocess -> parse -> END`.
`build_graph`/`run_graph` are the only
supported entry points for running a document through this project --
src/ui/app.py and this module's own `_main` both go through `run_graph`.

Next: src/parse.py, where the actual per-page work happens.
"""

from __future__ import annotations

import argparse
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
from src.preprocess import preprocess
from src.layout import ParseResult

# This graph only parses source pages into grounded layout data and Markdown.


class GraphState(TypedDict, total=False):
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


def node_preprocess(state: GraphState) -> dict:
    print(f"[ADE] preprocess: {state['image_path']}")
    result = preprocess(state["image_path"])
    # Preserve direct build_graph().invoke(...) callers as well as run_graph.
    run_id = state.get("run_id") or uuid4().hex
    return {
        "doc_sha": result["doc_sha256"],
        "run_id": run_id,
        "output_dir": state.get("output_dir", str(Path("data/parse/runs") / run_id)),
        "token_usage": state.get("token_usage", []),
        "model": state.get("model", DEFAULT_MODEL),
    }


def node_parse(state: GraphState) -> dict:
    # Best-effort: a parse failure is reported, not raised -- the caller can
    # still see doc_sha/status even if layout parsing didn't work.
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
        )
        filtered_pages = ", ".join(str(page) for page in result.content_filtered_pages)
        parse_error = (
            f"Pages rejected by content filter: {filtered_pages}"
            if result.content_filtered_pages
            else None
        )
        other_failures = [d for d in result.page_diagnostics if d.outcome not in ("parsed", "content_filtered")]
        if other_failures:
            summary = "; ".join(f"Page {d.page}: {d.outcome}" for d in other_failures)
            parse_error = f"{parse_error}; {summary}" if parse_error else summary
        artifacts = export_result(
            state["image_path"], result, state["output_dir"],
            formats=set(state.get("formats", DEFAULT_FORMATS)),
            view=state.get("view", "full"),
            annotation_metadata=state.get("annotation_metadata", True),
        )
        return {
            **artifacts,
            "parse_result": result,
            "parse_error": parse_error,
            "status": ("parse_failed" if not result.pages else
                       "parsed_partial" if parse_error else "parsed"),
        }
    except Exception as exc:
        print(f"[ADE] parse: skipped ({exc})")
        return {
            "parse_result": None,
            "markdown": None,
            "parse_error": str(exc),
            "annotated_pdf_path": None,
            "status": "parse_failed",
        }


def build_graph():
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
              formats: set[str] | None = None, view: str = "full") -> dict:
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
        "image_path": image_path,
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
