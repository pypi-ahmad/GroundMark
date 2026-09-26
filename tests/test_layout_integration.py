"""Active-path tests with in-memory V3 and LLM fakes; no paid or local inference."""
import base64
from copy import deepcopy
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
from pydantic import ValidationError
import pytest

from src import graph, parse, usage
from src.chat import document_pages
from src.config import ConfigError
from src.diagnostics import ExtractionCallError, layout_failure_diagnostic, layout_failure_summary
from src.layout import (BBox, BlockStructure, LegacyParsePage, ListItem,
                        ParseBlock, ParsePage, ParseResult, TableCell)
from src.layout_detector import LayoutInferenceError, LayoutModelUnavailable
from src.layout_reconcile import convert_layout, given_layout_json
from src.preprocess import MAX_LONG_EDGE, PDF_DPI, preprocess_pages
from tests.fake_layout import FakeLayoutRuntime, payload
from tests.fake_llm import FakeLLM
from tests.test_layout_reconcile import region, runtime


def sol_page(number=1, detailed=False):
    structures = {
        "heading": BlockStructure(heading_level=3, list_items=None, table_cells=None),
        "list": BlockStructure(heading_level=None, table_cells=None, list_items=[
            ListItem(text="Item", marker="☑", depth=0, checked=True),
            ListItem(text="Child", marker="b)", depth=1, checked=None)]),
        "table": BlockStructure(heading_level=None, list_items=None, table_cells=[
            TableCell(row=0, column=0, rowspan=1, colspan=2, is_header=True),
            TableCell(row=1, column=0, rowspan=1, colspan=1, is_header=False),
            TableCell(row=1, column=1, rowspan=1, colspan=1, is_header=False)]),
    }
    blocks = []
    for kind, text, box in (
        ("figure", "Caption", (.6, .6, .89, .9)),
        ("table", "Merged\nB | C", (.1, .5, .5, .8)),
        ("heading", "Exact Heading", (.1, .1, .5, .2)),
        ("list", "☑ Item\n  b) Child", (.1, .25, .5, .4)),
        ("text", "  Visible outside regions {literal}  ", None),
    ):
        blocks.append(ParseBlock(id=kind, type=kind, text=text,
                                 bbox=BBox(page=number, xyxy=box) if box else None, conf=.87,
                                 table=[["Merged", ""], ["B", " C "]] if kind == "table" else None,
                                 structure=structures.get(kind) if detailed else None))
    return ParsePage(page=number, width_px=100, height_px=100, blocks=blocks)


def regions():
    return [region((60, 60, 90, 90), label="image", order=40),
            region((11, 50, 51, 80), label="table", order=20),
            region((11, 10, 51, 20), label="paragraph_title", order=0),
            region((11, 25, 51, 40), order=10)]


def wire_llm(page, events, requests, *, finish="stop", content=None):
    client = FakeLLM(page)
    original = client.root_client.chat.completions.with_raw_response.create

    def create(**kwargs):
        events.append(("sol", page.page))
        requests.append(kwargs)
        body = original(**kwargs).parse().model_dump()
        body["choices"][0]["finish_reason"] = finish
        if content is not None:
            body["choices"][0]["message"]["content"] = content
        if finish == "content_filter":
            body["choices"][0]["content_filter_results"] = {"sexual": {"filtered": True, "severity": "high"}}
        body["usage"] = {"prompt_tokens": 100, "completion_tokens": 20,
                         "prompt_tokens_details": {"cached_tokens": 30}}
        return SimpleNamespace(status_code=200, headers={"x-request-id": f"req-{page.page}"},
                               parse=lambda: SimpleNamespace(model_dump=lambda: body))

    client.root_client.chat.completions.with_raw_response.create = create
    return client


def capture_calls(monkeypatch, detector, *, detailed=False, finishes=None, content=None):
    requests = []
    def build(**kwargs):
        number = detector.events[-1][1]
        return wire_llm(sol_page(number, detailed), detector.events, requests,
                        finish=(finishes or {}).get(number, "stop"), content=content)
    monkeypatch.setattr(parse, "_build_llm", build)
    return requests


