"""Offline provenance, overlay, and fallback contracts; no model requests."""
from dataclasses import replace
import json

from PIL import Image
import pytest

from src.annotate import annotate_document, page_overlays, V3_COLOR, DETECTOR_COLOR, BOX_COLOR
from src.layout import LayoutPageArtifact, ParseResult, ReconciliationDetails
from src.layout_reconcile import convert_layout, reconcile_page
from tests.test_layout_reconcile import block, page, region, runtime


def artifact_for(result):
    return LayoutPageArtifact(layout=result.metadata.layout,
        reconciliation=ReconciliationDetails.model_validate(result.metadata.model_dump(exclude={"layout"})))


def test_full_contour_and_detector_only_draw_once_on_png_and_pdf(tmp_path):
    import pypdfium2 as pdfium
    source = tmp_path / "source.png"
    Image.new("RGB", (100, 100), "white").save(source)
    original = page(block(), block((.05, .7, .2, .9), text="unmatched"))
    layout = convert_layout(runtime(region(polygon=((10, 10), (50, 10), (10, 50))),
                                    region((60, 60, 90, 90), order=20)))
    result = reconcile_page(original, layout)
    artifact = artifact_for(result)
    document = ParseResult(doc_sha="test", pages=[result.page], layout_metadata=[artifact])
    before = document.model_dump()
    pdf, metadata = annotate_document(source, document, output_dir=tmp_path / "out")
    with Image.open(pdf.parent / "test" / "page_001.png") as image:
        assert image.getpixel((30, 30)) == V3_COLOR
        assert image.getpixel((50, 40)) == (255, 255, 255)  # no matched envelope rectangle
        assert image.getpixel((60, 75)) == DETECTOR_COLOR
        assert image.getpixel((5, 85)) == BOX_COLOR
    with pdfium.PdfDocument(pdf) as doc:
        rendered = doc[0].render(scale=1).to_pil()
        blue = rendered.getpixel((30, 30))
        assert blue[2] > blue[0] + 50  # PDF raster encoding is lossy
    meta = json.loads(metadata.read_text())
    assert (meta["blocks_drawn"], meta["detector_regions_drawn"]) == (2, 1)
    rows = meta["page_annotations"][0]["overlays"]
    assert [r["region_index"] for r in rows] == [0, None, 1]
    assert rows[0]["geometry"] == "polygon" and rows[0]["order"] == 0
    assert document.model_dump() == before


def test_reordered_duplicate_ids_resolve_output_indices_and_legacy_provenance():
    layout = convert_layout(runtime(region(order=8), region((60, 60, 90, 90), order=1)))
    result = reconcile_page(page(block(), block((.6, .6, .9, .9))), layout)
    artifact = artifact_for(result)
    rows = list(page_overlays(result.page, artifact))
    assert [row[0]["region_index"] for row in rows] == [1, 0]
    assert [row[0]["original_index"] for row in rows] == [1, 0]
    data = artifact.model_dump()
    for value in data["layout"]["regions"]:
        value.pop("contour_source")
    assert LayoutPageArtifact.model_validate(data).layout.regions[0].contour_source == "legacy_unknown"


def test_upstream_rectangle_is_not_a_segmentation_contour():
    raw = replace(region(), contour_source="aabb_fallback")
    layout = convert_layout(runtime(raw))
    assert layout.regions[0].polygon_px == raw.polygon_px
    assert layout.regions[0].polygon == () and layout.regions[0].contour_status == "unusable"
    result = reconcile_page(page(block()), layout)
    row, box, points = next(page_overlays(result.page, artifact_for(result)))
    assert row["geometry"] == "v3_aabb"
    assert row["geometry_fallback"] == "upstream_rectangle_fallback"
    assert box == layout.regions[0].bbox and not points
    assert result.metadata.candidates[0].geometry == "aabb"


def test_analysis_only_is_unreconciled_not_a_match_and_bad_mapping_raises():
    layout = convert_layout(runtime(region()))
    rows = list(page_overlays(page(block()), LayoutPageArtifact(layout=layout)))
    assert [r[0]["kind"] for r in rows] == ["sol", "unreconciled_detector_only"]
    result = reconcile_page(page(block()), layout)
    artifact = artifact_for(result)
    result.page.blocks[0].bbox.xyxy = (0, 0, 1, 1)
    with pytest.raises(ValueError, match="geometry disagrees"):
        list(page_overlays(result.page, artifact))


@pytest.mark.parametrize("detailed", [False, True])
@pytest.mark.parametrize("bad", ["base64", "mime", "dimensions", "truncated"])
def test_invalid_image_with_initialization_failure_never_calls_sol(monkeypatch, detailed, bad):
    from src import parse
    from src.diagnostics import ExtractionCallError, PageDiagnostic
    from tests.fake_layout import payload
    import base64
    data = payload()
    width = 100
    if bad == "base64":
        data["base64"] = "invalid"
    elif bad == "mime":
        data["mime"] = "image/jpeg"
    elif bad == "dimensions":
        width = 200
    else:
        data["base64"] = base64.b64encode(base64.b64decode(data["base64"])[:45]).decode()
    monkeypatch.setattr(parse, "_build_llm", lambda **kw: pytest.fail("Sol called"))
    failure = PageDiagnostic(layout_stage="initialization", layout_code="dependencies_unavailable")
    diagnostics = []
    with pytest.raises(ExtractionCallError) as caught:
        parse.parse_page(data["base64"], data["mime"], 1, width, 100, diagnostics=diagnostics,
                         detailed_layout=detailed, layout_initialization_failure=failure)
    assert caught.value.diagnostic.layout_code == "invalid_image"
    assert not caught.value.diagnostic.layout_fallback


def test_mask_rectangle_and_empty_mask_have_distinct_provenance():
    np = pytest.importorskip("numpy")
    pytest.importorskip("cv2")
    from src.layout_detector import _decode_onnx
    boxes = np.array([[22, .9, 10, 10, 90, 90, 2]], dtype=np.float32)
    empty = np.zeros((1, 200, 200), dtype=np.int32)
    filled = empty.copy()
    filled[0, 20:180, 20:180] = 1
    assert _decode_onnx([boxes, np.array([1]), empty], 100, 100)[0].contour_source == "aabb_fallback"
    rectangle = _decode_onnx([boxes, np.array([1]), filled], 100, 100)[0]
    assert rectangle.contour_source == "mask" and len(rectangle.polygon_px) == 4


def test_weight_repository_and_file_contract_are_onnx_only():
    from src.layout_detector import MODEL_ID, REVISION, MODEL_FILES
    assert MODEL_ID == "PaddlePaddle/PP-DocLayoutV3_onnx"
    assert REVISION == "46bbdf188bb0a772c08aed74882ce7e51a8f1ea6"
    assert set(MODEL_FILES) == {"inference.onnx", "inference.yml"}
