"""Local saved-response evaluation. No Sol calls or automatic policy tuning."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from PIL import Image, ImageChops, ImageDraw
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.config import LayoutConfig
from src.layout import LayoutPageArtifact, LegacyParsePage, ParsePage, ReconcilePolicy, ReconciliationDetails
from src.layout_detector import LayoutRuntime, LayoutModelUnavailable, LayoutInferenceError, MODEL_ID, REVISION
from src.layout_reconcile import (
    LayoutConversionError, convert_layout, project_layout_guide, reconcile_page,
    check_reconciliation, layout_match_counts, _validate_polygon, ReconciliationInvariantError,
)


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class FileRef(Record):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Labels(Record):
    provenance: str = Field(min_length=1)
    # Original Sol indices. [] explicitly means no acceptable partner.
    acceptable_matches: dict[int, list[int]] = Field(default_factory=dict)
    # Strict before/after constraints; ties are deliberately not constraints.
    before: list[tuple[int, int]] = Field(default_factory=list)
    contours: dict[int, list[tuple[float, float]]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_labels(self):
        if any(b < 0 or len(rs) != len(set(rs)) or any(r < 0 for r in rs)
               for b, rs in self.acceptable_matches.items()):
            raise ValueError("Invalid correspondence labels")
        if len(self.before) != len(set(self.before)) or any(a < 0 or b < 0 or a == b for a, b in self.before):
            raise ValueError("Invalid order labels")
        edges = {}
        for a, b in self.before:
            edges.setdefault(a, set()).add(b)
        def visit(node, pending, done):
            if node in pending:
                raise ValueError("Cyclic order labels")
            if node in done:
                return
            for child in edges.get(node, ()):
                visit(child, pending | {node}, done)
            done.add(node)
        done = set()
        for node in edges:
            visit(node, set(), done)
        for index, points in self.contours.items():
            if index < 0 or any(not 0 <= v <= 1 for p in points for v in p):
                raise ValueError("Invalid contour labels")
            _validate_polygon(points)
        return self


class Sample(Record):
    image: FileRef
    response: FileRef
    page: int = Field(ge=1, strict=True)
    profile: str = Field(pattern="^(baseline|candidate|legacy|detailed)$")
    layout: FileRef | None = None
    labels: Labels | None = None
    category: str = "unreviewed"


class Manifest(Record):
    version: int = Field(default=1, ge=1, le=1)
    provenance: str = Field(min_length=1)
    samples: list[Sample] = Field(min_length=1)


def file_ref(path):
    path = Path(path).resolve()
    return FileRef(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def checked_file(ref, base):
    path = (base / ref.path).resolve()
    if hashlib.sha256(path.read_bytes()).hexdigest() != ref.sha256:
        raise ValueError("Evaluation input checksum mismatch")
    return path


def comparison_manifest(directory):
    """Explicit adapter for the existing paired comparison; never invent labels."""
    samples = []
    for image in sorted(Path(directory).glob("*.page-*.png")):
        for profile in ("baseline", "candidate"):
            samples.append(Sample(image=file_ref(image),
                response=file_ref(image.with_suffix(f".{profile}.json")),
                page=int(image.stem.rsplit("-", 1)[1]), profile=profile))
    return Manifest(provenance="Existing saved Sol responses; no reviewed quality labels", samples=samples)


def contour_mask_iou(predicted, expected, width, height):
    """Pillow binary raster overlap at source resolution, not vector IoU."""
    masks = []
    for points in (predicted, expected):
        mask = Image.new("1", (width, height))
        ImageDraw.Draw(mask).polygon([(x * width, y * height) for x, y in points], fill=1)
        masks.append(mask)
    intersection = ImageChops.logical_and(*masks).histogram()[255]
    union = ImageChops.logical_or(*masks).histogram()[255]
    return intersection / union if union else None


def score_replay(original, output, artifact, labels=None):
    details = artifact.reconciliation if artifact else None
    positions = {d.original_index: d.output_index for d in details.decisions} if details else dict(enumerate(range(len(original.blocks))))
    preserved = len(original.blocks) == len(output.blocks) and all(
        original.blocks[i].model_dump(exclude={"bbox"}) == output.blocks[j].model_dump(exclude={"bbox"})
        for i, j in positions.items())
    metrics = dict(content_preserved=preserved, **layout_match_counts(artifact),
                   correct_matches=None, incorrect_matches=None, labeled_missed_assignments=None,
                   unreviewed_matches=None, order_errors=None, order_constraints=0,
                   contour_mask_iou=[], quality_status="unreviewed" if labels is None else "partially_reviewed")
    if labels is None:
        return metrics
    region_count = len(artifact.layout.regions) if artifact else 0
    if (any(i >= len(original.blocks) for i in labels.acceptable_matches)
            or any(r >= region_count for rs in labels.acceptable_matches.values() for r in rs)
            or any(r >= region_count for r in labels.contours)
            or any(max(pair) >= len(original.blocks) for pair in labels.before)):
        raise ValueError("Review labels reference unavailable blocks or regions")
    if details:
        correct = incorrect = missed = unreviewed = 0
        for decision in details.decisions:
            partners = labels.acceptable_matches.get(decision.original_index)
            if partners is None:
                unreviewed += decision.region_index is not None
            elif decision.region_index is None:
                missed += bool(partners)
            elif decision.region_index in partners:
                correct += 1
            else:
                incorrect += 1
        metrics.update(correct_matches=correct, incorrect_matches=incorrect,
                       labeled_missed_assignments=missed, unreviewed_matches=unreviewed)
    if labels.before:
        metrics.update(order_constraints=len(labels.before),
                       order_errors=sum(positions[a] >= positions[b] for a, b in labels.before))
    if artifact:
        for index, expected in labels.contours.items():
            region = artifact.layout.regions[index]
            metrics["contour_mask_iou"].append(dict(region_index=index,
                iou=contour_mask_iou(region.polygon, expected, original.width_px, original.height_px)
                    if region.contour_status == "valid" else None,
                geometry="polygon" if region.contour_status == "valid" else "unavailable"))
    return metrics


def evaluate(manifest, base, output_dir, *, run_v3=False, device="auto", policy=None):
    """Persist replay evidence in a new directory; supplied labels are never inferred."""
    policy = policy or ReconcilePolicy()
    policy.check_active()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    runtime = None
    cache = {}
    rows = []
    for index, sample in enumerate(manifest.samples):
        started = perf_counter()
        image_path = checked_file(sample.image, base)
        response_path = checked_file(sample.response, base)
        data = json.loads(response_path.read_text(encoding="utf-8"))
        data = data.get("result", data)
        original = (LegacyParsePage.model_validate(data).to_page()
                    if sample.profile in ("baseline", "legacy") else ParsePage.model_validate(data))
        with Image.open(image_path) as image:
            image.load()
            if (original.page, original.width_px, original.height_px) != (sample.page, image.width, image.height):
                raise ValueError("Response/raster page identity mismatch")
        artifact = None
        layout = None
        failure = None
        application_error = None
        guide = None
        actual_device = None
        failures = ()
        stage = "inference"
        try:
            if sample.layout:
                saved = checked_file(sample.layout, base)
                artifact = LayoutPageArtifact.model_validate_json(saved.read_text(encoding="utf-8"))
                layout = artifact.layout
            elif run_v3:
                if runtime is None:
                    runtime = LayoutRuntime(LayoutConfig(device=device))
                key = (sample.image.sha256, sample.page)
                if key not in cache:
                    with Image.open(image_path) as image:
                        raw = runtime.predict(image, page_number=sample.page)
                    actual_device, failures = raw.device, raw.execution_failures
                    stage = "conversion"
                    cache[key] = convert_layout(raw)
                layout = cache[key]
            else:
                raise ValueError("Missing saved V3 artifact; explicitly select --run-v3")
            if (layout.model_id, layout.revision, layout.engine) != (MODEL_ID, REVISION, "onnxruntime"):
                raise ValueError("Evaluation requires the pinned official ONNX artifact")
            if (layout.page, layout.width_px, layout.height_px) != (original.page, original.width_px, original.height_px):
                raise ValueError("Layout/raster page identity mismatch")
            actual_device, failures = layout.device, layout.execution_failures
            artifact = LayoutPageArtifact(layout=layout)
            stage = "prompt"
            guide, contours = project_layout_guide(layout)
            artifact = artifact.model_copy(update={"guide_contours": contours})
        except (LayoutModelUnavailable, LayoutInferenceError, LayoutConversionError) as exc:
            failure = dict(stage="initialization" if isinstance(exc, LayoutModelUnavailable) else stage, code=exc.code)
            actual_device = getattr(exc, "device", None) or actual_device
            failures = getattr(exc, "failures", failures)
        layout_seconds = perf_counter() - started
        output = original.model_copy(deep=True)
        if failure is None:
            try:
                result = reconcile_page(original, layout, policy=policy)
                artifact = LayoutPageArtifact(layout=result.metadata.layout,
                    reconciliation=ReconciliationDetails.model_validate(result.metadata.model_dump(exclude={"layout"})),
                    guide_contours=artifact.guide_contours)
                check_reconciliation(original, result.page, artifact)
                output = result.page
            except Exception as exc:
                application_error = ("reconciliation_invariant_violation"
                                     if isinstance(exc, ReconciliationInvariantError) else "reconciliation_failed")
                artifact = artifact.model_copy(update={"reconciliation": None})
        metrics = score_replay(original, output, artifact, sample.labels)
        if not metrics["content_preserved"]:
            raise ValueError("Replay changed Sol content")
        if artifact:
            (output_dir / f"{index:03d}.layout.json").write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
        (output_dir / f"{index:03d}.page.json").write_text(output.model_dump_json(indent=2), encoding="utf-8")
        rows.append(dict(sample=index, page=sample.page, profile=sample.profile, category=sample.category,
            model_id=MODEL_ID, revision=REVISION, device=actual_device, execution_failures=failures,
            layout_seconds=layout_seconds, page_seconds=perf_counter() - started,
            failure=failure, application_error=application_error, policy=policy.model_dump(),
            policy_version="v3-authoritative-v1", guide_bytes=len(guide.encode()) if guide else None,
            label_provenance=sample.labels.provenance if sample.labels else None, **metrics))
    report = dict(provenance=manifest.provenance, samples=rows, paid_calls=0,
                  quality_note="Unreviewed metrics are unavailable, not zero errors. Match counts are not accuracy.",
                  contour_metric="Pillow binary masks at original raster resolution; coordinates x*width,y*height")
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    (output_dir / "report.md").write_text(
        "# Offline V3 reconciliation replay\n\nNo Sol calls. " + report["quality_note"] +
        "\n\n| Sample | Profile | Device | Matches | Content preserved | Quality labels |\n"
        "|---|---|---|---:|---|---|\n" +
        "".join(f"| {r['sample']} | {r['profile']} | {r['device']} | {r['matches']} | {r['content_preserved']} | {r['quality_status']} |\n" for r in rows),
        encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--manifest", type=Path)
    source.add_argument("--saved-comparison", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-v3", action="store_true")
    parser.add_argument("--device", choices=("auto", "cpu"), default="auto")
    parser.add_argument("--policy", type=Path, help="Explicit provisional policy JSON; no automatic tuning")
    args = parser.parse_args()
    manifest = (Manifest.model_validate_json(args.manifest.read_text(encoding="utf-8"))
                if args.manifest else comparison_manifest(args.saved_comparison))
    policy = ReconcilePolicy.model_validate_json(args.policy.read_text(encoding="utf-8")) if args.policy else None
    report = evaluate(manifest, args.manifest.parent if args.manifest else Path.cwd(), args.output,
                      run_v3=args.run_v3, device=args.device, policy=policy)
    print(json.dumps(dict(samples=len(report["samples"]), paid_calls=0, report=str(args.output / "report.json"))))


if __name__ == "__main__":
    main()