@pytest.mark.parametrize("detailed", [False, True])
def test_active_graph_reconciles_before_json_annotations_crops_and_chat(tmp_path, monkeypatch, detailed):
    source = tmp_path / "source.png"
    Image.new("RGB", (100, 100), "white").save(source)
    detector = FakeLayoutRuntime(regions={1: regions()})
    monkeypatch.setattr(parse, "get_layout_runtime", lambda: detector)
    requests = capture_calls(monkeypatch, detector, detailed=detailed)
    state = graph.run_graph(str(source), output_dir=tmp_path / "out", detailed_layout=detailed)
    assert state["status"] == "parsed"
    assert detector.events == [("prepare",), ("v3", 1), ("sol", 1)]
    assert len(requests) == 1
    request = requests[0]
    original_payload = preprocess_pages(source)[0]
    parts = request["messages"][0]["content"]
    assert parts[1]["image_url"]["url"] == "data:image/png;base64," + original_payload["base64"]
    with Image.open(io.BytesIO(base64.b64decode(original_payload["base64"]))) as image:
        assert detector.images[1] == (image.size, image.tobytes())
    hints = json.loads(parts[0]["text"].split("<given_layout>\n")[1].split("\n</given_layout>")[0])
    assert [r["id"] for r in hints["regions"]] == ["r002", "r003", "r001", "r000"]
    assert hints["regions"][0]["bbox"] == [.11, .1, .51, .2]
    schema = ParsePage if detailed else LegacyParsePage
    assert request["response_format"]["json_schema"]["schema"] == schema.model_json_schema()
    assert request["response_format"]["json_schema"]["strict"] is True
    result = state["parse_result"]
    assert [b.type for b in result.pages[0].blocks] == ["heading", "table", "figure", "list", "text"]
    assert result.pages[0].blocks[3] == sol_page(detailed=detailed).blocks[3]
    assert result.layout_metadata[0].reconciliation.decisions[3].reasons == ("role_disagreement",)
    originals = {b.id: b for b in sol_page(detailed=detailed).blocks}
    for block in result.pages[0].blocks:
        assert block.model_dump(exclude={"bbox"}) == originals[block.id].model_dump(exclude={"bbox"})
    assert result.pages[0].blocks[0].bbox.xyxy == (.11, .1, .51, .2)
    saved = ParseResult.model_validate_json(Path(state["parse_json_path"]).read_text(encoding="utf-8"))
    assert saved == result
    assert len(saved.layout_metadata) == 1 and saved.layout_metadata[0].reconciliation is not None
    assert saved.layout_metadata[0].layout.regions[0].polygon_px == regions()[0].polygon_px
    with Image.open(state["annotated_page_paths"][0]) as annotated:
        assert annotated.getpixel((60, 65)) == (220, 30, 30)
    crop_path, = (tmp_path / "out" / "images").glob("*_figure_002.png")
    with Image.open(crop_path) as crop:
        assert crop.size == (30, 30)
    assert "Exact Heading" in Path(state["markdown_path"]).read_text(encoding="utf-8")
    assert "Visible outside regions" in document_pages(result)[1]
    assert usage.totals(state["token_usage"])["input_tokens"] == 100


def test_selected_range_and_same_capped_image_without_raster_profile_changes(tmp_path, monkeypatch):
    source = tmp_path / "large.png"
    Image.new("RGB", (2000, 1000), "blue").save(source)
    detector = FakeLayoutRuntime()
    requests = capture_calls(monkeypatch, detector)
    result = parse.parse_document(source, layout_runtime=detector, save_json=False)
    assert (PDF_DPI, MAX_LONG_EDGE) == (200, 1600)
    assert detector.images[1][0] == (1600, 800)
    assert (result.pages[0].width_px, result.pages[0].height_px) == (1600, 800)
    assert '"regions":[]' in requests[0]["messages"][0]["content"][0]["text"]
    assert result.layout_metadata[0].layout.regions == ()


