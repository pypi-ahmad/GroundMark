"""Loads a source document (raster image or PDF) and turns it into the
model-ready payload every downstream step consumes: a capped-size PNG,
base64-encoded, plus its `doc_sha256`. `preprocess` handles page 1 for the
graph bootstrap; `preprocess_pages` renders the selected page range.

Must not emit anything other than "image/png" or silently truncate a range.
Invalid page ranges are rejected before model calls.

Next: src/parse.py, the active caller of `preprocess_pages`.
"""

from __future__ import annotations

import base64
import hashlib
import io
from collections.abc import Iterator
from pathlib import Path

from PIL import Image

from src.config import max_image_pixels, max_pages, max_source_bytes

# Matches the resolution used for the live evaluation corpus (see "the same
# 1600-pixel page rendering" in docs/PROMPT-EVALUATION.md and docs/PROMPTS.md)
# -- changing this would make those recorded evaluation results non-reproducible
# without a new evaluation run.
MAX_LONG_EDGE = 1600
PDF_DPI = 200

_RASTER_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}


class PreprocessError(Exception):
    pass


def count_pages(path: str | Path) -> int:
    """Total page count -- 1 for a raster image, the real page count for a PDF.

    Only opens the document to read its page count; doesn't rasterize
    anything, so this is cheap enough to call right after upload to seed the
    page-range UI before the user picks a subset.
    """
    p, suffix = _validate_source(path)
    if suffix in _RASTER_EXTS:
        with Image.open(p) as image:
            _validate_dimensions(image.width, image.height)
            image.verify()
        return 1
    if suffix != ".pdf":
        raise PreprocessError(f"unsupported file type: {suffix}")

    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(p))
    try:
        return len(pdf)
    finally:
        pdf.close()


def inspect_source(path: str | Path) -> dict:
    """Validate a source without loading it and return stable metadata."""
    p, suffix = _validate_source(path)
    digest = hashlib.sha256()
    with p.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": p, "suffix": suffix, "pages": count_pages(p), "doc_sha256": digest.hexdigest()}


def preprocess(path: str | Path) -> dict:
    """Load an invoice file and return a model-ready payload.

    Always emits a PNG-encoded image (re-encoding is unavoidable once the
    long edge is capped, and PDF pages are rasterized) so downstream code
    has exactly one mime type to deal with.
    """
    result = next(iter_preprocessed_pages(path, start_page=1, end_page=1))
    result["pages"] = 1
    result.pop("page", None)
    return result


def preprocess_pages(
    path: str | Path,
    *,
    start_page: int = 1,
    end_page: int | None = None,
    max_long_edge: int = MAX_LONG_EDGE,
    pdf_dpi: int = PDF_DPI,
) -> list[dict]:
    """Like `preprocess`, but one payload per page (a raster image is just page 1).

    `start_page`/`end_page` are 1-based and inclusive; `end_page=None` means
    "through the last page". The configured selected-page limit still applies.
    A raster image has exactly one page;
    any other range is rejected. Each returned dict adds a
    "page" key -- the page's true 1-based number in the source document --
    alongside the same doc_sha256/mime/base64/width/height shape
    `preprocess` returns.
    """
    return list(iter_preprocessed_pages(path, start_page=start_page, end_page=end_page,
                                        max_long_edge=max_long_edge, pdf_dpi=pdf_dpi))


def iter_preprocessed_pages(
    path: str | Path, *, start_page: int = 1, end_page: int | None = None,
    max_long_edge: int = MAX_LONG_EDGE, pdf_dpi: int = PDF_DPI,
) -> Iterator[dict]:
    info = inspect_source(path)
    p, suffix, doc_sha256, total = info["path"], info["suffix"], info["doc_sha256"], info["pages"]
    if max_long_edge < 1 or pdf_dpi < 1:
        raise PreprocessError("Rendering dimensions must be positive")
    end = total if end_page is None else end_page
    if not 1 <= start_page <= end <= total:
        raise PreprocessError(f"Page range must be within 1..{total}")
    if end - start_page + 1 > max_pages():
        raise PreprocessError(f"Selected page range exceeds the {max_pages()} page limit")

    if suffix == ".pdf":
        images = _iter_pdf_pages(p, start_page=start_page, end_page=end, dpi=pdf_dpi,
                                 max_long_edge=max_long_edge)
    else:
        def raster():
            with Image.open(p) as source:
                _validate_dimensions(source.width, source.height)
                source.load()
                yield 1, _cap_long_edge(source.convert("RGB"), max_long_edge)
        images = raster()

    for page_number, image in images:
        try:
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            yield {
                "page": page_number,
                "doc_sha256": doc_sha256,
                "mime": "image/png",
                "base64": base64.b64encode(buf.getvalue()).decode("ascii"),
                "width": image.width,
                "height": image.height,
            }
        finally:
            image.close()


def _cap_long_edge(image: Image.Image, max_long_edge: int) -> Image.Image:
    long_edge = max(image.width, image.height)
    if long_edge <= max_long_edge:
        return image
    scale = max_long_edge / long_edge
    new_size = (round(image.width * scale), round(image.height * scale))
    return image.resize(new_size, Image.LANCZOS)


def _iter_pdf_pages(p: Path, *, start_page: int, end_page: int, dpi: int,
                    max_long_edge: int) -> Iterator[tuple[int, Image.Image]]:
    """Render pages `start_page..end_page` (1-based, inclusive) of a PDF.

    The caller validates the selected range and configured page limit before
    this internal renderer is reached.
    """
    import pypdfium2 as pdfium  # native-Windows wheel, no Poppler/Docker

    pdf = pdfium.PdfDocument(str(p))
    try:
        for n in range(start_page, end_page + 1):
            page = pdf[n - 1]
            try:
                width, height = page.get_size()
                scale = min(dpi / 72, max_long_edge / max(width, height))
                bitmap = page.render(scale=scale)
                try:
                    image = bitmap.to_pil().convert("RGB").copy()
                finally:
                    bitmap.close()
            finally:
                page.close()
            _validate_dimensions(image.width, image.height)
            yield n, image
    finally:
        pdf.close()


def _validate_source(path: str | Path) -> tuple[Path, str]:
    p = Path(path)
    if not p.is_file():
        raise PreprocessError(f"file not found: {p}")
    suffix = p.suffix.lower()
    if suffix not in _RASTER_EXTS | {".pdf"}:
        raise PreprocessError(f"unsupported file type: {suffix}")
    if p.stat().st_size > max_source_bytes():
        raise PreprocessError(f"Source exceeds the {max_source_bytes() // (1024 * 1024)} MiB limit")
    return p, suffix


def _validate_dimensions(width: int, height: int) -> None:
    if width < 1 or height < 1 or width * height > max_image_pixels():
        raise PreprocessError(f"Image exceeds the {max_image_pixels()} pixel limit")
