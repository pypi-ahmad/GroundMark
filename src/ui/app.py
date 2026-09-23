"""Document parsing and grounded chat. Model calls require explicit submission."""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import streamlit as st

from src import usage
from src import chat
from src.models import DEFAULT_MODEL
from src.graph import run_graph
from src.markdown import parse_to_html, parse_to_markdown, markdown_bundle
from src.figures import load_figures
from src.preprocess import count_pages, preprocess_pages
from src.ui.clipboard import copy_buttons

INBOX_DIR = Path("data/inbox")
st.set_page_config(page_title="ADE - Document Parsing", layout="wide")
st.title("ADE - Agentic Document Extraction")

if st.session_state.get("usage_model_version") != DEFAULT_MODEL:
    if st.session_state.get("session_token_usage"):
        st.info("Started a new Sol usage ledger. Previous model usage has not been repriced.")
    st.session_state["session_token_usage"] = []
    st.session_state["usage_model_version"] = DEFAULT_MODEL
    st.session_state.pop("last_parse_result", None)

_usage_display = st.empty()


def clear_chat():
    st.session_state["document_chat"] = []


st.session_state.setdefault("document_chat", [])


@st.cache_data(max_entries=8, show_spinner=False)
def load_input_preview(path: str, start_page: int, end_page: int) -> list[tuple[int, bytes]]:
    return [
        (page["page"], base64.b64decode(page["base64"]))
        for page in preprocess_pages(path, start_page=start_page, end_page=end_page)
    ]


def show_usage():
    entries = st.session_state.session_token_usage
    totals = usage.totals(entries)
    incomplete = any(not entry.get("usage_known", True) for entry in entries)
    label = "Reported " if incomplete else ""
    with _usage_display.container():
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric(f"{label}Input tokens (session)", f"{totals['input_tokens']:,}")
        c2.metric(f"{label}Cached input tokens", f"{totals['cached_tokens']:,}")
        c3.metric(f"{label}Cache-write tokens", f"{totals['cache_write_tokens']:,}")
        c4.metric(f"{label}Output tokens", f"{totals['output_tokens']:,}")
        c5.metric(f"{label}Session cost", f"${usage.session_cost_usd(entries):.4f}")
        if incomplete:
            st.caption("Some requests did not report usage. Totals and estimated cost exclude unknown usage.")


show_usage()
st.divider()
with st.sidebar:
    st.header("Options")
    st.caption("Model: GPT-6 Sol")
    detailed_layout = st.checkbox("Detailed layout (experimental)", value=False,
                                 help="Captures heading levels, lists, merged cells, and running headers. The five-page evaluation found new transcription errors, so this is off by default.")
    uploaded = st.file_uploader(
        "Upload a document", type=["png", "jpg", "jpeg", "webp", "tif", "tiff", "pdf"], key="uploader"
    )
    if uploaded is None:
        clear_chat()
        st.session_state.pop("last_parse_result", None)
        st.session_state.pop("upload_id", None)
        st.stop()
    raw = uploaded.getvalue()
    upload_id = hashlib.sha256(raw).hexdigest() + Path(uploaded.name).suffix.lower()
    dest = INBOX_DIR / upload_id
    if st.session_state.get("upload_id") != upload_id:
        clear_chat()
        st.session_state["upload_id"] = upload_id
        st.session_state.pop("last_parse_result", None)
        st.session_state["upload_error"] = None
        try:
            INBOX_DIR.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
            total = count_pages(dest)
            if total < 1:
                raise ValueError("Document contains no pages")
            st.session_state["detected_total_pages"] = total
            st.session_state["start_page_input"] = 1
            st.session_state["end_page_input"] = total
        except Exception:
            st.session_state["upload_error"] = "Cannot read this document. Upload a valid image or PDF."
    if st.session_state.get("upload_error"):
        st.error(st.session_state["upload_error"])
        st.stop()
    total = st.session_state["detected_total_pages"]
    st.caption(f"Detected {total} page(s) in the uploaded file.")
    start_page = st.number_input("Start page", min_value=1, step=1, key="start_page_input")
    end_page_raw = st.number_input("End page", min_value=0, step=1, key="end_page_input")
    end_page = int(end_page_raw) or total

