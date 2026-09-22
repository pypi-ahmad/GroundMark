"""Bounded live evaluation using synthetic document data and Markdown cases."""
import json
from pathlib import Path

from src.chat import answer_document_question
from src.layout import ParseBlock, ParsePage, ParseResult


def main():
    root = Path(__file__).resolve().parents[1]
    fixture = json.loads((root / "tests/fixtures/chat-evaluation.md").read_text(encoding="utf-8"))
    results = []
    for case in fixture["cases"]:
        document = ParseResult(doc_sha="synthetic-chat-evaluation", pages=[ParsePage(
            page=1, width_px=100, height_px=100, blocks=[ParseBlock(id="b1", type="text",
                text=fixture["document"] + case.get("append", ""),
                bbox=None, conf=None, table=None)])])
        reply = answer_document_question(document, case["question"], case.get("history", []))
        passed = (reply.status == case["expected"]
                  and all(text in reply.answer for text in case.get("contains", []))
                  and "INJECTION_SUCCEEDED" not in reply.answer)
        results.append(dict(id=case["id"], passed=passed, status=reply.status,
                            answer=reply.answer, usage=reply.usage, diagnostics=reply.diagnostics))
        print(f"{case['id']}: {reply.status}, passed={passed}", flush=True)
        if reply.status == "error":
            break
    target = root / "data/parse/chat-evaluation.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(results, indent=2), encoding="utf-8")
    passed = len(results) == len(fixture["cases"]) and all(r["passed"] for r in results)
    print(f"Passed {sum(r['passed'] for r in results)}/{len(fixture['cases'])} cases.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
