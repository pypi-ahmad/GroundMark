import json
from pathlib import Path

from PIL import Image
import pytest

from scripts.evaluate_reconciliation import (
    Labels, Manifest, Sample, file_ref, score_replay, contour_mask_iou, evaluate,
)
from src.layout_reconcile import convert_layout, reconcile_page
from tests.test_layout_reconcile import block, page, region, runtime
from tests.test_v3_completion import artifact_for


def test_independent_match_and_order_labels_and_partial_judgments():
    original = page(block(), block((.6, .6, .9, .9)))
    result = reconcile_page(original, convert_layout(runtime(region(order=8), region((60, 60, 90, 90), order=0))))
    artifact = artifact_for(result)
    labels = Labels(provenance="Synthetic hand-specified test", acceptable_matches={0: [0], 1: []},
                    before=[(0, 1)], contours={0: [( .1,.1),(.5,.1),(.5,.5),(.1,.5)]})
    metrics = score_replay(original, result.page, artifact, labels)
    assert metrics["correct_matches"] == 1 and metrics["incorrect_matches"] == 1
    assert metrics["order_errors"] == 1 and metrics["content_preserved"]
    assert metrics["contour_mask_iou"][0]["iou"] == 1
    partial = score_replay(original, result.page, artifact, Labels(provenance="partial", acceptable_matches={0: [0]}))
    assert partial["unreviewed_matches"] == 1
    unavailable = score_replay(original, result.page, artifact)
    assert unavailable["correct_matches"] is None and unavailable["order_errors"] is None


def test_mask_iou_and_invalid_labels():
    a = [(0,0),(.4,0),(.4,.4),(0,.4)]
    b = [(.6,.6),(1,.6),(1,1),(.6,1)]
    assert contour_mask_iou(a, a, 100, 100) == 1
    assert contour_mask_iou(a, b, 100, 100) == 0
    for values in (dict(before=[(0,1),(1,0)]), dict(acceptable_matches={0:[1,1]}),
                   dict(contours={0:[(0,0),(1,1),(1,0),(0,1)]})):
        with pytest.raises(ValueError):
            Labels(provenance="invalid", **values)


def test_saved_artifact_replay_is_offline_and_hash_bound(tmp_path, monkeypatch):
    from scripts import evaluate_reconciliation as evaluator
    original = page(block())
    result = reconcile_page(original, convert_layout(runtime(region())))
    image, response, layout = [tmp_path / name for name in ("page.png", "response.json", "layout.json")]
    Image.new("RGB", (100,100), "white").save(image)
    response.write_text(original.model_dump_json())
    layout.write_text(artifact_for(result).model_dump_json())
    sample = Sample(image=file_ref(image), response=file_ref(response), layout=file_ref(layout),
                    page=1, profile="detailed")
    manifest = Manifest(provenance="synthetic", samples=[sample])
    monkeypatch.setattr(evaluator, "LayoutRuntime", lambda *a: pytest.fail("inference called"))
    report = evaluate(manifest, tmp_path, tmp_path/"output")
    assert report["paid_calls"] == 0 and report["samples"][0]["content_preserved"]
    assert (tmp_path/"output"/"report.md").exists()
    response.write_text("{}")
    with pytest.raises(ValueError, match="checksum"):
        evaluate(manifest, tmp_path, tmp_path/"bad")


def test_labeled_missed_assignment_and_unreviewed_order():
    original = page(block())
    result = reconcile_page(original, convert_layout(runtime(region(score=.7))))
    metrics = score_replay(original, result.page, artifact_for(result),
                           Labels(provenance="synthetic", acceptable_matches={0:[0]}))
    assert metrics["labeled_missed_assignments"] == 1
    assert metrics["order_errors"] is None


@pytest.mark.parametrize("failure_stage", ["inference", "prompt", "reconciliation"])
def test_replay_distinguishes_fallback_from_application_defect(tmp_path, monkeypatch, failure_stage):
    from scripts import evaluate_reconciliation as evaluator
    from src.layout_detector import LayoutInferenceError
    from src.layout_reconcile import LayoutConversionError, ReconciliationInvariantError

    original = page(block())
    image, response = tmp_path / "page.png", tmp_path / "response.json"
    Image.new("RGB", (100, 100), "white").save(image)
    response.write_text(original.model_dump_json())
    manifest = Manifest(provenance="synthetic failure", samples=[Sample(
        image=file_ref(image), response=file_ref(response), page=1, profile="detailed")])

    class Runtime:
        def predict(self, *args, **kwargs):
            if failure_stage == "inference":
                raise LayoutInferenceError("prediction_failed", device="cpu",
                    failures=("cuda_execution", "cpu_execution"))
            return runtime(region())

    monkeypatch.setattr(evaluator, "LayoutRuntime", lambda *args: Runtime())
    def fail(*args, **kwargs):
        if failure_stage == "prompt":
            raise LayoutConversionError("guide_too_large", page=1)
        raise ReconciliationInvariantError("not a detector miss")
    if failure_stage != "inference":
        monkeypatch.setattr(evaluator,
            "project_layout_guide" if failure_stage == "prompt" else "check_reconciliation", fail)
    row = evaluate(manifest, tmp_path, tmp_path / "out", run_v3=True)["samples"][0]
    assert row["content_preserved"] and row["matches"] is None
    assert json.loads((tmp_path / "out/000.page.json").read_text()) == original.model_dump(mode="json")
    if failure_stage == "reconciliation":
        assert row["application_error"] == "reconciliation_invariant_violation"
        assert row["failure"] is None
    else:
        assert row["failure"]["stage"] == failure_stage
        assert row["application_error"] is None and row["guide_bytes"] is None
    if failure_stage == "inference":
        assert row["execution_failures"] == ("cuda_execution", "cpu_execution")


def test_replay_rejects_mismatched_source_dimensions(tmp_path):
    image, response = tmp_path / "page.png", tmp_path / "response.json"
    Image.new("RGB", (120, 100), "white").save(image)
    response.write_text(page(block()).model_dump_json())
    manifest = Manifest(provenance="mismatch", samples=[Sample(
        image=file_ref(image), response=file_ref(response), page=1, profile="detailed")])
    with pytest.raises(ValueError, match="identity mismatch"):
        evaluate(manifest, tmp_path, tmp_path / "out")
