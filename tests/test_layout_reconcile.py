"""Synthetic offline geometry, matching, and existing-consumer contracts."""
from dataclasses import replace
import hashlib
import io
import json
import subprocess
import sys

from PIL import Image
import pytest

from src.annotate import _bbox_is_valid
from src.figures import extract_figures
from src.layout import BBox, BlockStructure, ListItem, ParseBlock, ParsePage, ParseResult, TableCell
from src.layout_detector import LABELS, LayoutPageResult, LayoutRegion
from src.layout_reconcile import (
    LayoutConversionError, ReconcilePolicy, ROLE_HINTS, convert_layout, reconcile_page,
)
from src.markdown import parse_to_html, parse_to_markdown


def region(box=(10, 10, 50, 50), *, label="text", score=.95, order=0, polygon=None):
    x0, y0, x1, y1 = box
    return LayoutRegion(LABELS.index(label), label, score, box,
                        polygon if polygon is not None else ((x0, y0), (x1, y0), (x1, y1), (x0, y1)), order)


def runtime(*regions, width=100, height=100, page=1):
    return LayoutPageResult(page, width, height, regions, "cpu", None)


def block(box=(.1, .1, .5, .5), *, text="Source", kind="text", **kwargs):
    return ParseBlock(id="duplicate-id", type=kind, text=text,
                      bbox=BBox(page=1, xyxy=box) if box is not None else None,
                      conf=kwargs.pop("conf", .87), table=kwargs.pop("table", None),
                      structure=kwargs.pop("structure", None), **kwargs)


def page(*blocks, width=100, height=100):
    return ParsePage(page=1, width_px=width, height_px=height, blocks=list(blocks))


def reconcile(blocks, regions, **kwargs):
    return reconcile_page(page(*blocks), convert_layout(runtime(*regions)), **kwargs)


def test_conversion_clips_box_and_polygon_preserving_raw_and_provenance():
    raw = replace(region((-10, 10, 110, 90)), label="raw detector alias")
    source = runtime(raw, height=200)
    normalized = convert_layout(source)
    converted = normalized.regions[0]
    assert converted.bbox == BBox(page=1, xyxy=(0, .05, 1, .45))
    assert set(converted.polygon) == {(0, .05), (1, .05), (1, .45), (0, .45)}
    assert converted.box_px == raw.box_px and converted.polygon_px == raw.polygon_px
    assert converted.raw_label == raw.label and converted.canonical_label == "text"
    assert converted.box_clipped and converted.polygon_clipped
    assert normalized.model_id == source.model_id and normalized.revision == source.revision
    assert normalized.device == "cpu" and normalized.order_base == 0
    json.dumps(normalized.model_dump(mode="json"), allow_nan=False)


def test_triangle_clipping_preserves_edges_not_vertex_clamping_or_rectangles():
    converted = convert_layout(runtime(region((-20, 20, 60, 80), polygon=((-20, 20), (60, 20), (60, 80))))).regions[0]
    assert set(converted.polygon) == {(0, .2), (.6, .2), (.6, .8), (0, .35)}
    assert (0, .8) not in converted.polygon


@pytest.mark.parametrize("points", [
    ((10, 10), (10, 50), (50, 50), (50, 10)),  # clockwise
    ((10, 10), (50, 10), (50, 50), (30, 30), (10, 50)),  # concave
    ((10, 10), (10, 10), (50, 10), (50, 50), (10, 50), (10, 10)),
])
def test_valid_polygon_shapes_and_redundant_closure(points):
    result = convert_layout(runtime(region(polygon=points))).regions[0]
    assert result.polygon_px == points
    assert len(set(result.polygon)) == len(result.polygon)
    assert not result.polygon_clipped


