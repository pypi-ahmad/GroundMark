"""Filename families, collision handling, and adjacent legacy figure loading."""
from datetime import UTC, datetime, timedelta, timezone
from urllib.parse import unquote
import re

import pytest
from PIL import Image

from src.output_names import reserve_basename, source_stem
from src.markdown import render_and_save
from tests.test_layout_structure import block, document


@pytest.mark.parametrize("source, expected", [
    (r"C:\inbox\invoice.pdf", "invoice"),
    ("/inbox/日本語 report.v2.pdf", "日本語 report.v2"),
    ('bad<>:\x01?.pdf', "bad_____"),
    ("CON.pdf", "_CON"),
    ("lpt1.txt", "_lpt1"),
    (".pdf", ".pdf"),
    ("...", "document"),
    (" x. .pdf", "x"),
    ("a" * 150 + ".pdf", "a" * 120),
])
def test_source_stem(source, expected):
    assert source_stem(source) == expected


def test_utc_reservation_collision_and_cleanup(tmp_path):
    start = datetime(2026, 9, 23, 15, 30, 45, 123456, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    with reserve_basename("invoice.pdf", start, tmp_path) as first:
        assert first == "invoice_20260923_100045Z"
        with reserve_basename("invoice.pdf", start, tmp_path) as concurrent:
            assert concurrent == "invoice_20260923_100045_123456Z"
            (tmp_path / (concurrent + ".md")).write_text("other")
        (tmp_path / (first + ".json")).write_text("original")
    with reserve_basename("invoice.pdf", start, tmp_path) as third:
        assert third == "invoice_20260923_100045_123457Z"
    assert (tmp_path / (first + ".json")).read_text() == "original"
    assert not list(tmp_path.glob(".groundmark-*"))
    with pytest.raises(RuntimeError), reserve_basename("failed.pdf", start, tmp_path):
        raise RuntimeError("export interrupted")
    assert not list(tmp_path.glob(".groundmark-*"))


@pytest.mark.parametrize("relative", ["annotated/invoice_20260923_100045Z.pdf", "INVOICE_20260923_100045Z.md",
    "annotated/invoice_20260923_100045Z", "images/invoice_20260923_100045Z_page_001_figure_000.png"])
def test_collision_with_annotation_or_image_only(tmp_path, relative):
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    with reserve_basename("invoice.pdf", datetime(2026, 9, 23, 10, 0, 45, tzinfo=UTC), tmp_path) as name:
        assert name == "invoice_20260923_100045_000000Z"


@pytest.mark.parametrize("legacy", [False, True])
def test_json_rerender_resolves_figure_paths_with_special_characters(tmp_path, legacy):
    basename = "日本語 report (1) [draft]_20260923_100045Z"
    result = document(block("figure", "caption"))
    path = tmp_path / (basename + ".json")
    path.write_text(result.model_dump_json(), encoding="utf-8")
    image_name = ("" if legacy else basename + "_") + "page_001_figure_000.png"
    (tmp_path / "images").mkdir()
    Image.new("RGB", (10, 10)).save(tmp_path / "images" / image_name)
    rendered = render_and_save(path)
    assert rendered.stem == basename
    link = re.search(r"!\[Figure\]\(([^)]+)\)", rendered.read_text(encoding="utf-8"))[1]
    assert unquote(link) == "images/" + image_name
    assert (tmp_path / unquote(link)).is_file()
