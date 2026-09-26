"""Structure contracts and their visible rendering consequences."""
import io
import json
import zipfile

import pytest
from PIL import Image
from pydantic import ValidationError

from src.chat import document_pages
from src.figures import extract_figures, load_figures
from src.layout import BBox, BlockStructure, ListItem, ParseBlock, ParsePage, ParseResult, TableCell
from src.markdown import markdown_bundle, parse_to_html, parse_to_markdown


def block(kind="text", text="source", structure=None, **kwargs):
    return ParseBlock(id="b", type=kind, text=text, bbox=kwargs.pop("bbox", None),
                      conf=None, table=kwargs.pop("table", None), structure=structure, **kwargs)


def document(*blocks):
    return ParseResult(doc_sha="test", pages=[ParsePage(page=1, width_px=100, height_px=100, blocks=list(blocks))])


def structure(**kwargs):
    return BlockStructure(**dict(heading_level=None, list_items=None, table_cells=None) | kwargs)


def test_live_schema_requires_all_fields_and_legacy_load_does_not_change_input():
    schema = ParsePage.model_json_schema()
    for item in [schema, *schema["$defs"].values()]:
        if item.get("type") == "object":
            assert set(item["required"]) == set(item["properties"])
            assert item["additionalProperties"] is False
            assert all("default" not in value for value in item["properties"].values())
    legacy = document(block("table", table=[["first", "value"]])).model_dump()
    del legacy["schema_version"]
    del legacy["pages"][0]["blocks"][0]["structure"]
    before = json.dumps(legacy)
    loaded = ParseResult.model_validate(legacy)
    assert json.dumps(legacy) == before
    assert loaded.schema_version == 2
    assert "<td>first</td>" in parse_to_markdown(loaded)
    assert "<th>" not in parse_to_html(loaded)
    with pytest.raises(ValidationError):
        ParsePage.model_validate(legacy["pages"][0])


def test_headings_lists_and_lines_preserve_structure_and_source():
    items = [ListItem(text="First", marker="a)", depth=0, checked=None),
             ListItem(text="Nested\nline", marker="☑", depth=1, checked=True),
             ListItem(text="Second", marker="b)", depth=0, checked=None)]
    result = document(block("heading", "Section\nSubtitle", structure(heading_level=3)),
                      block("list", "a) First\n☑ Nested\nline\nb) Second", structure(list_items=items)),
                      block(text="Address\nSecond line"))
    before = result.model_dump_json()
    md, rendered = parse_to_markdown(result), parse_to_html(result)
    assert "### Section<br>Subtitle" in md
    assert "<h3>Section<br>Subtitle</h3>" in rendered
    for output in (md, rendered):
        assert "<li>a) First<ul" in output
        assert "☑ Nested<br>line</li></ul></li><li>b) Second" in output
        assert "Address<br>Second line" in output
    assert result.model_dump_json() == before


def test_merged_header_and_headerless_tables():
    cells = [TableCell(row=0, column=0, rowspan=1, colspan=2, is_header=True),
             TableCell(row=1, column=0, rowspan=1, colspan=1, is_header=False),
             TableCell(row=1, column=1, rowspan=1, colspan=1, is_header=False)]
    result = document(block("table", table=[["Title", ""], ["A", "B"]], structure=structure(table_cells=cells)))
    for output in (parse_to_markdown(result), parse_to_html(result)):
        assert '<th colspan="2">Title</th>' in output
        assert "<td>A</td><td>B</td>" in output
    result.pages[0].blocks[0] = block("table", table=[["Drug", "10"]], structure=structure(table_cells=[
        TableCell(row=0, column=c, rowspan=1, colspan=1, is_header=False) for c in range(2)]))
    assert "<th" not in parse_to_markdown(result)


@pytest.mark.parametrize("cells", [
    [dict(row=0, column=0, rowspan=3, colspan=1, is_header=False)],
    [dict(row=0, column=0, rowspan=1, colspan=1, is_header=False)] * 2,
    [dict(row=0, column=0, rowspan=1, colspan=2, is_header=False)],
    [],
])
def test_invalid_table_metadata_is_rejected(cells):
    with pytest.raises(ValidationError):
        block("table", table=[["A", "B"]], structure=structure(table_cells=cells))


def test_invalid_nesting_and_heading_level_are_rejected():
    with pytest.raises(ValidationError):
        block("list", structure=structure(list_items=[dict(text="x", marker="-", depth=1, checked=None)]))
    with pytest.raises(ValidationError):
        structure(heading_level=7)


