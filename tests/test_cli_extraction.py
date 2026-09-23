"""Exercise real preprocessing and exports without model requests."""

import os
import re
from urllib.parse import unquote
from pathlib import Path
import zipfile

import pytest

from src import cli, parse
from src.layout import BBox, ParseBlock, ParsePage


@pytest.fixture
def extraction(tmp_path, monkeypatch):
    from PIL import Image
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setenv("GROUNDMARK_ENV_LOADED", "1")
    source = tmp_path / "source document.png"
    Image.new("RGB", (80, 60), "white").save(source)
    calls = []

    def page(*args, **kwargs):
        calls.append(kwargs)
        return ParsePage(page=args[2], width_px=args[3], height_px=args[4], blocks=[
            ParseBlock(id="figure", type="figure", text="Sample figure", table=None,
                       conf=1, bbox=BBox(page=args[2], xyxy=(0.1, 0.1, 0.8, 0.8)), structure=None),
        ])
    monkeypatch.setattr(parse, "parse_page", page)
    return source, tmp_path / "output folder", calls


@pytest.mark.parametrize("flags,extensions", [
    ([], {".md", ".png"}),
    (["--markdown"], {".md", ".png"}),
    (["--html"], {".html"}),
    (["--json"], {".json"}),
    (["--annotated-pdf"], {".pdf"}),
    (["--annotated-images"], {".png"}),
    (["--markdown-zip"], {".zip"}),
    (["--markdown", "--html"], {".md", ".html", ".png"}),
    (["--all"], {".md", ".html", ".json", ".pdf", ".png", ".zip"}),
])
def test_selected_formats_only(extraction, flags, extensions):
    source, output, calls = extraction
    assert cli.main([str(source), str(output), *flags]) == 0
    files = [p for p in output.rglob("*") if p.is_file()]
    assert {p.suffix for p in files} == extensions
    assert not any(p.name.endswith(".meta.json") for p in files)
    assert len(calls) == 1
    primary = next(p for p in files if p.parent == output or p.suffix == ".pdf" or "_figure_" not in p.name)
    basename = primary.stem.split("_page_")[0]
    assert re.fullmatch(r"source document_\d{8}_\d{6}Z", basename)
    assert all(p.name.startswith(basename) for p in files)
    if ".html" in extensions:
        assert "data:image/png;base64," in next(output.glob("*.html")).read_text()
    if ".zip" in extensions:
        with zipfile.ZipFile(next(output.glob("*.zip"))) as archive:
            assert set(archive.namelist()) == {f"{basename}.md", f"images/{basename}_page_001_figure_000.png"}
            markdown = archive.read(f"{basename}.md").decode()
            link = re.search(r"!\[Figure\]\(([^)]+)\)", markdown)[1]
            assert unquote(link) in archive.namelist()
    assert not (source.parent / "data").exists()


def test_json_skips_presentation(extraction, monkeypatch):
    source, output, _ = extraction
    monkeypatch.setattr("src.export.extract_figures", lambda *a, **k: pytest.fail("Unexpected figures"))
    monkeypatch.setattr("src.export.annotate_document", lambda *a, **k: pytest.fail("Unexpected annotations"))
    assert cli.main([str(source), str(output), "--json"]) == 0


@pytest.mark.parametrize("flags", [["--start-page", "0"], ["--end-page", "2"], ["--port", "5805"]])
def test_invalid_options_fail_before_extraction(extraction, flags):
    source, output, calls = extraction
    with pytest.raises(SystemExit, match="2"):
        cli.main([str(source), str(output), *flags])
    assert not calls and not output.exists()


def test_overwrite_preserves_unrelated_files(extraction):
    source, output, calls = extraction
    output.mkdir()
    keep = output / "keep.txt"
    keep.write_text("keep")
    with pytest.raises(SystemExit, match="2"):
        cli.main([str(source), str(output)])
    assert not calls
    assert cli.main([str(source), str(output), "--overwrite"]) == 0
    assert keep.read_text() == "keep"


def test_input_inside_output_is_rejected(extraction):
    source, _, calls = extraction
    with pytest.raises(SystemExit, match="2"):
        cli.main([str(source), str(source.parent), "--overwrite"])
    assert not calls


