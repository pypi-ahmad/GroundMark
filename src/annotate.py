"""Draw reconciled full contours and explicit detector-only inspection overlays.

PDF, page PNGs, and metadata are independently selectable under output_dir
(data/annotated/ by default). These are inspection artifacts, not parser
inputs. Rectangles remain the envelope used by crop and chat consumers.

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
from src.layout import ParseResult, LayoutPageArtifact
from src.output_names import artifact_name

BOX_COLOR = (220, 30, 30)
V3_COLOR = (0, 102, 204)
DETECTOR_COLOR = (190, 110, 0)
LABEL_FONT_SIZE = 16


def _bbox_is_valid(xyxy: tuple[float, float, float, float]) -> bool:
    # Coordinates are normalized 0-1 (see BBox.xyxy in src/layout.py);
    # reject anything outside that range or degenerate (zero/negative width
    # or height) instead of drawing a nonsensical box.
    x0, y0, x1, y1 = xyxy
    if not all(0.0 <= v <= 1.0 for v in xyxy):
        return False
    return x1 > x0 and y1 > y0


def page_overlays(page, artifact):
    """Yield inspection references and geometry; never infer correspondence."""
    if artifact is not None:
        artifact = LayoutPageArtifact.model_validate(artifact.model_dump())
        artifact.check_parsed_page(page)
    details = artifact.reconciliation if artifact else None
    matches = {d.output_index: d for d in details.decisions if d.region_index is not None} if details else {}

    def detector(region, kind, output_index=None, original_index=None):
        full = region.contour_status == "valid"
        return (dict(kind=kind, output_index=output_index, original_index=original_index,
                     region_index=region.index, class_id=region.class_id, label=region.canonical_label,
                     confidence=region.score, order=region.order, contour_source=region.contour_source,
                     geometry="polygon" if full else "v3_aabb",
                     geometry_fallback=None if full else (
                         "upstream_rectangle_fallback" if region.contour_source == "aabb_fallback"
                         else region.contour_status)),
                region.bbox, region.polygon if full else ())

    for index, block in enumerate(page.blocks if page else []):
        decision = matches.get(index)
        if decision is not None:
            yield detector(artifact.layout.regions[decision.region_index], "matched",
                           index, decision.original_index)
        else:
            valid = (block.bbox is not None and block.bbox.page == page.page
                     and _bbox_is_valid(block.bbox.xyxy))
            yield (dict(kind="sol", output_index=index, region_index=None, label=block.type,
                        geometry="sol_aabb" if valid else "skipped", geometry_fallback=None),
                   block.bbox if valid else None, ())
    if artifact:
        indices = details.unmatched_region_indices if details else range(len(artifact.layout.regions))
        for index in indices:
            yield detector(artifact.layout.regions[index],
                           "detector_only" if details else "unreconciled_detector_only")


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
    """Draw selected geometry and return optional PDF and metadata Paths.

    Pillow encodes each rasterized page separately. PDFium assembles those
    encoded pages without retaining every page's decoded pixels at once.

    save_pdf, save_images, and save_metadata select independent artifacts.
    Missing, out-of-range, and degenerate boxes are skipped and counted when
    metadata is saved. Source/decoder, naming, and filesystem errors propagate.
    No model calls occur. Invalid artifact mappings raise rather than silently
    replacing selected detector geometry with Sol boxes.
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
    pages_by_number = {page.page: page for page in parse_result.pages}
    artifacts = {}
    for entry in parse_result.layout_metadata:
        if entry.layout.page in artifacts:
            raise ValueError("Duplicate annotation layout page")
        checked = LayoutPageArtifact.model_validate(entry.model_dump())
        checked.check_parsed_page(pages_by_number.get(entry.layout.page))
        artifacts[entry.layout.page] = checked

    font = ImageFont.load_default(size=LABEL_FONT_SIZE)
    annotated_paths: list[tuple[int, Path]] = []
    drawn = 0
    skipped = 0
    detector_drawn = 0
    inspection = []

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

            artifact = artifacts.get(payload["page"])
            if artifact and (artifact.layout.width_px, artifact.layout.height_px) != image.size:
                raise ValueError("Annotation raster disagrees with V3 coordinates")
            rows = []
            for row, box, polygon in page_overlays(pages_by_number.get(payload["page"]), artifact):
                rows.append(row)
                if box is None:
                    skipped += 1
                    continue
                x0, y0, x1, y1 = box.xyxy
                box_px = (x0 * image.width, y0 * image.height, x1 * image.width, y1 * image.height)
                is_detector_only = row["kind"].endswith("detector_only")
                color = DETECTOR_COLOR if is_detector_only else V3_COLOR if row["kind"] == "matched" else BOX_COLOR
                if polygon:
                    points = [(x * image.width, y * image.height) for x, y in polygon]
                    draw.line(points + points[:1], fill=color, width=2 if is_detector_only else 3)
                else:
                    draw.rectangle(box_px, outline=color, width=2 if is_detector_only else 3)
                label = row["label"]
                if row["region_index"] is not None:
                    prefix = "V3-only" if is_detector_only else f"b{row['output_index']}"
                    order = row["order"] if row["order"] is not None else "?"
                    label = f"{prefix} r{row['region_index']} {label} {row['confidence']:.2f} o{order}"
                draw.text((box_px[0], max(box_px[1] - LABEL_FONT_SIZE - 2, 0)), label,
                          fill=color, font=font)
                if is_detector_only:
                    detector_drawn += 1
                else:
                    drawn += 1
            inspection.append(dict(page=payload["page"], overlays=rows,
                                   model_id=artifact.layout.model_id if artifact else None,
                                   revision=artifact.layout.revision if artifact else None,
                                   device=artifact.layout.device if artifact else None))

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
                    "detector_regions_drawn": detector_drawn,
                    "page_annotations": inspection,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    return pdf_path if save_pdf else None, meta_path if save_metadata else None