def test_page_failure_uses_sol_and_preserves_later_pages_context_progress_and_filtering(monkeypatch, tmp_path):
    data = [payload(n, color=color) for n, color in zip(range(2, 6), ("red", "green", "blue", "white"))]
    monkeypatch.setattr(parse, "preprocess_pages", lambda *a, **k: data)
    detector = FakeLayoutRuntime(failures={3: LayoutInferenceError("inference_failed")})
    requests = capture_calls(monkeypatch, detector, finishes={5: "content_filter"})
    entries, progress = [], []
    result = parse.parse_document("unused", start_page=2, end_page=5, layout_runtime=detector,
                                  usage_entries=entries, on_progress=progress.append, output_dir=tmp_path)
    assert detector.events == [("prepare",), ("v3", 2), ("sol", 2), ("v3", 3), ("sol", 3),
                               ("v3", 4), ("sol", 4), ("v3", 5), ("sol", 5)]
    assert [p.page for p in result.pages] == [2, 3, 4]
    assert result.pages[1] == sol_page(3)
    assert result.page_diagnostics[1].layout_fallback
    assert [d.outcome for d in result.page_diagnostics] == ["parsed", "parsed", "parsed", "content_filtered"]
    assert result.page_diagnostics[1].layout_stage == "inference"
    assert result.page_diagnostics[3].filters[0].filtered
    assert result.page_diagnostics[3].request_id == "req-5"
    assert result.content_filtered_pages == [5] and len(entries) == 4
    assert [e["phase"] for e in progress[:2]] == ["layout_preparing", "layout_ready"]
    assert [e["completed"] for e in progress if e["phase"] == "page_complete"] == [1, 2, 3, 4]
    assert {k: progress[-1][k] for k in ("completed", "total", "successful", "failed")} == dict(completed=4, total=4, successful=3, failed=1)
    assert all(d.layout_device == "cpu" and 0 <= d.layout_seconds <= d.page_seconds for d in result.page_diagnostics)
    assert "Exact Heading" in requests[1]["messages"][0]["content"][0]["text"].split("<preceding_page_context>")[1]
    assert [m.layout.page for m in result.layout_metadata] == [2, 4, 5]
    assert result.layout_metadata[-1].reconciliation is None
    assert set(document_pages(result)) == {2, 3, 4}
    assert ParseResult.model_validate_json((tmp_path / "synthetic.json").read_text(encoding="utf-8")) == result


@pytest.mark.parametrize("error,code", [
    (LayoutModelUnavailable("dependencies_unavailable"), "dependencies_unavailable"),
    (LayoutModelUnavailable("devices_failed", attempted_devices=("cuda", "cpu")), "devices_failed"),
    (ConfigError("private value"), "invalid_configuration"),
    (RuntimeError("private native failure"), "unexpected_layout_error"),
])
def test_initialization_failure_uses_sol_without_retrying_v3(monkeypatch, tmp_path, error, code):
    closed = []
    def pages(*args, **kwargs):
        try:
            yield payload(2)
            yield payload(3)
            yield payload(4)
        finally:
            closed.append(True)
    monkeypatch.setattr(parse, "preprocess_pages", pages)
    detector = FakeLayoutRuntime(initialization_error=error)
    requests = []
    monkeypatch.setattr(parse, "_build_llm", lambda **k: wire_llm(sol_page(2 + len(requests)), [], requests))
    entries, progress = [], []
    result = parse.parse_document("unused", start_page=2, end_page=4, layout_runtime=detector,
                                  usage_entries=entries, on_progress=progress.append, output_dir=tmp_path)
    assert len(result.pages) == len(entries) == len(requests) == 3 and not result.layout_metadata
    assert all(p == sol_page(p.page) for p in result.pages)
    assert detector.events == [("prepare",)] and closed == [True]
    assert [d.page for d in result.page_diagnostics] == [2, 3, 4]
    assert all(d.outcome == "parsed" and d.layout_fallback and d.layout_code == code for d in result.page_diagnostics)
    assert "private" not in result.model_dump_json()
    assert {k: progress[-1][k] for k in ("completed", "total", "successful", "failed")} == dict(completed=3, total=3, successful=3, failed=0)
    assert not any(e["phase"] == "layout_ready" for e in progress)
    assert progress[-1]["matches"] is None and progress[-1]["device"] is None
    assert (tmp_path / "synthetic.json").exists()