st.caption(f"Document: {uploaded.name}")
valid_range = 1 <= start_page <= end_page <= total
scope = (upload_id, uploaded.name, int(start_page), end_page, detailed_layout)
if st.session_state.get("document_scope") != scope:
    clear_chat()
    st.session_state.pop("last_parse_result", None)
    st.session_state["document_scope"] = scope
if not valid_range:
    st.error(f"Page range must be within 1..{total}, with start no greater than end.")

if st.button("Parse", disabled=not valid_range):
    clear_chat()
    progress = st.progress(0, text="Preparing pages...")

    def update_progress(event):
        progress.progress(event["completed"] / event["total"], text=(
            f"Pages: {event['completed']}/{event['total']} completed; "
            f"{event['successful']} successful; {event['failed']} failed"
        ))

    with st.spinner("Parsing..."):
        try:
            result = run_graph(str(dest), start_page=int(start_page), end_page=end_page,
                               model=DEFAULT_MODEL, detailed_layout=detailed_layout, on_progress=update_progress,
                               original_filename=uploaded.name)
        except Exception:
            st.error("Unable to prepare this document. Check the file and page range.")
            result = None
    st.session_state["last_parse_result"] = result
    if result:
        st.session_state.session_token_usage.extend(result.get("token_usage", []))
        show_usage()

result = st.session_state.get("last_parse_result")
if result:
    status = result.get("status")
    st.subheader(f"Status: {status}")
    st.caption(f"Result model: {result.get('model', DEFAULT_MODEL)}")
    if result.get("parse_error"):
        label = "Layout parsing incomplete" if status == "parsed_partial" else "Layout parsing failed"
        st.warning(f"{label}: {result['parse_error']}")
    current_parse = result.get("parse_result")
    for warning in result.get("figure_warnings", []):
        st.caption(warning)
    if current_parse and current_parse.page_diagnostics:
        with st.expander("API diagnostics", expanded=False):
            st.json([d.model_dump(exclude_none=True) for d in current_parse.page_diagnostics])
            if any(d.outcome != "parsed" and not d.filters for d in current_parse.page_diagnostics):
                st.caption("Filter details are unavailable for one or more failed pages. The provider did not supply recognized annotations.")
else:
    current_parse = None

doc_sha = result.get("doc_sha", "document") if result else "document"
output_basename = result.get("output_basename", doc_sha) if result else doc_sha
run_id = result.get("run_id", doc_sha) if result else upload_id
view = "full"
if current_parse:
    reading_view = st.segmented_control("Document view", ["Clean", "Full"], default="Clean",
                                        key=f"{run_id}_document_view")
    view = "full" if reading_view == "Full" else "clean"
    st.caption("Clean view hides classified running page headers and footers. Unclassified content stays visible. JSON, annotations, and chat retain all content.")


@st.cache_data(max_entries=8, show_spinner=False)
def figure_assets(output_dir: str, parse_json: str, output_basename: str):
    from src.layout import ParseResult
    return load_figures(ParseResult.model_validate_json(parse_json), output_dir, output_basename=output_basename)


figures = {}
if current_parse and result.get("output_dir"):
    figures = figure_assets(result["output_dir"], current_parse.model_dump_json(), output_basename)
tab_input, tab_md, tab_pdf, tab_html, tab_json, tab_chat = st.tabs(
    ["Input preview", "Markdown", "Annotated", "HTML", "JSON", "Chat"],
    key="preview_tab", on_change="rerun",
)

if tab_input.open:
    with tab_input:
        try:
            for page_number, image_bytes in load_input_preview(str(dest), int(start_page), end_page):
                st.image(image_bytes, caption=f"Page {page_number}")
        except Exception:
            st.error("Unable to render the selected input pages.")

