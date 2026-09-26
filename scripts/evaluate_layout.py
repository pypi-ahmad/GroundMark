"""Two-stage, bounded layout comparison. Baseline runs before schema changes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.evaluate_prompts import REFERENCES, ROOT, run_page, score_page
from scripts.evaluate_resolution import APPROVED_SAMPLES
from src.layout import ParsePage, LegacyParsePage
from src.preprocess import preprocess_pages
from src.usage import cost_usd


def metric_gate(pages: list[dict]) -> bool:
    """Require five paired parsed pages with no per-page candidate F1 regression."""
    if len(pages) != 10 or any(p["status"] != "parsed" for p in pages):
        return False
    scores = {}
    for page in pages:
        scores.setdefault((page["document"], page["page"]), {})[page["phase"]] = page["metrics"]["reference_token_f1"]
    return len(scores) == 5 and all(set(pair) == {"baseline", "candidate"}
                                   and pair["candidate"] >= pair["baseline"] for pair in scores.values())


def compare(output: Path, phase: str, *, runner=None) -> dict:
    """Run one authorized baseline/candidate phase and persist its manifest.

    output is the evidence directory; phase selects the prompt and schema.
    runner can inject offline responses. Invalid phase/source progression raises
    ValueError; input/I/O errors propagate. The default runner makes paid calls.
    """
    if phase not in {"baseline", "candidate"}:
        raise ValueError("Unknown comparison phase")
    runner = runner or run_page
    manifest_path = output / "manifest.json"
    prompt_name = "parse-page-structured.md" if phase == "candidate" else "parse-page.md"
    prompt = (ROOT / "prompts/runtime" / prompt_name).read_text(encoding="utf-8")
    schema = ParsePage if phase == "candidate" else LegacyParsePage
    sources = {}
    references = {}
    for name, _ in APPROVED_SAMPLES:
        source = ROOT / "data/inbox" / f"{name}.pdf"
        sources[name] = hashlib.sha256(source.read_bytes()).hexdigest()
        references[name] = json.loads((REFERENCES / f"{name}.parse.json").read_text(encoding="utf-8"))
    if phase == "baseline":
        output.mkdir(parents=True, exist_ok=False)
        manifest = dict(requests=0, estimated_cost_usd=0.0, max_requests=10,
                        budget_usd=2.0, reserve_usd=0.20, sources=sources, pages=[],
                        phases=[], stop_reason=None, promoted=False,
                        model="gpt-6-sol", reasoning="medium", dpi=200, long_edge=1600,
                        max_completion_tokens=8192, max_retries=0, context="empty for both profiles")
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["sources"] != sources or manifest["phases"] != ["baseline"]:
            raise ValueError("Sources changed or baseline is incomplete")
        if manifest["stop_reason"] != "baseline_complete":
            raise ValueError("Baseline did not complete successfully")
    if phase in manifest["phases"]:
        raise ValueError("Phase already dispatched")
    manifest["phases"].append(phase)
    (output / f"{phase}-prompt.md").write_text(prompt, encoding="utf-8")
    (output / f"{phase}-schema.json").write_text(json.dumps(schema.model_json_schema(), indent=2), encoding="utf-8")

    def save():
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    save()
    for name, end in APPROVED_SAMPLES:
        for number in range(1, end + 1):
            if manifest["requests"] >= 10:
                manifest["stop_reason"] = "request_limit"
            elif manifest["estimated_cost_usd"] + 0.20 > 2.0:
                manifest["stop_reason"] = "estimated_budget"
            else:
                manifest["stop_reason"] = None
            if manifest["stop_reason"]:
                save()
                return manifest
            payload = preprocess_pages(ROOT / "data/inbox" / f"{name}.pdf",
                                       start_page=number, end_page=number)[0]
            manifest["requests"] += 1
            save()  # A dispatched or interrupted request consumes the allowance.
            outcome = runner(payload, prompt, max_completion_tokens=8192, reasoning_effort="medium", schema=schema)
            outcome.update(document=name, phase=phase)
            diagnostic = outcome.get("diagnostics", {})
            if diagnostic.get("usage_known"):
                manifest["estimated_cost_usd"] += cost_usd(dict(
                    input_tokens=diagnostic["input_tokens"], output_tokens=diagnostic["output_tokens"],
                    cached_tokens=diagnostic.get("cached_tokens") or 0,
                    cache_write_tokens=diagnostic.get("cache_write_tokens") or 0))
            else:
                manifest["stop_reason"] = "unknown_usage"
            if outcome["status"] == "parsed":
                outcome["metrics"] = score_page(ParsePage.model_validate(outcome["result"]), references[name])
            else:
                manifest["stop_reason"] = manifest["stop_reason"] or outcome["status"]
            filename = f"{name}.page-{number}.{phase}.json"
            (output / filename).write_text(json.dumps(outcome, indent=2), encoding="utf-8")
            manifest["pages"].append({k: v for k, v in outcome.items() if k not in {"result", "usage"}})
            save()
            print(f"{phase}: {name}, page {number}: {outcome['status']}; requests={manifest['requests']}; estimated=${manifest['estimated_cost_usd']:.5f}", flush=True)
            if manifest["stop_reason"]:
                return manifest
    manifest["stop_reason"] = f"{phase}_complete"
    if phase == "candidate":
        manifest["metric_gate_passed"] = metric_gate(manifest["pages"])
        manifest["visual_review"] = "pending"
    save()
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=["baseline", "candidate"], required=True)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if not args.live:
        parser.error("Explicit --live is required")
    compare(args.output, args.phase)
