"""Render grounded blocks without changing source data or executing source markup."""
from __future__ import annotations

import argparse
import base64
import html
import io
import re
import zipfile
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from src.layout import ParseBlock, ParseResult, TableCell, check_document_tables
from src.config import max_source_bytes, max_table_cells
from src.output_names import artifact_name, figure_name

View = Literal["full", "clean"]
Figures = dict[str, bytes]


def _blocks(result: ParseResult, view: View, output_basename=None, figures=None):
    check_document_tables(result.pages)
    if view not in {"full", "clean"}:
        raise ValueError("Unknown rendering view")
    for page in sorted(result.pages, key=lambda p: p.page):
        for index, block in enumerate(page.blocks):
            if view == "clean" and block.type in {"page_header", "page_footer"}:
                continue
            name = figure_name(page.page, index, output_basename)
            if figures and name not in figures:
                name = figure_name(page.page, index)
            yield name, block


def _cell_html(text: str) -> str:
    return html.escape(text).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _md_text(text: str) -> str:
    # Escape source syntax, but leave renderer-owned markup untouched.
    text = html.escape(text, quote=False)
    text = re.sub(r"([\\`*_{}\[\]|$])", r"\\\1", text)
    text = re.sub(r"(?m)^(\s*)([#+>-])(?=\s)", r"\1\\\2", text)
    text = re.sub(r"(?m)^(\s*)(\d+)([.)])(?=\s)", r"\1\2\\\3", text)
    text = re.sub(r"(?m)^([-=]{3,})$", lambda m: "".join("\\" + c for c in m[0]), text)
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _table_rows(rows: list[list[str]]) -> list[list[str]]:
    width = max((len(row) for row in rows), default=0)
    if len(rows) * width > max_table_cells():
        raise ValueError("Expanded table exceeds GROUNDMARK_MAX_TABLE_CELLS")
    return [row + [""] * (width - len(row)) for row in rows]


def _cells(block: ParseBlock) -> list[TableCell]:
    if block.structure and block.structure.table_cells is not None:
        return block.structure.table_cells
    # Legacy artifacts never recorded whether the first row was a header.
    return [TableCell(row=r, column=c, rowspan=1, colspan=1, is_header=False)
            for r, row in enumerate(_table_rows(block.table or [])) for c in range(len(row))]


def _render_table_html(rows: list[list[str]], cells: list[TableCell] | None = None) -> str:
    rows = _table_rows(rows)
    if not rows or not any(rows):
        return ""
    if cells is None:
        cells = [TableCell(row=r, column=c, rowspan=1, colspan=1, is_header=False)
                 for r, row in enumerate(rows) for c in range(len(row))]
    by_row: dict[int, list[TableCell]] = {}
    for cell in cells:
        by_row.setdefault(cell.row, []).append(cell)
    lines = []
    for row in range(len(rows)):
        content = []
        for cell in sorted(by_row.get(row, []), key=lambda c: c.column):
            tag = "th" if cell.is_header else "td"
            spans = (f' rowspan="{cell.rowspan}"' if cell.rowspan > 1 else "")
            spans += f' colspan="{cell.colspan}"' if cell.colspan > 1 else ""
            content.append(f"<{tag}{spans}>{_cell_html(rows[row][cell.column])}</{tag}>")
        lines.append("<tr>" + "".join(content) + "</tr>")
    return "<table><tbody>" + "".join(lines) + "</tbody></table>"