def test_missing_key_fails_before_extraction(extraction, monkeypatch):
    source, output, calls = extraction
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(SystemExit, match="2"):
        cli.main([str(source), str(output)])
    assert not calls and not output.exists()


def test_env_file_and_environment_precedence(extraction, monkeypatch):
    source, output, _ = extraction
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    config = source.parent / "settings.env"
    config.write_text("OPENAI_API_KEY=file-key\nOPENAI_BASE_URL=https://example.invalid/v1\n")
    assert cli.main([str(source), str(output), "--env-file", str(config)]) == 0
    assert os.environ["OPENAI_API_KEY"] == "test-only"
    assert os.environ["OPENAI_BASE_URL"] == "https://example.invalid/v1"


def test_missing_explicit_env_file(extraction):
    source, output, calls = extraction
    with pytest.raises(SystemExit, match="2"):
        cli.main([str(source), str(output), "--env-file", "absent.env"])
    assert not calls


def test_requested_export_failure_keeps_other_outputs(extraction, monkeypatch):
    source, output, _ = extraction
    def fail(*a, **k):
        raise OSError("private provider details")
    monkeypatch.setattr("src.export.parse_to_html", fail)
    assert cli.main([str(source), str(output), "--markdown", "--html"]) == 3
    assert list(output.glob("*.md")) and not list(output.glob("*.html"))


def test_parse_failure_writes_only_requested_diagnostics(extraction, monkeypatch):
    source, output, _ = extraction
    def fail(*a, **k):
        raise ValueError("fake parse failure")
    monkeypatch.setattr(parse, "parse_page", fail)
    assert cli.main([str(source), str(output), "--all"]) == 1
    assert {p.suffix for p in output.iterdir()} == {".json"}


def test_partial_parse_and_page_range(extraction, monkeypatch):
    from PIL import Image
    source, output, calls = extraction
    pdf = source.with_suffix(".pdf")
    image = Image.new("RGB", (80, 60), "white")
    image.save(pdf, save_all=True, append_images=[image, image])
    original = parse.parse_page
    def page(*args, **kwargs):
        if args[2] == 3:
            raise ValueError("fake failure")
        return original(*args, **kwargs)
    monkeypatch.setattr(parse, "parse_page", page)
    assert cli.main([str(pdf), str(output), "--start-page", "2", "--end-page", "3"]) == 3
    assert len(calls) == 1
    assert list(output.glob("*.md"))


def test_rendering_view_does_not_filter_json(extraction, monkeypatch):
    source, output, _ = extraction
    def page(*args, **kwargs):
        return ParsePage(page=1, width_px=80, height_px=60, blocks=[
            ParseBlock(id="header", type="page_header", text="Running header", table=None,
                       conf=1, bbox=None, structure=None),
        ])
    monkeypatch.setattr(parse, "parse_page", page)
    assert cli.main([str(source), str(output), "--markdown", "--json", "--view", "clean"]) == 0
    assert "Running header" not in next(output.glob("*.md")).read_text()
    assert "Running header" in next(output.glob("*.json")).read_text()


def test_graph_uses_upload_name_and_start_time_for_every_format(extraction, monkeypatch):
    from datetime import UTC, datetime
    from src import graph
    source, output, _ = extraction
    class Clock(datetime):
        current = datetime(2026, 9, 23, 10, 0, 45, 123456, tzinfo=UTC)
        @classmethod
        def now(cls, tz=None):
            return cls.current
    monkeypatch.setattr(graph, "datetime", Clock)
    original = parse.parse_page
    def page(*args, **kwargs):
        Clock.current = datetime(2026, 9, 23, 10, 5, 0, tzinfo=UTC)
        return original(*args, **kwargs)
    monkeypatch.setattr(parse, "parse_page", page)
    result = graph.run_graph(str(source), output_dir=output, formats=set(graph.FORMATS),
                             original_filename="Uploaded report.pdf")
    assert result["status"] == "parsed"
    assert result["export_errors"] == []
    assert result["output_basename"] == "Uploaded report_20260923_100045Z"
    assert all(Path(p).name.startswith(result["output_basename"]) for p in result["output_paths"])
    assert result["doc_sha"] == result["parse_result"].doc_sha
