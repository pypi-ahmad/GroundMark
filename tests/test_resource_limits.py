"""Small, offline regression checks for allocation and packaging boundaries."""

import hashlib
import pytest
from PIL import Image
from pydantic import ValidationError

from src import figures, parse
from src.layout import BBox, LegacyBlock, ParseBlock, ParseResult
from src.markdown import _table_rows, parse_to_html, render_and_save
from tests.test_layout_structure import block, document


@pytest.mark.parametrize("model", [LegacyBlock, ParseBlock])
def test_table_budget_is_checked_before_padding(monkeypatch, model):
    monkeypatch.setenv("GROUNDMARK_MAX_TABLE_CELLS", "4")
    data = dict(id="table", type="table", text="", bbox=None, conf=None,
                table=[["A", "B", "C"], ["D"]])
    if model is ParseBlock:
        data["structure"] = None
    with pytest.raises(ValidationError, match="MAX_TABLE_CELLS"):
        model(**data)
    with pytest.raises(ValueError, match="MAX_TABLE_CELLS"):
        _table_rows(data["table"])


def test_table_budget_is_shared_across_saved_tables_and_rendering(monkeypatch):
    result = document(block("table", table=[["A", "B"]]), block("table", table=[["C", "D"]]))
    monkeypatch.setenv("GROUNDMARK_MAX_TABLE_CELLS", "3")
    with pytest.raises(ValidationError, match="MAX_TABLE_CELLS"):
        ParseResult.model_validate_json(result.model_dump_json())
    with pytest.raises(ValueError, match="MAX_TABLE_CELLS"):
        parse_to_html(result)


def test_saved_json_size_is_checked_before_reading(tmp_path, monkeypatch):
    source = tmp_path / "document.json"
    source.write_text(document().model_dump_json())
    monkeypatch.setattr("src.markdown.max_source_bytes", lambda: 8)
    with pytest.raises(ValueError, match="MAX_SOURCE_MIB"):
        render_and_save(source)
    assert not source.with_suffix(".md").exists()


def figure_document(tmp_path):
    source = tmp_path / "source.png"
    with Image.new("RGB", (20, 20), "red") as image:
        image.save(source)
    result = document(*(block("figure", bbox=BBox(page=1, xyxy=(0, 0, 1, 1))) for _ in range(2)))
    result.doc_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    return source, result


def test_figure_count_is_bounded_for_extraction_and_saved_files(tmp_path, monkeypatch):
    source, result = figure_document(tmp_path)
    output = tmp_path / "output"
    original, _ = figures.extract_figures(source, result, output)
    assert len(original) == 2
    monkeypatch.setenv("GROUNDMARK_MAX_FIGURES", "1")
    retained, warnings = figures.extract_figures(source, result, tmp_path / "limited")
    assert len(retained) == 1 and "count limit" in warnings[0]
    with pytest.raises(ValueError, match="count or byte limit"):
        figures.load_figures(result, output)


def test_figure_bytes_are_bounded_for_extraction_and_saved_files(tmp_path, monkeypatch):
    source, result = figure_document(tmp_path)
    output = tmp_path / "output"
    original, _ = figures.extract_figures(source, result, output)
    monkeypatch.setattr(figures, "max_figure_bytes", lambda: len(next(iter(original.values()))))
    retained, warnings = figures.extract_figures(source, result, tmp_path / "limited")
    assert len(retained) == 1 and "byte limit" in warnings[0]
    with pytest.raises(ValueError, match="count or byte limit"):
        figures.load_figures(result, output)


def test_parser_keeps_successful_pages_within_document_table_budget(monkeypatch, fake_layout_runtime):
    page = document(block("table", table=[["A", "B"]])).pages[0]
    monkeypatch.setenv("GROUNDMARK_MAX_TABLE_CELLS", "3")
    monkeypatch.setattr(parse, "preprocess_pages", lambda *a, **kw: [
        dict(base64="", mime="image/png", page=n, width=20, height=20, doc_sha256="test")
        for n in (1, 2)])
    monkeypatch.setattr(parse, "parse_page", lambda image, mime, n, *a, **kw: page.model_copy(update={"page": n}))
    result = parse.parse_document("unused", save_json=False)
    assert [p.page for p in result.pages] == [1]
    assert result.page_diagnostics[1].outcome == "invalid_response"


def test_release_manifest_includes_all_prompts_and_rejects_extras():
    from scripts.verify_release_artifacts import _check, _manifest, PROMPTS
    for wheel in (True, False):
        manifest = _manifest(wheel=wheel)
        assert all(any(name.endswith(f"/{prompt}.md") for name in manifest) for prompt in PROMPTS)
        assert _check(list(manifest), wheel=wheel) == manifest
        with pytest.raises(SystemExit, match="manifest mismatch"):
            _check([*manifest, "notes.txt"], wheel=wheel)
        with pytest.raises(SystemExit, match="manifest mismatch"):
            _check([name for name in manifest if not name.endswith("chat-verify.md")], wheel=wheel)
        with pytest.raises(SystemExit, match="duplicate"):
            _check([*manifest, next(iter(manifest))], wheel=wheel)


def test_release_content_must_match_checkout(tmp_path):
    from scripts.verify_release_artifacts import _check_bytes
    path = tmp_path / "prompt.md"
    path.write_bytes(b"expected")
    _check_bytes("prompt.md", b"expected", path)
    with pytest.raises(SystemExit, match="differs from checkout"):
        _check_bytes("prompt.md", b"changed", path)