def _render_table(rows: list[list[str]]) -> str:
    """Pipe table, called only after confirming an explicit single header row."""
    if not rows or not any(rows):
        return ""
    escaped = [[_md_text(cell) for cell in row] for row in _table_rows(rows)]
    header, *body = escaped
    lines = ["| " + " | ".join(header) + " |",
             "| " + " | ".join("---" for _ in header) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(lines)


def _simple_table(block: ParseBlock) -> bool:
    return bool(block.structure and block.structure.table_cells) and all(
        c.rowspan == c.colspan == 1 and c.is_header == (c.row == 0) for c in _cells(block))


def _list_context(block: ParseBlock) -> tuple[str, str] | None:
    """Retain list labels/tails; fall back to source when metadata omits interior text."""
    cursor = 0
    label = ""
    for index, item in enumerate(block.structure.list_items):
        if not item.text.strip():
            return None
        pattern = r"\s+".join(re.escape(word) for word in item.text.split())
        match = re.search(pattern, block.text[cursor:])
        if match is None:
            return None
        prefix = block.text[cursor:cursor + match.start()].rstrip()
        if item.marker:
            if not prefix.endswith(item.marker):
                return None
            prefix = prefix[:-len(item.marker)].rstrip()
        if index == 0:
            label = prefix.strip()
        elif prefix.strip():
            return None
        cursor += match.end()
    return label, block.text[cursor:].strip()


def _list_html(block: ParseBlock) -> str:
    """Nested semantic lists; markers remain literal, including letter numbering."""
    context = _list_context(block)
    if context is None:
        return f"<p>{_cell_html(block.text)}</p>"
    label, tail = context
    parts = [f"<p>{_cell_html(label)}</p>"] if label else []
    depth = -1
    for item in block.structure.list_items:
        if item.depth > depth:
            parts.append('<ul style="list-style:none;padding-left:1.5em">')
        else:
            parts.append("</li>")
            for _ in range(depth - item.depth):
                parts.append("</ul></li>")
        marker = ("☑" if item.checked else "☐") if item.checked is not None else item.marker
        parts.append(f"<li>{html.escape(marker)} {_cell_html(item.text)}")
        depth = item.depth
    if depth >= 0:
        parts.append("</li></ul>" + "</li></ul>" * depth)
    if tail:
        parts.append(f"<p>{_cell_html(tail)}</p>")
    return "".join(parts)


def _list_markdown(block: ParseBlock) -> str:
    items = block.structure.list_items
    context = _list_context(block)
    if context is None:
        return _md_text(block.text)
    bullets = {"", "-", "*", "+", "•", "◦", "▪", "●", "○", "☐", "☑", "□", "✓", "[ ]", "[x]"}
    if any(item.checked is None and item.marker not in bullets
           and not re.fullmatch(r"\d+[.)]", item.marker) for item in items):
        return _list_html(block)
    lines = []
    for item in items:
        marker = item.marker if re.fullmatch(r"\d+[.)]", item.marker) else "-"
        if item.checked is not None:
            marker = "- [x]" if item.checked else "- [ ]"
        lines.append("    " * item.depth + marker + " " + _md_text(item.text))
    label, tail = context
    return "\n\n".join(part for part in (_md_text(label), "\n".join(lines), _md_text(tail)) if part)


def _heading_level(block: ParseBlock) -> int:
    return (block.structure.heading_level if block.structure else None) or (1 if block.type == "title" else 2)


def _render_block_html(block: ParseBlock) -> str:
    text = _cell_html(block.text)
    if block.type in {"title", "heading"}:
        level = _heading_level(block)
        return f"<h{level}>{text}</h{level}>"
    if block.type == "list" and block.structure and block.structure.list_items:
        return _list_html(block)
    if block.type == "key_value":
        key, sep, value = block.text.partition(":")
        if sep:
            return f"<p><strong>{_cell_html(key.strip())}:</strong> {_cell_html(value.strip())}</p>"
    if block.type == "table":
        return _render_table_html(block.table, _cells(block)) if block.table else f"<pre>{html.escape(block.text)}</pre>"
    if block.type == "figure":
        return f"<p><em>[figure]</em> {text}</p>"
    return f"<p>{text}</p>"


def _render_block(block: ParseBlock) -> str:
    text = _md_text(block.text)
    if block.type in {"title", "heading"}:
        return f"{'#' * _heading_level(block)} {text}".rstrip()
    if block.type == "list" and block.structure and block.structure.list_items:
        return _list_markdown(block)
    if block.type == "key_value":
        key, sep, value = block.text.partition(":")
        if sep:
            return f"**{_md_text(key.strip())}:** {_md_text(value.strip())}"
    if block.type == "table":
        if block.table and _simple_table(block):
            return _render_table(block.table)
        return _render_block_html(block)
    if block.type == "figure":
        return f"[figure] {text}".rstrip()
    return text


def parse_to_markdown(result: ParseResult, *, view: View = "full", figures: Figures | None = None,
                      inline_images: bool = False, output_basename: str | None = None) -> str:
    """Return Markdown for result in full or clean presentation view.

    figures maps filenames to PNG bytes; inline_images embeds data URLs instead
    of relative links. output_basename controls figure filenames. Source content
    is escaped, not retranscribed. Invalid view, table budget, or names may raise
    ValueError. The input result is not modified and no files are written.
    """
    parts = []
    for name, block in _blocks(result, view, output_basename, figures):
        if block.type == "figure" and figures and name in figures:
            source = "data:image/png;base64," + base64.b64encode(figures[name]).decode("ascii") if inline_images else quote(f"images/{name}", safe="/")
            rendered = f"![Figure]({source})"
            if block.text:
                rendered += "\n\n" + _md_text(block.text)
        else:
            rendered = _render_block(block)
        if rendered:
            parts.append(rendered)
    return "\n\n".join(parts) + "\n"


_HTML_STYLE = """<style>
.groundmark-document { background:#ffffff; color:#000000; font-family:Georgia,'Times New Roman',serif;
       max-width:960px; margin:auto; padding:24px; line-height:1.5; }
.groundmark-document h1 { font-size:1.6em; } .groundmark-document h2 { font-size:1.25em; }
.groundmark-document h3 { font-size:1.1em; }
.groundmark-document table { border-collapse:collapse; margin:12px 0; max-width:100%; }
.groundmark-document th,.groundmark-document td { border:1px solid #777; padding:6px 10px; text-align:left; vertical-align:top; }
.groundmark-document th { background:#eeeeee; } .groundmark-document p { margin:0.6em 0; }
.groundmark-document img { max-width:100%; height:auto; }
</style>"""


def parse_to_html(result: ParseResult, *, view: View = "full", figures: Figures | None = None,
                  output_basename: str | None = None) -> str:
    """Return self-contained escaped HTML, embedding any supplied figure bytes.

    view and output_basename follow parse_to_markdown. The page includes a
    restrictive CSP. No filesystem or model calls occur; validation errors
    from view, budgets, or names propagate.
    """
    parts = []
    for name, block in _blocks(result, view, output_basename, figures):
        if block.type == "figure" and figures and name in figures:
            image = base64.b64encode(figures[name]).decode("ascii")
            parts.append(f'<figure><img alt="Source figure" src="data:image/png;base64,{image}">'
                         f'<figcaption>{_cell_html(block.text)}</figcaption></figure>')
        else:
            parts.append(_render_block_html(block))
    csp = "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">"
    return "<!doctype html><html><head><meta charset='utf-8'>" + csp + _HTML_STYLE + "</head><body><div class='groundmark-document'>" + "\n".join(parts) + "</div></body></html>"


def markdown_bundle(result: ParseResult, *, view: View = "full", figures: Figures | None = None,
                    output_basename: str | None = None) -> bytes:
    """Return ZIP bytes containing Markdown and referenced figure PNGs.

    Use view and output_basename for the same presentation/names as the text
    renderer. Input data is not changed and no files are written.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(artifact_name(output_basename, ".md") if output_basename else "document.md",
                         parse_to_markdown(result, view=view, figures=figures, output_basename=output_basename))
        for name, block in _blocks(result, view, output_basename, figures):
            if block.type == "figure" and figures and name in figures:
                archive.writestr(f"images/{name}", figures[name])
    return buffer.getvalue()


def render_and_save(parse_json_path: str | Path) -> Path:
    """Validate saved JSON and write adjacent full-view Markdown; return its Path.

    Load matching saved figures without inference. Byte-budget, JSON/schema,
    figure-budget, and filesystem errors propagate.
    """
    path = Path(parse_json_path)
    limit = max_source_bytes()
    if path.stat().st_size > limit:
        raise ValueError("Saved JSON exceeds GROUNDMARK_MAX_SOURCE_MIB")
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Saved JSON exceeds GROUNDMARK_MAX_SOURCE_MIB")
    result = ParseResult.model_validate_json(data)
    from src.figures import load_figures
    figures = load_figures(result, path.parent, output_basename=path.stem)
    output = path.with_suffix(".md")
    output.write_text(parse_to_markdown(result, figures=figures, output_basename=path.stem), encoding="utf-8")
    return output


def save_markdown_for_doc(result: ParseResult, *, output_dir: str | Path = "data/parse",
                          figures: Figures | None = None, output_basename: str | None = None) -> Path:
    """Write full-view Markdown under output_dir and return its Path.

    Use output_basename or doc_sha; figures supplies already-loaded PNG bytes.
    Create the directory if needed. Rendering and filesystem errors propagate.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / artifact_name(output_basename or result.doc_sha, ".md")
    path.write_text(parse_to_markdown(result, figures=figures, output_basename=output_basename), encoding="utf-8")
    return path


def save_html_for_doc(result: ParseResult, *, output_dir: str | Path = "data/parse",
                     figures: Figures | None = None, output_basename: str | None = None) -> Path:
    """Write full-view embedded-image HTML under output_dir; return its Path.

    Use output_basename or doc_sha and optional PNG bytes in figures. Rendering
    and filesystem errors propagate.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / artifact_name(output_basename or result.doc_sha, ".html")
    path.write_text(parse_to_html(result, figures=figures, output_basename=output_basename), encoding="utf-8")
    return path


def _main() -> None:
    parser = argparse.ArgumentParser(description="Render grounded JSON as Markdown.")
    parser.add_argument("--parse", required=True)
    print(f"written to {render_and_save(parser.parse_args().parse)}")


if __name__ == "__main__":
    _main()
