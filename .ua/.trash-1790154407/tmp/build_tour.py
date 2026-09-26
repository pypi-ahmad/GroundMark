import json
from pathlib import Path

UA_DIR = Path("D:/AI/GroundMark/.ua")
INTERMEDIATE = UA_DIR / "intermediate"

graph = json.loads((INTERMEDIATE / "assembled-graph.json").read_text(encoding="utf-8"))
node_ids = {n["id"] for n in graph["nodes"]}

tour = [
    {
        "order": 1,
        "title": "Project Architecture & Mission",
        "description": "Start with the project documentation and interactive architecture diagram to understand GroundMark's mission: high-fidelity document layout analysis, OCR visual reading order, and conversational question answering.",
        "nodeIds": [
            "document:README.md",
            "document:docs/ARCHITECTURE.md",
            "file:groundmark-architecture.html"
        ]
    },
    {
        "order": 2,
        "title": "Document Ingestion & Preprocessing",
        "description": "Learn how raw documents enter the system: PDFs are rasterized into page images, normalized, deskewed, and base64 encoded for multimodal LLM vision ingestion.",
        "nodeIds": [
            "file:src/preprocess.py"
        ]
    },
    {
        "order": 3,
        "title": "Layout Extraction & Bounding Box Detection",
        "description": "Examine the layout engine that predicts bounding boxes (BBox), identifies columns, headers, list items, and table structures across document pages.",
        "nodeIds": [
            "file:src/layout.py",
            "document:prompts/runtime/parse-page.md",
            "document:prompts/runtime/parse-page-structured.md"
        ]
    },
    {
        "order": 4,
        "title": "Markdown Serialization & Table Reconstruction",
        "description": "See how structured bounding boxes and cell coordinates are reconstituted into clean GitHub Flavored Markdown and HTML tables.",
        "nodeIds": [
            "file:src/markdown.py",
            "file:src/figures.py"
        ]
    },
    {
        "order": 5,
        "title": "Visual Annotation & Overlay Rendering",
        "description": "Explore how extracted bounding boxes and reading order paths are rendered directly back onto PDF and PNG document pages for human inspection.",
        "nodeIds": [
            "file:src/annotate.py"
        ]
    },
    {
        "order": 6,
        "title": "State Graph & Pipeline Orchestration",
        "description": "Discover how the state machine coordinates the end-to-end execution flow from raw file input to parsed artifacts, error boundaries, and telemetry.",
        "nodeIds": [
            "file:src/graph.py",
            "file:src/parse.py"
        ]
    },
    {
        "order": 7,
        "title": "Model Access & Diagnostics Telemetry",
        "description": "Inspect the low-level OpenAI model clients, prompt management, token cost accounting, and content filter safety diagnostics.",
        "nodeIds": [
            "file:src/llm.py",
            "file:src/prompts.py",
            "file:src/usage.py",
            "file:src/diagnostics.py"
        ]
    },
    {
        "order": 8,
        "title": "Conversational Q&A & Citation Verification",
        "description": "Understand how GroundMark answers complex questions over documents using multi-turn chat with strict statement-level citation verification.",
        "nodeIds": [
            "file:src/chat.py",
            "document:prompts/runtime/chat-answer.md",
            "document:prompts/runtime/chat-verify.md"
        ]
    },
    {
        "order": 9,
        "title": "Interactive Web UI",
        "description": "Tour the Streamlit frontend that provides side-by-side document inspection, bounding box debugging overlays, and real-time chat.",
        "nodeIds": [
            "file:src/ui/app.py",
            "file:run.cmd"
        ]
    },
    {
        "order": 10,
        "title": "Evaluation Benchmarks & Test Suite",
        "description": "Review the evaluation harnesses and automated test suite benchmarking layout IoU, prompt variations, and resolution latency trade-offs.",
        "nodeIds": [
            "file:scripts/evaluate_layout.py",
            "file:scripts/evaluate_chat.py",
            "file:tests/test_layout_structure.py"
        ]
    }
]

# Verify all nodeIds exist
for step in tour:
    for nid in step["nodeIds"]:
        if nid not in node_ids:
            print(f"Error: Tour node {nid} not found in graph!")
        else:
            print(f"Verified {nid}")

out_path = INTERMEDIATE / "tour.json"
out_path.write_text(json.dumps(tour, indent=2), encoding="utf-8")
print(f"Wrote {len(tour)} tour steps to {out_path.name}")
