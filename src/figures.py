"""Source figure crops. Filenames derive from page positions, never extracted text."""
from __future__ import annotations

import base64
import io
import math
from pathlib import Path

from PIL import Image

from src.annotate import _bbox_is_valid
from src.layout import ParseResult
from src.preprocess import preprocess_pages


def extract_figures(source: str | Path, result: ParseResult, output_dir: str | Path,
                    *, save_images: bool = True) -> tuple[dict[str, bytes], list[str]]:
    figures = {}
    warnings = []
    for page in result.pages:
        blocks = [(i, b) for i, b in enumerate(page.blocks) if b.type == "figure"]
        if not blocks:
            continue
        try:
            payload = preprocess_pages(source, start_page=page.page, end_page=page.page)[0]
            if payload["doc_sha256"] != result.doc_sha:
                raise ValueError("Source does not match extraction")
            with Image.open(io.BytesIO(base64.b64decode(payload["base64"]))) as image:
                for index, block in blocks:
                    if block.bbox is None or block.bbox.page != page.page or not _bbox_is_valid(block.bbox.xyxy):
                        warnings.append(f"Page {page.page}, figure {index}: invalid or missing box")
                        continue
                    x0, y0, x1, y1 = block.bbox.xyxy
                    crop = image.crop((math.floor(x0 * image.width), math.floor(y0 * image.height),
                                       math.ceil(x1 * image.width), math.ceil(y1 * image.height)))
                    buffer = io.BytesIO()
                    crop.save(buffer, format="PNG")
                    name = f"page_{page.page:03d}_figure_{index:03d}.png"
                    directory = Path(output_dir) / "images"
                    data = buffer.getvalue()
                    if save_images:
                        directory.mkdir(parents=True, exist_ok=True)
                        (directory / name).write_bytes(data)
                    figures[name] = data
        except Exception:
            # Presentation failures must not discard a successful transcription.
            warnings.append(f"Page {page.page}: figure crops unavailable")
    return figures, warnings


def load_figures(result: ParseResult, output_dir: str | Path) -> dict[str, bytes]:
    figures = {}
    for page in result.pages:
        for index, block in enumerate(page.blocks):
            if block.type != "figure":
                continue
            name = f"page_{page.page:03d}_figure_{index:03d}.png"
            try:
                data = (Path(output_dir) / "images" / name).read_bytes()
                with Image.open(io.BytesIO(data)) as image:
                    if image.format != "PNG":
                        continue
                    image.verify()
                figures[name] = data
            except (OSError, ValueError):
                continue
    return figures