@pytest.mark.parametrize("changes,code", [
    ({"box_px": (10, 10, float("nan"), 50)}, "invalid_box"),
    ({"box_px": (10, 10, float("inf"), 50)}, "invalid_box"),
    ({"box_px": (50, 10, 10, 50)}, "invalid_box"),
    ({"box_px": (10, 10, 10, 50)}, "invalid_box"),
    ({"box_px": (-20, 10, 0, 50)}, "invalid_box"),
    ({"polygon_px": ((10, 10), (20, 20), (30, 30))}, "invalid_polygon"),
    ({"polygon_px": ((10, 10), (50, 50), (10, 50), (50, 10))}, "invalid_polygon"),
    ({"polygon_px": ((10, 10), (80, 10), (20, 10), (50, 50))}, "invalid_polygon"),
    ({"polygon_px": ((10, 10), (50, 10), (float("nan"), 50))}, "invalid_polygon"),
    ({"polygon_px": ((110, 10), (150, 10), (150, 50))}, "invalid_polygon"),
    ({"polygon_px": ()}, "invalid_polygon"),
    ({"score": float("inf")}, "invalid_score"),
    ({"score": -1}, "invalid_score"),
    ({"class_id": 25}, "invalid_class"),
    ({"order": -1}, "invalid_order"),
    ({"order": True}, "invalid_order"),
    ({"order": 300}, "invalid_order"),
])
def test_invalid_region_fails_closed_with_safe_location(changes, code):
    source = runtime(region(), replace(region(), **changes))
    with pytest.raises(LayoutConversionError) as exc:
        convert_layout(source)
    assert (exc.value.code, exc.value.page, exc.value.region_index) == (code, 1, 1)
    assert "Source" not in str(exc.value)


def test_disconnected_clipped_polygon_is_rejected_not_fabricated():
    # Connected above the viewport, but two separate legs inside it.
    points = ((10, -20), (90, -20), (90, 50), (70, 50), (70, -10), (30, -10), (30, 50), (10, 50))
    with pytest.raises(LayoutConversionError, match="invalid_polygon"):
        convert_layout(runtime(region((10, -20, 90, 50), polygon=points)))


@pytest.mark.parametrize("changes,code", [
    ({"width_px": 0}, "invalid_page"), ({"height_px": -1}, "invalid_page"),
    ({"page": 0}, "invalid_page"), ({"order_base": 1}, "invalid_order_base"),
])
def test_invalid_page_metadata(changes, code):
    with pytest.raises(LayoutConversionError, match=code):
        convert_layout(replace(runtime(), **changes))


def test_page_identity_and_dimensions_must_match():
    for layout in (runtime(page=2), runtime(width=200), runtime(height=200)):
        with pytest.raises(LayoutConversionError, match="page_mismatch"):
            reconcile_page(page(), convert_layout(layout))


def test_confident_match_changes_geometry_only_and_does_not_share_mutable_inputs():
    source = page(block())
    layout = convert_layout(runtime(region((11, 10, 51, 50))))
    before, before_layout = source.model_dump(), layout.model_dump()
    result = reconcile_page(source, layout)
    assert result.page.blocks[0].bbox.xyxy == (.11, .1, .51, .5)
    assert result.metadata.decisions[0].region_index == 0
    assert result.metadata.candidates[0].sol_coverage == pytest.approx(.975)
    assert result.metadata.candidates[0].reasons == ()
    assert result.metadata.unmatched_region_indices == ()
    assert source.model_dump() == before and layout.model_dump() == before_layout
    result.page.blocks[0].bbox.xyxy = (0, 0, 1, 1)
    result.metadata.layout.regions[0].bbox.xyxy = (0, 0, 1, 1)
    assert source.model_dump() == before and layout.model_dump() == before_layout


def test_two_columns_reorder_only_matched_slots_with_duplicate_ids():
    boxes = [(60, 10, 90, 30), (10, 60, 40, 80), (10, 10, 40, 30), (60, 60, 90, 80)]
    blocks = [block(tuple(v / 100 for v in box), text=str(i)) for i, box in enumerate(boxes)]
    blocks.insert(1, block(None, text="unpositioned"))
    regions = [region(box, order=rank) for box, rank in zip(boxes, (20, 10, 0, 30))]
    result = reconcile(blocks, regions)
    assert [b.text for b in result.page.blocks] == ["2", "unpositioned", "1", "0", "3"]
    assert [d.output_index for d in result.metadata.decisions] == [3, 1, 2, 0, 4]
    doc = ParseResult(doc_sha="test", pages=[result.page])
    for render in (parse_to_markdown, parse_to_html):
        output = render(doc)
        assert output.index("unpositioned") < output.index(">1<" if render is parse_to_html else "\n1\n")


