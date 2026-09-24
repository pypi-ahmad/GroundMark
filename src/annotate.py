"""Draws every parsed block's bbox onto a rasterized copy of each page and
saves the result as a multi-page annotated PDF (plus per-page PNGs and a
sidecar .meta.json) under data/annotated/ -- a human-readable check of what
the layout parser found, not a data source anything else reads back.

Must not guess a box for a block with a missing/out-of-range bbox -- skip and count
it instead (see `_bbox_is_valid`).

Next: src/markdown.py, which renders the same ParseResult as text instead of
boxes.
"""

from __future__ import annotations

import base64
import io
import json
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium

from src.preprocess import iter_preprocessed_pages
from src.layout import ParseResult
from src.output_names import artifact_name

BOX_COLOR = (220, 30, 30)
LABEL_FONT_SIZE = 16


def _bbox_is_valid(xyxy: tuple[float, float, float, float]) -> bool:
    # Coordinates are normalized 0-1 (see BBox.xyxy in src/schema.py);
    # reject anything outside that range or degenerate (zero/negative width
    # or height) instead of drawing a nonsensical box.
    x0, y0, x1, y1 = xyxy
    if not all(0.0 <= v <= 1.0 for v in xyxy):
        return False
    return x1 > x0 and y1 > y0


def annotate_document(
    source_path: str | Path,
    parse_result: ParseResult,
    *,
    output_dir: str | Path = "data/annotated",
    save_pdf: bool = True,
    save_images: bool = True,
    save_metadata: bool = True,
    output_basename: str | None = None,
) -> tuple[Path | None, Path | None]:
    """Draw every block's bbox onto a rasterized copy of each page and save a
    multi-page PDF, plus a sidecar .meta.json.

    Pillow encodes each rasterized page separately. PDFium assembles those
    encoded pages without retaining every page's decoded pixels at once.

    Blocks with a missing or out-of-range bbox are skipped and counted in the
    sidecar file.
    """
    # Annotate exactly the pages parse_result actually covers (whatever page
    # range was parsed) -- no separate range/cap needed here.
    parsed_page_numbers = sorted(
        [page.page for page in parse_result.pages] + parse_result.content_filtered_pages
        + [d.page for d in parse_result.page_diagnostics if d.page is not None]
    )
    start_page = parsed_page_numbers[0] if parsed_page_numbers else 1
    end_page = parsed_page_numbers[-1] if parsed_page_numbers else 1

    pages_payload = iter_preprocessed_pages(source_path, start_page=start_page, end_page=end_page)
    doc_sha = parse_result.doc_sha
    basename = output_basename or doc_sha
    artifact_name(basename, ".pdf")  # Validate before creating any directories.
    blocks_by_page = {page.page: page.blocks for page in parse_result.pages}

    font = ImageFont.load_default(size=LABEL_FONT_SIZE)
    annotated_paths: list[tuple[int, Path]] = []
    drawn = 0
    skipped = 0

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pages_dir = out_dir / basename
    if save_images:
        pages_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="groundmark-annotate-") as temp_name:
        temp_dir = Path(temp_name)
        for payload in pages_payload:
            with Image.open(io.BytesIO(base64.b64decode(payload["base64"]))) as decoded:
                image = decoded.convert("RGB")
            draw = ImageDraw.Draw(image)

            for block in blocks_by_page.get(payload["page"], []):
                if block.bbox is None or not _bbox_is_valid(block.bbox.xyxy):
                    skipped += 1
                    continue
                x0, y0, x1, y1 = block.bbox.xyxy
                box_px = (x0 * image.width, y0 * image.height, x1 * image.width, y1 * image.height)
                label = block.type
                draw.rectangle(box_px, outline=BOX_COLOR, width=3)
                draw.text((box_px[0], max(box_px[1] - LABEL_FONT_SIZE - 2, 0)), label,
                          fill=BOX_COLOR, font=font)
                drawn += 1

            name = f"page_{payload['page']:03d}.png"
            target = (pages_dir / (artifact_name(basename, "_" + name) if output_basename else name)
                      if save_images else temp_dir / name)
            image.save(target)
            image.close()
            annotated_paths.append((payload["page"], target))

        pdf_path = out_dir / artifact_name(basename, ".pdf")
        if save_pdf:
            with pdfium.PdfDocument.new() as document:
                for _, path in annotated_paths:
                    page_pdf = temp_dir / "page.pdf"
                    with Image.open(path) as image:
                        image.save(page_pdf, "PDF")
                    with pdfium.PdfDocument(page_pdf) as page_document:
                        document.import_pages(page_document)
                document.save(pdf_path)

    meta_path = out_dir / artifact_name(basename, ".meta.json")
    if save_metadata:
        meta_path.write_text(
            json.dumps(
                {
                    "doc_sha": doc_sha,
                    "pages": len(annotated_paths),
                    "blocks_drawn": drawn,
                    "blocks_skipped": skipped,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    return pdf_path if save_pdf else None, meta_path if save_metadata else None