def test_clean_only_hides_running_furniture_and_chat_keeps_all_text():
    result = document(block("page_header", "FAX"), block("heading", "Clinical title"),
                      block("marginalia", "stamp"), block("page_footer", "page 1"))
    for render in (parse_to_markdown, parse_to_html):
        clean = render(result, view="clean")
        assert "FAX" not in clean and "page 1" not in clean
        assert "Clinical title" in clean and "stamp" in clean
        assert "FAX" in render(result)
    assert "FAX" in document_pages(result)[1]
    assert "page 1" in document_pages(result)[1]


def test_literal_markup_never_becomes_executable_or_formatting():
    result = document(block(text='<img src="https://example.invalid/a" onerror="bad"> **literal** [link](javascript:bad) $20'))
    md = parse_to_markdown(result)
    assert '<img' not in md and r'\*\*literal\*\*' in md and r'\[link\]' in md
    assert '&lt;img' in md and r'\$20' in md
    assert '<img' not in parse_to_html(result)
    assert '**literal**' in document_pages(result)[1]
    assert r"1\. Literal numbering" in parse_to_markdown(document(block(text="1. Literal numbering")))
    assert r"\-\-\-" in parse_to_markdown(document(block(text="---")))


def test_list_labels_tail_and_unrepresented_text_are_not_lost():
    items = [ListItem(text="Outpatient", marker="☑", depth=0, checked=True),
             ListItem(text="Home", marker="☐", depth=0, checked=False)]
    result = document(block("list", "Type of service: ☑ Outpatient ☐ Home\nOriginal note", structure(list_items=items)))
    for render in (parse_to_markdown, parse_to_html):
        output = render(result)
        assert "Type of service:" in output and "Original note" in output
        assert output.index("Type of service:") < output.index("Outpatient") < output.index("Original note")
    assert "- [x] Outpatient" in parse_to_markdown(result)
    result.pages[0].blocks[0].text = "Type of service: ☑ Outpatient important note ☐ Home"
    for render in (parse_to_markdown, parse_to_html):
        assert "important note" in render(result)


def test_plain_bullets_numbering_and_missing_item_source():
    items = [ListItem(text="First", marker="3.", depth=0, checked=None),
             ListItem(text="Child", marker="•", depth=1, checked=None),
             ListItem(text="Second", marker="4.", depth=0, checked=None)]
    result = document(block("list", "3. First\n• Child\n4. Second", structure(list_items=items)))
    assert parse_to_markdown(result) == "3. First\n    - Child\n4. Second\n"
    result.pages[0].blocks[0].text = "Source without the requested items"
    assert parse_to_markdown(result) == "Source without the requested items\n"


def test_default_extraction_uses_original_contract_and_detailed_is_opt_in(monkeypatch, fake_layout_runtime):
    from src import parse
    from src.layout import LegacyParsePage
    calls = []
    monkeypatch.setattr(parse, "_build_llm", lambda **kw: object())
    def invoke(llm, schema, messages, **kwargs):
        calls.append((schema, messages[0].content[0]["text"]))
        return schema(page=1, width_px=100, height_px=100, blocks=[])
    monkeypatch.setattr(parse, "_invoke_structured", invoke)
    from tests.fake_layout import payload
    encoded = payload()["base64"]
    parse.parse_page(encoded, "image/png", 1, 100, 100)
    parse.parse_page(encoded, "image/png", 1, 100, 100, detailed_layout=True)
    assert calls[0][0] is LegacyParsePage and "table_cells" not in calls[0][1]
    assert calls[1][0] is ParsePage and "table_cells" in calls[1][1]


def test_figure_crop_bundle_and_fallback(tmp_path):
    import hashlib
    source = tmp_path / "source.png"
    Image.new("RGB", (100, 80), "red").save(source)
    result = document(block("figure", "Caption", bbox=BBox(page=1, xyxy=(0.1, 0.25, 0.6, 0.75))),
                      block("figure", "Missing"))
    result.doc_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    result.pages[0].blocks[0].id = "../../outside"
    figures, warnings = extract_figures(source, result, tmp_path / "run")
    name = "page_001_figure_000.png"
    assert list(figures) == [name] and len(warnings) == 1
    with Image.open(io.BytesIO(figures[name])) as crop:
        assert crop.size == (50, 40)
    assert load_figures(result, tmp_path / "run") == figures
    assert "data:image/png;base64," in parse_to_html(result, figures=figures)
    md = parse_to_markdown(result, figures=figures)
    assert f"images/{name}" in md and "[figure] Missing" in md
    with zipfile.ZipFile(io.BytesIO(markdown_bundle(result, figures=figures))) as archive:
        assert archive.read("document.md").decode() == md
        assert archive.read(f"images/{name}") == figures[name]
    result.doc_sha = "different"
    assert extract_figures(source, result, tmp_path / "other")[0] == {}