def test_missing_and_duplicate_ranks_keep_stable_positions():
    boxes = [(0, 0, 20, 20), (30, 0, 50, 20), (60, 0, 80, 20)]
    blocks = [block(tuple(v / 100 for v in box), text=str(i)) for i, box in enumerate(boxes)]
    result = reconcile(blocks, [region(box, order=rank) for box, rank in zip(boxes, (142, None, 142))])
    assert [b.text for b in result.page.blocks] == ["0", "1", "2"]
    assert result.metadata.decisions[1].reasons == ("missing_order",)
    assert [r.order for r in result.metadata.layout.regions] == [142, None, 142]


@pytest.mark.parametrize("blocks,regions,reason", [
    ([block((.1, .1, .9, .5))], [region((10, 10, 50, 50)), region((50, 10, 90, 50))], "split"),
    ([block((.1, .1, .5, .5)), block((.5, .1, .9, .5))], [region((10, 10, 90, 50))], "merge"),
    ([block(), block()], [region(), region()], "many_to_many"),
    ([block()], [region(), region((20, 20, 30, 30))], "split"),
])
def test_split_merge_nested_and_many_to_many_never_snap(blocks, regions, reason):
    result = reconcile(blocks, regions)
    assert result.page == page(*blocks)
    assert all(d.region_index is None and reason in d.reasons for d in result.metadata.decisions)
    assert result.metadata.unmatched_region_indices == tuple(range(len(regions)))


def test_equal_scores_use_geometry_but_exact_geometric_ties_are_reviewed():
    result = reconcile([block()], [region((49, 10, 89, 50)), region((11, 10, 51, 50))])
    assert result.metadata.decisions[0].region_index == 1
    tied = reconcile([block()], [region(), region()])
    assert tied.metadata.decisions[0].region_index is None
    assert [c.region_index for c in tied.metadata.candidates] == [0, 1]
    assert "ambiguous" in tied.metadata.candidates[0].reasons
    assert tied == reconcile([block()], [region(), region()])


def test_weak_overlap_low_score_and_distance_are_reported():
    for layout, reason in ((region((40, 10, 80, 50)), "weak_overlap"),
                           (region(score=.79), "low_score")):
        result = reconcile([block()], [layout])
        assert result.page == page(block())
        assert reason in result.metadata.decisions[0].reasons
    result = reconcile([block()], [region((11, 10, 51, 50))], policy=ReconcilePolicy(max_center_distance=0))
    assert "distant_centers" in result.metadata.decisions[0].reasons


def test_initial_threshold_boundaries_and_policy_evidence():
    result = reconcile([block((0, 0, 1, 1))], [region((0, 0, 90, 100), score=.80)])
    assert result.metadata.decisions[0].region_index == 0
    assert result.metadata.candidates[0].sol_coverage == .9
    assert result.metadata.policy.min_iou_margin == .1
    assert result.metadata.policy_version == "conservative-v2"
    for box in ((0, 0, 89.99, 100), (0, 0, 90, 100)):
        low_score = .7999 if box[2] == 90 else .8
        assert reconcile([block((0, 0, 1, 1))], [region(box, score=low_score)]).metadata.decisions[0].region_index is None
    with pytest.raises(ValueError):
        ReconcilePolicy(min_score=float("nan"))


def test_near_ties_remain_ambiguous_even_if_topology_gate_is_tuned():
    result = reconcile([block()], [region((11, 10, 51, 50)), region((12, 10, 52, 50))],
                       policy=ReconcilePolicy(significant_coverage=1))
    assert result.metadata.decisions[0].region_index is None
    assert "ambiguous" in result.metadata.decisions[0].reasons


def test_iou_margin_boundary_and_zero_margin_does_not_accept_exact_ties():
    regions = [region(), region((15, 10, 55, 50))]
    initial = reconcile([block()], regions, policy=ReconcilePolicy(significant_coverage=1))
    first, second = initial.metadata.candidates
    margin = first.iou - second.iou
    assert reconcile([block()], regions, policy=ReconcilePolicy(
        significant_coverage=1, min_iou_margin=margin)).metadata.decisions[0].region_index == 0
    result = reconcile([block()], regions, policy=ReconcilePolicy(
        significant_coverage=1, min_iou_margin=margin + 1e-9))
    assert "ambiguous" in result.metadata.decisions[0].reasons
    tied = reconcile([block()], [region((11, 10, 51, 50)), region((11, 10, 51, 50))],
                     policy=ReconcilePolicy(significant_coverage=1, min_iou_margin=0))
    assert tied.metadata.decisions[0].region_index is None
    assert "ambiguous" in tied.metadata.decisions[0].reasons


