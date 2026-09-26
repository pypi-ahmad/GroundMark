import json
from datetime import datetime, timezone
from pathlib import Path

UA_DIR = Path("D:/AI/GroundMark/.ua")
INTERMEDIATE = UA_DIR / "intermediate"

assembled = json.loads((INTERMEDIATE / "assembled-graph.json").read_text(encoding="utf-8"))
layers = json.loads((INTERMEDIATE / "layers.json").read_text(encoding="utf-8"))
tour = json.loads((INTERMEDIATE / "tour.json").read_text(encoding="utf-8"))

now_iso = datetime.now(timezone.utc).isoformat()

full_graph = {
    "version": "1.0.0",
    "project": {
        "name": "GroundMark",
        "languages": ["python", "markdown", "json", "toml", "batch"],
        "frameworks": ["LangChain", "LangGraph", "Pydantic", "Pytest", "Streamlit"],
        "description": "Document layout analysis, OCR visual reading order, and conversational QA toolkit",
        "analyzedAt": now_iso,
        "gitCommitHash": "e751f84f2f20bc2d30a0064bd07c7ba787ace97a"
    },
    "nodes": assembled["nodes"],
    "edges": assembled["edges"],
    "layers": layers,
    "tour": tour
}

out_file = INTERMEDIATE / "assembled-graph.json"
out_file.write_text(json.dumps(full_graph, indent=2), encoding="utf-8")
print(f"Wrote full KnowledgeGraph to {out_file} with {len(full_graph['nodes'])} nodes, {len(full_graph['edges'])} edges, {len(layers)} layers, {len(tour)} tour steps.")