def test_graph_surfaces_initialization_remediation_without_gui_changes(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    Image.new("RGB", (100, 100), "white").save(source)
    detector = FakeLayoutRuntime(initialization_error=LayoutModelUnavailable("dependencies_unavailable"))
    monkeypatch.setattr(parse, "get_layout_runtime", lambda: detector)
    monkeypatch.setattr(parse, "_build_llm", lambda **k: wire_llm(sol_page(), [], []))
    state = graph.run_graph(str(source), output_dir=tmp_path / "out")
    assert state["status"] == "parsed" and state["parse_result"].page_diagnostics[0].layout_fallback
    assert state["parse_json_path"] and state["markdown"]


def test_graph_keeps_partial_exports_after_a_layout_page_failure(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    image = Image.new("RGB", (100, 100), "white")
    image.save(source, save_all=True, append_images=[image, image])
    detector = FakeLayoutRuntime(failures={2: LayoutInferenceError("inference_failed")})
    monkeypatch.setattr(parse, "get_layout_runtime", lambda: detector)
    requests = capture_calls(monkeypatch, detector)
    state = graph.run_graph(str(source), output_dir=tmp_path / "out")
    assert state["status"] == "parsed" and len(requests) == 3
    assert [p.page for p in state["parse_result"].pages] == [1, 2, 3]
    assert state["parse_result"].page_diagnostics[1].layout_code == "inference_failed"
    assert Path(state["markdown_path"]).exists() and len(state["annotated_page_paths"]) == 3
    # Sol boxes remain available to annotations and chat on the fallback page.
    with Image.open(state["annotated_page_paths"][1]) as failed_page:
        assert failed_page.convert("RGB").getextrema() != ((255, 255),) * 3
    assert set(document_pages(state["parse_result"])) == {1, 2, 3}


def test_template_failure_retains_analysis_without_calling_sol(monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("private template value")
    monkeypatch.setattr(parse, "render_prompt", fail)
    monkeypatch.setattr(parse, "_build_llm", lambda **k: pytest.fail("Sol constructed"))
    data, diagnostics, artifacts = payload(), [], []
    with pytest.raises(ExtractionCallError):
        parse.parse_page(data["base64"], data["mime"], 1, 100, 100,
                         layout_runtime=FakeLayoutRuntime(), diagnostics=diagnostics, layout_metadata=artifacts)
    assert diagnostics[0].layout_stage == "prompt" and diagnostics[0].outcome == "layout_failed"
    assert len(artifacts) == 1 and artifacts[0].reconciliation is None


@pytest.mark.parametrize("detailed", [False, True])
def test_v3_fallback_preserves_every_sol_field_and_full_image(monkeypatch, detailed):
    detector = FakeLayoutRuntime(failures={1: LayoutInferenceError("inference_failed")})
    requests = capture_calls(monkeypatch, detector, detailed=detailed)
    data, diagnostics = payload(), []
    result = parse.parse_page(data["base64"], data["mime"], 1, 100, 100,
                              layout_runtime=detector, detailed_layout=detailed, diagnostics=diagnostics)
    assert result == sol_page(detailed=detailed)
    message = requests[0]["messages"][0]["content"]
    assert '<given_layout>\n{"regions":[]}\n</given_layout>' in message[0]["text"]
    assert message[1]["image_url"]["url"].endswith(data["base64"])
    assert diagnostics[-1].outcome == "parsed" and diagnostics[-1].layout_fallback


@pytest.mark.parametrize("finish,content,outcome", [
    ("content_filter", None, "content_filtered"),
    ("stop", '{"not_a_page":true}', "invalid_response"),
])
def test_v3_fallback_does_not_mask_sol_failure_or_paid_usage(monkeypatch, finish, content, outcome):
    detector = FakeLayoutRuntime(failures={1: LayoutInferenceError("inference_failed")})
    capture_calls(monkeypatch, detector, finishes={1: finish}, content=content)
    monkeypatch.setattr(parse, "preprocess_pages", lambda *a, **k: [payload()])
    entries = []
    result = parse.parse_document("unused", end_page=1, layout_runtime=detector, save_json=False, usage_entries=entries)
    assert not result.pages and len(entries) == 1
    diagnostic = result.page_diagnostics[0]
    assert diagnostic.outcome == outcome and diagnostic.layout_fallback
    assert diagnostic.request_id == "req-1" and diagnostic.input_tokens == 100
    assert result.content_filtered_pages == ([1] if finish == "content_filter" else [])


def test_preflight_failure_passed_to_graph_does_not_retry_initialization(monkeypatch, tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (100, 100), "white").save(source)
    failure = layout_failure_diagnostic(LayoutModelUnavailable("devices_failed"), page=1,
                                        stage="initialization", requested_model="gpt-6-sol")
    monkeypatch.setattr(parse, "get_layout_runtime", lambda: pytest.fail("V3 retried"))
    requests = []
    monkeypatch.setattr(parse, "_build_llm", lambda **k: wire_llm(sol_page(), [], requests))
    state = graph.run_graph(str(source), output_dir=tmp_path / "out", layout_initialization_failure=failure)
    assert state["status"] == "parsed" and len(requests) == 1
    assert state["parse_result"].page_diagnostics[0].layout_fallback


def test_cli_fallback_is_visible_and_successful(monkeypatch, tmp_path, capsys):
    from src import cli
    source = tmp_path / "source.png"
    Image.new("RGB", (100, 100), "white").save(source)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    detector = FakeLayoutRuntime(initialization_error=LayoutModelUnavailable("devices_failed"))
    monkeypatch.setattr(parse, "get_layout_runtime", lambda: detector)
    monkeypatch.setattr(parse, "_build_llm", lambda **k: wire_llm(sol_page(), [], []))
    assert cli.main([str(source), str(tmp_path / "out"), "--json"]) == 0
    stdout, stderr = capsys.readouterr()
    assert "using Sol blocks" in stderr and "test-only" not in stderr
    saved = ParseResult.model_validate_json(Path(stdout.strip()).read_text(encoding="utf-8"))
    assert saved.pages[0] == sol_page() and saved.page_diagnostics[0].layout_fallback


def test_document_table_budget_preserves_paid_diagnostics_and_analysis(monkeypatch):
    monkeypatch.setattr(parse, "preprocess_pages", lambda *a, **k: [payload(1), payload(2)])
    monkeypatch.setattr(parse, "max_table_cells", lambda: 4)
    detector = FakeLayoutRuntime(regions={1: regions(), 2: regions()})
    capture_calls(monkeypatch, detector)
    entries = []
    result = parse.parse_document("unused", layout_runtime=detector, usage_entries=entries, save_json=False)
    assert [p.page for p in result.pages] == [1]
    assert result.page_diagnostics[1].outcome == "invalid_response"
    assert result.page_diagnostics[1].request_id == "req-2"
    assert result.page_diagnostics[1].input_tokens == 100 and len(entries) == 2
    assert result.layout_metadata[0].reconciliation is not None
    assert result.layout_metadata[1].reconciliation is None


@pytest.mark.parametrize("failure", ["conversion", "prompt", "image", "identity"])
def test_direct_page_falls_back_except_for_invalid_image(monkeypatch, failure):
    data = payload()
    detector = FakeLayoutRuntime()
    if failure == "conversion":
        detector.regions[1] = [replace(region(), score=float("nan"))]
    elif failure == "prompt":
        monkeypatch.setattr("src.layout_reconcile.GIVEN_LAYOUT_MAX_BYTES", 1)
    elif failure == "image":
        data["base64"] = "not valid PNG"
    else:
        detector.predict = lambda image, page_number: runtime(page=2)
    monkeypatch.setattr(parse, "get_layout_runtime", lambda: detector)
    requests = []
    monkeypatch.setattr(parse, "_build_llm", lambda **k: wire_llm(sol_page(), [], requests))
    diagnostics, artifacts = [], []
    if failure == "image":
        with pytest.raises(ExtractionCallError):
            parse.parse_page(data["base64"], data["mime"], 1, 100, 100, diagnostics=diagnostics)
        assert not requests
        return
    else:
        result = parse.parse_page(data["base64"], data["mime"], 1, 100, 100,
                         diagnostics=diagnostics, layout_metadata=artifacts)
    assert result == sol_page() and len(requests) == 1
    assert diagnostics[-1].outcome == "parsed" and diagnostics[-1].layout_fallback
    assert diagnostics[-1].layout_stage == {"image": "inference", "identity": "conversion"}.get(failure, failure)


def test_reconciliation_failure_retains_sol_page_and_paid_usage(monkeypatch):
    monkeypatch.setattr(parse, "preprocess_pages", lambda *a, **k: [payload(1), payload(2)])
    detector = FakeLayoutRuntime()
    requests = capture_calls(monkeypatch, detector)
    original = parse.reconcile_page
    def reconcile(page, layout):
        if page.page == 1:
            raise RuntimeError("private source text")
        return original(page, layout)
    monkeypatch.setattr(parse, "reconcile_page", reconcile)
    entries = []
    result = parse.parse_document("unused", layout_runtime=detector, usage_entries=entries, save_json=False)
    assert [p.page for p in result.pages] == [1, 2] and len(requests) == 2
    assert result.pages[0] == sol_page()
    failed = result.page_diagnostics[0]
    assert (failed.outcome, failed.layout_stage, failed.request_id) == ("parsed", "reconciliation", "req-1")
    assert failed.layout_fallback
    assert failed.input_tokens == 100 and failed.output_tokens == 20 and failed.usage_known
    assert usage.totals(entries)["input_tokens"] == 200
    assert "private" not in result.model_dump_json() and result.layout_metadata[0].reconciliation is None


def test_invalid_sol_response_keeps_analysis_and_paid_diagnostic(monkeypatch):
    monkeypatch.setattr(parse, "preprocess_pages", lambda *a, **k: [payload()])
    monkeypatch.setattr(parse, "inspect_source", lambda *a: {"pages": 1})
    detector = FakeLayoutRuntime()
    capture_calls(monkeypatch, detector, content='{"not_a_page":true}')
    result = parse.parse_document("unused", layout_runtime=detector, save_json=False)
    assert result.pages == [] and result.page_diagnostics[0].outcome == "invalid_response"
    assert result.page_diagnostics[0].input_tokens == 100
    assert result.layout_metadata[0].reconciliation is None


def test_prompt_projection_is_bounded_complete_and_keeps_only_useful_polygons(monkeypatch):
    triangle = region(polygon=((10, 10), (50, 10), (50, 50)))
    layout = convert_layout(runtime(region(order=142), triangle))
    original = layout.model_dump()
    hints = json.loads(given_layout_json(layout))
    assert hints["regions"][0]["id"] == "r001" and len(hints["regions"][0]["polygon_points"]) == 3
    assert "polygon_points" not in hints["regions"][1]
    assert layout.model_dump() == original
    # At the boxes-only budget, omit the triangle without dropping either region.
    no_polygons = deepcopy(hints)
    del no_polygons["regions"][0]["polygon_points"]
    limit = len(json.dumps(no_polygons, separators=(",", ":")))
    monkeypatch.setattr("src.layout_reconcile.GIVEN_LAYOUT_MAX_BYTES", limit)
    projected = json.loads(given_layout_json(layout))
    assert projected == no_polygons


def test_dense_layout_and_tiny_boxes_fit_without_geometry_mutation():
    small = region((10.00000001, 10.00000001, 10.00000002, 10.00000002),
                   polygon=((10, 10), (11, 10), (11, 11), (10, 11)))
    layout = convert_layout(runtime(*[region(label="reference_content", order=i) for i in range(300)]))
    text = given_layout_json(layout)
    assert len(text.encode()) <= 65536 and len(json.loads(text)["regions"]) == 300
    box = json.loads(given_layout_json(convert_layout(runtime(small))))["regions"][0]["bbox"]
    assert box[0] < box[2] and box[1] < box[3]
    with pytest.raises(ValueError, match="layout_prompt_too_large"):
        given_layout_json(convert_layout(runtime(*[region(order=0) for _ in range(301)])))


def test_legacy_json_loading_and_strict_schemas_remain_unchanged():
    baseline = {"ParsePage": "87fb833659364832061e590587c68d1c32bac49795eac8ea252bf4d9c433e328",
                "LegacyParsePage": "cb2fe39ca45e4d8f1c98df5ebf0ec6db516a761648d4751be07afbc2adeb8229"}
    for schema in (ParsePage, LegacyParsePage):
        assert hashlib.sha256(json.dumps(schema.model_json_schema(), sort_keys=True).encode()).hexdigest() == baseline[schema.__name__]
    for version in (None, 2):
        data = dict(doc_sha="old", pages=[sol_page().model_dump()])
        if version is not None:
            data["schema_version"] = version
        else:
            for block in data["pages"][0]["blocks"]:
                block.pop("structure")
        before = deepcopy(data)
        assert ParseResult.model_validate(data).layout_metadata == []
        assert data == before


@pytest.mark.parametrize("corruption", ["nan", "bbox", "polygon", "region", "decision", "duplicate", "dimension", "unknown"])
def test_saved_metadata_is_validated_not_arbitrary_json(monkeypatch, corruption):
    detector = FakeLayoutRuntime(regions={1: regions()})
    capture_calls(monkeypatch, detector)
    artifacts = []
    source = payload()
    parsed = parse.parse_page(source["base64"], source["mime"], 1, 100, 100,
                              layout_runtime=detector, layout_metadata=artifacts)
    data = ParseResult(doc_sha="test", pages=[parsed], layout_metadata=artifacts).model_dump(mode="json")
    entry = data["layout_metadata"][0]
    if corruption == "nan":
        entry["layout"]["regions"][0]["score"] = float("nan")
    elif corruption == "bbox":
        entry["layout"]["regions"][0]["bbox"]["xyxy"][0] = -1
    elif corruption == "polygon":
        entry["layout"]["regions"][0]["polygon"] = [[0, 0], [0, 0], [0, 0]]
    elif corruption == "region":
        entry["layout"]["regions"][1]["index"] = 0
    elif corruption == "decision":
        entry["reconciliation"]["decisions"][0]["region_index"] = 99
    elif corruption == "duplicate":
        data["layout_metadata"].append(deepcopy(entry))
    elif corruption == "dimension":
        entry["layout"]["width_px"] = 200
    else:
        entry["unvalidated_extra"] = "not allowed"
    with pytest.raises(ValidationError):
        ParseResult.model_validate(data)


def test_local_failure_codes_cannot_leak_native_text():
    error = RuntimeError("private source and secret")
    error.code = "private secret"
    diagnostic = layout_failure_diagnostic(error, page=1, stage="inference", requested_model="gpt-6-sol")
    assert diagnostic.layout_code == "unexpected_layout_error"
    assert "private" not in diagnostic.model_dump_json() + layout_failure_summary(diagnostic)


def test_cli_reports_safe_device_timings_and_matches(tmp_path, monkeypatch, capsys):
    from src import cli
    source = tmp_path / "source.png"
    Image.new("RGB", (100, 100), "white").save(source)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    detector = FakeLayoutRuntime(regions={1: regions()})
    monkeypatch.setattr(parse, "get_layout_runtime", lambda: detector)
    capture_calls(monkeypatch, detector)
    assert cli.main([str(source), str(tmp_path / "out"), "--json"]) == 0
    stdout, stderr = capsys.readouterr()
    assert stdout.strip().endswith(".json") and "PP-DocLayoutV3" not in stdout
    assert "Preparing PP-DocLayoutV3" in stderr and "ready: CPU" in stderr
    assert "page 1: parsed" in stderr and "matches=3" in stderr
    assert "layout_seconds=" in stderr and "page_seconds=" in stderr
    assert "Exact Heading" not in stderr and str(source) not in stderr and "test-only" not in stderr
    saved = ParseResult.model_validate_json(Path(stdout.strip()).read_text(encoding="utf-8"))
    assert saved.page_diagnostics[0].layout_device == "cpu"
    from src.layout_reconcile import layout_match_counts
    assert layout_match_counts(saved.layout_metadata[0]) == dict(
        regions=4, matches=3, unmatched_blocks=2, unmatched_regions=1, review_blocks=2)


def test_graph_unexpected_exception_does_not_leak_raw_text(tmp_path, monkeypatch, capsys):
    source = tmp_path / "private-document.png"
    Image.new("RGB", (100, 100)).save(source)
    def fail(*a, **k):
        raise RuntimeError("private provider message C:/secret-model sk-private")
    monkeypatch.setattr(graph, "parse_document", fail)
    result = graph.run_graph(str(source), output_dir=tmp_path / "out")
    captured = capsys.readouterr()
    assert result["status"] == "parse_failed"
    text = captured.out + captured.err + result["parse_error"]
    assert "private" not in text and "secret-model" not in text


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_diagnostic_timings_are_validated(value):
    from src.diagnostics import PageDiagnostic
    with pytest.raises(ValidationError):
        PageDiagnostic(layout_seconds=value)


def test_evaluator_current_template_uses_same_gate_and_keeps_image(monkeypatch):
    from scripts import evaluate_prompts
    from src.prompts import PROMPT_DIR
    from tests.test_diagnostics import call_response, completion
    detector = FakeLayoutRuntime()
    monkeypatch.setattr(parse, "get_layout_runtime", lambda: detector)
    llm, requests = call_response(completion())
    monkeypatch.setattr(evaluate_prompts, "_build_llm", lambda: llm)
    data = payload()
    prompt = (PROMPT_DIR / "parse-page.md").read_text(encoding="utf-8")
    try:
        outcome = evaluate_prompts.run_page(data, prompt)
        assert outcome["status"] == "parsed" and len(requests) == 1
        assert outcome["layout_metadata"][0]["reconciliation"] is not None
        assert requests[0]["messages"][0]["content"][1]["image_url"]["url"].endswith(data["base64"])
        detector.failures[1] = LayoutInferenceError("inference_failed")
        failed = evaluate_prompts.run_page(data, prompt)
        assert failed["status"] == "layout_failed" and len(requests) == 1
    finally:
        llm.root_client.close()
