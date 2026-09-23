"""Enforce the shared allowance across baseline and candidate runs."""
import json

import pytest

from scripts import evaluate_layout as evaluation
from src.layout import ParsePage, LegacyParsePage


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    (tmp_path / "data/inbox").mkdir(parents=True)
    (tmp_path / "prompts/runtime").mkdir(parents=True)
    (tmp_path / "prompts/runtime/parse-page.md").write_text("page {page_number}")
    (tmp_path / "prompts/runtime/parse-page-structured.md").write_text("page {page_number}")
    references = tmp_path / "references"
    references.mkdir()
    for name, _ in evaluation.APPROVED_SAMPLES:
        (tmp_path / "data/inbox" / f"{name}.pdf").write_bytes(b"source")
        (references / f"{name}.parse.json").write_text("{}")
    monkeypatch.setattr(evaluation, "ROOT", tmp_path)
    monkeypatch.setattr(evaluation, "REFERENCES", references)
    monkeypatch.setattr(evaluation, "preprocess_pages", lambda p, **kw: [dict(page=kw["start_page"])])
    monkeypatch.setattr(evaluation, "score_page", lambda *a: dict(reference_token_f1=1.0))
    return tmp_path / "output"


def runner(payload, prompt, **kwargs):
    assert kwargs.pop("schema") in (ParsePage, LegacyParsePage)
    assert kwargs == dict(max_completion_tokens=8192, reasoning_effort="medium")
    return dict(page=payload["page"], status="parsed", result=ParsePage(
        page=payload["page"], width_px=100, height_px=100, blocks=[]).model_dump(),
        diagnostics=dict(usage_known=True, input_tokens=100, output_tokens=10))


def test_two_stages_share_ten_request_allowance(corpus):
    baseline = evaluation.compare(corpus, "baseline", runner=runner)
    assert baseline["requests"] == 5 and baseline["phases"] == ["baseline"]
    candidate = evaluation.compare(corpus, "candidate", runner=runner)
    assert candidate["requests"] == 10 and candidate["metric_gate_passed"]
    assert candidate["promoted"] is False
    with pytest.raises(ValueError):
        evaluation.compare(corpus, "candidate", runner=runner)


@pytest.mark.parametrize("status,known,expected", [
    ("refused", True, "refused"), ("content_filtered", True, "content_filtered"),
    ("parsed", False, "unknown_usage")])
def test_failure_stops_and_prevents_candidate(corpus, status, known, expected):
    def fail(payload, prompt, **kwargs):
        result = runner(payload, prompt, **kwargs)
        result["status"] = status
        result["diagnostics"]["usage_known"] = known
        return result
    outcome = evaluation.compare(corpus, "baseline", runner=fail)
    assert outcome["requests"] == 1 and outcome["stop_reason"] == expected
    with pytest.raises(ValueError):
        evaluation.compare(corpus, "candidate", runner=runner)


@pytest.mark.parametrize("field,value,reason", [("estimated_cost_usd", 1.9, "estimated_budget"),
                                               ("requests", 10, "request_limit")])
def test_candidate_stops_before_exceeding_allowance(corpus, field, value, reason):
    evaluation.compare(corpus, "baseline", runner=runner)
    path = corpus / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest[field] = value
    path.write_text(json.dumps(manifest))
    outcome = evaluation.compare(corpus, "candidate", runner=lambda *a, **k: pytest.fail("Unexpected call"))
    assert outcome["stop_reason"] == reason


def test_metric_gate_rejects_regression(corpus):
    evaluation.compare(corpus, "baseline", runner=runner)
    outcome = evaluation.compare(corpus, "candidate", runner=runner)
    outcome["pages"][-1]["metrics"]["reference_token_f1"] = 0.99
    assert not evaluation.metric_gate(outcome["pages"])
