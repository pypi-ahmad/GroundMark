"""Write selected artifacts from one extraction, preserving usable partial output."""

from pathlib import Path

from src.annotate import annotate_document
from src.figures import extract_figures
from src.layout import ParseResult
from src.markdown import markdown_bundle, parse_to_html, parse_to_markdown

FORMATS = frozenset({"markdown", "html", "json", "annotated-pdf", "annotated-images", "markdown-zip"})
DEFAULT_FORMATS = FORMATS - {"markdown-zip"}


def export_result(source: str, result: ParseResult, output_dir: str | Path, *,
                  formats: set[str] | frozenset[str], view: str = "full",
                  annotation_metadata: bool = False) -> dict:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "markdown": None, "markdown_path": None, "html_path": None,
        "parse_json_path": None, "markdown_zip_path": None,
        "annotated_pdf_path": None, "annotated_page_paths": [],
        "figure_warnings": [], "export_errors": [], "output_paths": [],
    }

    def write(kind, suffix, value):
        path = directory / f"{result.doc_sha}{suffix}"
        if isinstance(value, bytes):
            path.write_bytes(value)
        else:
            path.write_text(value, encoding="utf-8")
        artifacts[kind] = str(path)
        artifacts["output_paths"].append(str(path))

    if "json" in formats:
        try:
            write("parse_json_path", ".json", result.model_dump_json(indent=2))
        except Exception as exc:
            artifacts["export_errors"].append(f"JSON export failed ({type(exc).__name__})")
    if not result.pages:
        return artifacts

    figures = {}
    if formats & {"markdown", "html", "markdown-zip"}:
        figures, artifacts["figure_warnings"] = extract_figures(
            source, result, directory, save_images="markdown" in formats)
        if "markdown" in formats:
            artifacts["output_paths"].extend(str(directory / "images" / name) for name in figures)

    for name, key, suffix, render in (
        ("markdown", "markdown_path", ".md", parse_to_markdown),
        ("html", "html_path", ".html", parse_to_html),
        ("markdown-zip", "markdown_zip_path", ".zip", markdown_bundle),
    ):
        if name in formats:
            try:
                content = render(result, view=view, figures=figures)
                write(key, suffix, content)
                if name == "markdown":
                    artifacts["markdown"] = content
            except Exception as exc:
                artifacts["export_errors"].append(f"{name} export failed ({type(exc).__name__})")

    if formats & {"annotated-pdf", "annotated-images"}:
        try:
            pdf, metadata = annotate_document(
                source, result, output_dir=directory / "annotated",
                save_pdf="annotated-pdf" in formats,
                save_images="annotated-images" in formats,
                save_metadata=annotation_metadata,
            )
            if pdf:
                artifacts["annotated_pdf_path"] = str(pdf)
                artifacts["output_paths"].append(str(pdf))
            if metadata:
                artifacts["output_paths"].append(str(metadata))
            if "annotated-images" in formats:
                pages = sorted((directory / "annotated" / result.doc_sha).glob("page_*.png"))
                artifacts["annotated_page_paths"] = [str(p) for p in pages]
                artifacts["output_paths"].extend(str(p) for p in pages)
        except Exception as exc:
            artifacts["export_errors"].append(f"Annotation export failed ({type(exc).__name__})")
    return artifacts