def test_mutual_best_prevents_two_blocks_claiming_one_region_even_with_tuned_policy():
    blocks = [block(), block((.14, .1, .54, .5), text="Other")]
    result = reconcile(blocks, [region((11, 10, 51, 50))],
                       policy=ReconcilePolicy(significant_coverage=1, min_iou_margin=0))
    assert result.metadata.decisions[0].region_index == 0
    assert result.metadata.decisions[1].region_index is None
    assert "not_mutual_best" in result.metadata.decisions[1].reasons
    assert result.page.blocks[1] == blocks[1]


@pytest.mark.parametrize("box,reason", [
    (None, "missing_box"), ((0, 0, 2, 1), "invalid_box"),
    ((.2, .2, .2, .3), "invalid_box"), ((0, 0, float("nan"), 1), "invalid_box"),
    ((.6, .6, .9, .9), "no_overlap"), ((.5, .1, .8, .5), "no_overlap"),
])
def test_unmatched_sol_boxes_are_preserved_and_metadata_stays_finite(box, reason):
    original = block(box)
    result = reconcile([original], [region()])
    assert result.page.blocks[0].text == original.text
    if box is None:
        assert result.page.blocks[0].bbox is None
    else:
        assert result.page.blocks[0].bbox.model_dump_json() == original.bbox.model_dump_json()
    assert result.metadata.decisions[0].reasons == (reason,)
    json.dumps(result.metadata.model_dump(mode="json"), allow_nan=False)


def test_wrong_page_sol_box_is_preserved_and_empty_results_are_valid():
    original = block()
    original.bbox.page = 2
    result = reconcile([original], [region()])
    assert result.page.blocks[0] == original
    assert result.metadata.decisions[0].reasons == ("invalid_box",)
    assert reconcile([], [region()]).page.blocks == []
    assert reconcile([], []).metadata.candidates == ()
    assert reconcile([block()], []).page == page(block())


def test_all_role_hints_preserve_raw_labels_and_every_sol_type():
    assert set(ROLE_HINTS) == set(LABELS) and len(ROLE_HINTS) == 25
    expected_groups = {
        "title": "doc_title", "heading": "paragraph_title", "table": "table",
        "figure": "chart image header_image footer_image seal",
        "page_header": "header", "page_footer": "footer",
        "marginalia": "aside_text footnote vision_footnote",
        "text": "abstract algorithm content display_formula figure_title formula_number inline_formula number reference reference_content text vertical_text",
    }
    assert ROLE_HINTS == {label: role for role, labels in expected_groups.items() for label in labels.split()}
    for label in LABELS:
        for kind in ("title", "heading", "list", "table", "text", "page_header", "page_footer", "figure"):
            source = block(kind=kind)
            result = reconcile([source], [replace(region(label=label), label="raw alias")])
            assert result.page.blocks[0].type == kind
            assert result.metadata.layout.regions[0].raw_label == "raw alias"
            assert result.metadata.layout.regions[0].role_hint == ROLE_HINTS[label]
            assert "label_disagreement" in result.metadata.decisions[0].reasons
            assert result.page.blocks[0] == source
            assert result.metadata.decisions[0].region_index is None


@pytest.mark.parametrize("kind,label", [("table", "text"), ("heading", "text"),
                                       ("list", "text"), ("text", "header"), ("figure", "table")])
def test_role_mismatch_keeps_sol_box_and_position_even_with_strong_overlap(kind, label):
    source = block(kind=kind)
    other = block((.6, .6, .9, .9), text="Other")
    result = reconcile([source, other], [region((11, 10, 51, 50), label=label, order=1),
                                         region((60, 60, 90, 90), order=0)])
    assert result.page.blocks[0] == source
    assert result.metadata.decisions[0].region_index is None
    assert result.metadata.decisions[0].reasons == ("role_disagreement",)
    assert result.metadata.decisions[0].output_index == 0
    assert result.metadata.decisions[1].region_index == 1
    assert result.metadata.unmatched_region_indices == (0,)


def test_old_reconciliation_policy_metadata_still_loads():
    from src.layout import ReconciliationMetadata
    data = reconcile([block()], [region()]).metadata.model_dump()
    data["policy_version"] = "conservative-v1"
    assert ReconciliationMetadata.model_validate(data).policy_version == "conservative-v1"
    del data["policy_version"]
    assert ReconciliationMetadata.model_validate(data).policy_version == "conservative-v1"


