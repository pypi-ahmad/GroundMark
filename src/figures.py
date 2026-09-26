"""Source figure crops. Filenames derive from page positions, never extracted text."""
from __future__ import annotations

import base64
import io
import math
from pathlib import Path

from PIL import Image

from src.annotate import _bbox_is_valid
from src.config import max_figure_bytes, max_figures, max_image_pixels
from src.layout import ParseResult
from src.output_names import figure_name
from src.preprocess import preprocess_pages


def extract_figures(source: str | Path, result: ParseResult, output_dir: str | Path,
                    *, save_images: bool = True, output_basename: str | None = None) -> tuple[dict[str, bytes], list[str]]:
    """Return PNG bytes by figure filename and safe crop warnings.

    Use rectangular boxes from result only when the source hash matches. Save
    under output_dir/images when save_images is true; otherwise retain bytes
    only. Invalid boxes, page crop errors, and count/byte limits omit crops
    without changing transcription. Configuration errors may propagate.
    """
    figures = {}
    warnings = []
    byte_limit, count_limit = max_figure_bytes(), max_figures()
    retained_bytes = 0
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
                    if len(figures) >= count_limit:
                        warnings.append("Figure count limit reached; remaining crops omitted")
                        return figures, warnings
                    if block.bbox is None or block.bbox.page != page.page or not _bbox_is_valid(block.bbox.xyxy):
                        warnings.append(f"Page {page.page}, figure {index}: invalid or missing box")
                        continue
                    x0, y0, x1, y1 = block.bbox.xyxy
                    with image.crop((math.floor(x0 * image.width), math.floor(y0 * image.height),
                                     math.ceil(x1 * image.width), math.ceil(y1 * image.height))) as crop:
                        with io.BytesIO() as buffer:
                            crop.save(buffer, format="PNG")
                            data = buffer.getvalue()
                    name = figure_name(page.page, index, output_basename)
                    directory = Path(output_dir) / "images"
                    if retained_bytes + len(data) > byte_limit:
                        warnings.append("Figure byte limit reached; remaining crops omitted")
                        return figures, warnings
                    if save_images:
                        directory.mkdir(parents=True, exist_ok=True)
                        (directory / name).write_bytes(data)
                    figures[name] = data
                    retained_bytes += len(data)
        except Exception:
            # Presentation failures must not discard a successful transcription.
            warnings.append(f"Page {page.page}: figure crops unavailable")
    return figures, warnings


def load_figures(result: ParseResult, output_dir: str | Path, *, output_basename: str | None = None) -> dict[str, bytes]:
    """Load validated saved PNG crops for result, accepting legacy filenames.

    Search output_dir/images using the run basename and page/block positions.
    Skip missing or unreadable images. Raise ValueError when saved collections
    exceed configured count/byte limits; filesystem/configuration errors may
    propagate. No source document or model is read.
    """
    figures = {}
    byte_limit, count_limit = max_figure_bytes(), max_figures()
    retained_bytes = 0
    for page in result.pages:
        for index, block in enumerate(page.blocks):
            if block.type != "figure":
                continue
            names = dict.fromkeys((figure_name(page.page, index, output_basename), figure_name(page.page, index)))
            for name in names:
                path = Path(output_dir) / "images" / name
                if not path.is_file():
                    continue
                if len(figures) >= count_limit or path.stat().st_size > byte_limit - retained_bytes:
                    raise ValueError("Saved figures exceed configured count or byte limit")
                try:
                    with path.open("rb") as handle:
                        data = handle.read(byte_limit - retained_bytes + 1)
                    if len(data) > byte_limit - retained_bytes:
                        raise OSError("Figure changed while reading")
                    with Image.open(io.BytesIO(data)) as image:
                        if image.format != "PNG" or image.width * image.height > max_image_pixels():
                            continue
                        image.verify()
                    figures[name] = data
                    retained_bytes += len(data)
                    break
                except (OSError, ValueError):
                    continue
    return figures