if tab_md.open:
    with tab_md:
        if current_parse and current_parse.pages:
            md_text = parse_to_markdown(current_parse, view=view, figures=figures, output_basename=output_basename)
            rendered_html = parse_to_html(current_parse, view=view, figures=figures, output_basename=output_basename)
            st.download_button("Download Markdown", data=md_text, file_name=f"{output_basename}.md",
                               mime="text/markdown", key=f"{run_id}_download_md", on_click="ignore")
            if figures:
                st.download_button("Download Markdown with images", data=markdown_bundle(current_parse, view=view, figures=figures, output_basename=output_basename),
                                   file_name=f"{output_basename}.zip", mime="application/zip",
                                   key=f"{run_id}_download_bundle", on_click="ignore")
            copy_buttons(data={"markdown": md_text, "html": rendered_html},
                         key=f"{run_id}_copy_md", height="content")
            markdown_view = st.segmented_control(
                "Markdown view", ["Rendered", "Raw"], default="Rendered",
                key=f"{run_id}_markdown_view",
            )
            if markdown_view == "Raw":
                st.code(md_text, language="markdown", wrap_lines=True, height=500)
            else:
                # All source text is escaped; only renderer-owned markup is enabled.
                st.markdown(parse_to_markdown(current_parse, view=view, figures=figures, output_basename=output_basename, inline_images=True),
                            unsafe_allow_html=True)
        else:
            st.info("Parse the document to create Markdown.")

if tab_pdf.open:
    with tab_pdf:
        pdf_path = result.get("annotated_pdf_path") if result else None
        if pdf_path and Path(pdf_path).is_file():
            st.download_button("Download annotated PDF", data=Path(pdf_path).read_bytes(),
                               file_name=Path(pdf_path).name, mime="application/pdf",
                               key=f"{run_id}_download_annotated", on_click="ignore")
            for page_png in result.get("annotated_page_paths", []):
                st.image(page_png, caption=Path(page_png).stem)
        else:
            st.info("Parse the document to create an annotated PDF.")

if tab_html.open:
    with tab_html:
        if current_parse:
            rendered_html = parse_to_html(current_parse, view=view, figures=figures, output_basename=output_basename)
            st.download_button("Download HTML", data=rendered_html, file_name=f"{output_basename}.html",
                               mime="text/html", key=f"{run_id}_download_html", on_click="ignore")
            st.iframe(rendered_html, height=800)
        else:
            st.info("Parse the document to create HTML.")

if tab_json.open:
    with tab_json:
        if current_parse:
            json_text = current_parse.model_dump_json(indent=2)
            st.download_button("Download JSON", data=json_text, file_name=f"{output_basename}.json",
                               mime="application/json", key=f"{run_id}_download_json", on_click="ignore")
            copy_buttons(data={"label": "Copy JSON", "text": json_text},
                         key=f"{run_id}_copy_json", height="content")
            st.json(current_parse.model_dump())
        else:
            st.info("Parse the document to create grounded layout JSON.")

if tab_chat.open:
    with tab_chat:
        pages = chat.document_pages(current_parse) if valid_range else {}
        st.caption("Chat: GPT-6 Luna · medium reasoning")
        if pages:
            st.caption("Available pages: " + ", ".join(map(str, sorted(pages))))
            missing = sorted(set(range(int(start_page), end_page + 1)) - set(pages))
            if missing:
                st.caption("Unavailable pages: " + ", ".join(map(str, missing)))
        else:
            st.info("Parse document pages before using chat.")
        if st.button("Clear chat", key="clear_document_chat"):
            clear_chat()
        for turn in st.session_state.document_chat:
            st.chat_message("user").text(turn["question"])
            st.chat_message("assistant").text(turn["answer"])
        question = st.chat_input("Ask about this document", key=f"document_question_{run_id}",
                                 max_chars=chat.MAX_QUESTION, disabled=not bool(pages),
                                 submit_mode="disable")
        # Browser widget constraints are not an authorization boundary.
        if question and pages and valid_range:
            st.chat_message("user").text(question)
            with st.spinner("Checking document evidence..."):
                reply = chat.answer_document_question(current_parse, question,
                                                       st.session_state.document_chat)
            st.session_state.session_token_usage.extend(reply.usage)
            st.session_state.document_chat.append(dict(question=question, answer=reply.answer,
                                                       status=reply.status))
            st.chat_message("assistant").text(reply.answer)
            show_usage()