def test_header_footer_labels_never_hide_sol_content_in_clean_view():
    result = reconcile([block(text="Keep visible")], [region(label="header")])
    doc = ParseResult(doc_sha="test", pages=[result.page])
    for render in (parse_to_markdown, parse_to_html):
        assert "Keep visible" in render(doc, view="clean")
    result = reconcile([block(kind="page_footer", text="Page 1")], [region(label="text")])
    doc.pages = [result.page]
    for render in (parse_to_markdown, parse_to_html):
        assert "Page 1" not in render(doc, view="clean")
        assert "Page 1" in render(doc)


def test_header_body_footer_rank_order_preserves_existing_furniture_types():
    blocks = [block((0, .9, 1, 1), kind="page_footer", text="Footer"),
              block((.1, .2, .9, .8), text="Body"),
              block((0, 0, 1, .1), kind="page_header", text="Header")]
    regions = [region((0, 90, 100, 100), label="footer", order=299),
               region((10, 20, 90, 80), order=50), region((0, 0, 100, 10), label="header", order=0)]
    result = reconcile(blocks, regions)
    assert [b.text for b in result.page.blocks] == ["Header", "Body", "Footer"]
    assert [b.type for b in result.page.blocks] == ["page_header", "text", "page_footer"]


def test_all_transcription_and_detailed_structure_fields_survive_without_aliasing():
    structures = [
        ("heading", None, BlockStructure(heading_level=3, list_items=None, table_cells=None)),
        ("list", None, BlockStructure(heading_level=None, table_cells=None, list_items=[
            ListItem(text="exact\ntext", marker="☑", depth=0, checked=True),
            ListItem(text="nested", marker="b)", depth=1, checked=None)])),
        ("table", [["Merged", ""], ["A\nB", " C "]], BlockStructure(heading_level=None, list_items=None, table_cells=[
            TableCell(row=0, column=0, rowspan=1, colspan=2, is_header=True),
            TableCell(row=1, column=0, rowspan=1, colspan=1, is_header=False),
            TableCell(row=1, column=1, rowspan=1, colspan=1, is_header=False)])),
    ]
    for kind, table, structure in structures:
        source = block(kind=kind, text="  Exact source\n☑ <tag> **text**  ", table=table, structure=structure, conf=None)
        before = source.model_dump()
        result = reconcile([source], [region((11, 10, 51, 50))])
        updated = result.page.blocks[0]
        assert updated.model_dump(exclude={"bbox"}) == source.model_dump(exclude={"bbox"})
        assert updated.structure is not source.structure
        if updated.table:
            updated.table[0][0] = "changed copy"
        assert source.model_dump() == before


def test_rectangular_consumers_and_fresh_position_named_figure_crops(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (100, 80), "red").save(source)
    blocks = [block((.1, .25, .59, .75), kind="figure", text="Caption"),
              block((.7, .1, .9, .2), text="First")]
    layout = convert_layout(runtime(region((10, 20, 60, 60), label="image", order=20),
                                    region((70, 8, 90, 16), order=10), height=80))
    result = reconcile_page(page(*blocks, height=80), layout)
    assert all(_bbox_is_valid(b.bbox.xyxy) for b in result.page.blocks)
    assert result.page.blocks[1].type == "figure"
    doc = ParseResult(doc_sha=hashlib.sha256(source.read_bytes()).hexdigest(), pages=[result.page])
    figures, warnings = extract_figures(source, doc, tmp_path / "run")
    assert not warnings and list(figures) == ["page_001_figure_001.png"]
    with Image.open(io.BytesIO(next(iter(figures.values())))) as crop:
        assert crop.size == (50, 40)
    assert "images/page_001_figure_001.png" in parse_to_markdown(doc, figures=figures)
    assert "data:image/png;base64," in parse_to_html(doc, figures=figures)


def test_base_import_never_loads_optional_inference_packages_or_initializes_runtime():
    code = """
import sys
class NoInferenceImports:
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in {'torch', 'torchvision', 'transformers', 'cv2', 'huggingface_hub'}:
            raise AssertionError('Optional inference import: ' + fullname)
sys.meta_path.insert(0, NoInferenceImports())
from src.layout_reconcile import convert_layout
from src import layout_detector
assert layout_detector._singleton is None
"""
    subprocess.run([sys.executable, "-B", "-c", code], check=True, capture_output=True, text=True)
