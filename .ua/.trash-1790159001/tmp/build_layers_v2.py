import json
from pathlib import Path

UA_DIR = Path("D:/AI/GroundMark/.ua")
INTERMEDIATE = UA_DIR / "intermediate"

graph = json.loads((INTERMEDIATE / "assembled-graph.json").read_text(encoding="utf-8"))
file_level_types = {'file', 'config', 'document', 'service', 'pipeline', 'table', 'schema', 'resource', 'endpoint'}
all_file_nodes = {n["id"] for n in graph["nodes"] if n["type"] in file_level_types}

layers_spec = [
    {
        "id": "layer:user-interface",
        "name": "CLI & User Interface",
        "description": "Interactive Streamlit web frontend, CLI runner and commands, clipboard integrations, launcher scripts, and interactive architecture visualizations.",
        "patterns": [
            "file:src/cli.py",
            "file:src/ui/app.py",
            "file:src/ui/clipboard.py",
            "file:src/ui/__init__.py",
            "file:run.cmd",
            "file:groundmark-architecture.html",
            "file:groundmark-architecture.visual-check.html"
        ]
    },
    {
        "id": "layer:document-chat",
        "name": "Document Chat & Reasoning",
        "description": "Conversational question-answering engine with page-level citation verification, structured evidence extraction, and claim validation.",
        "patterns": [
            "file:src/chat.py"
        ]
    },
    {
        "id": "layer:pipeline-orchestration",
        "name": "Pipeline Orchestration & State Graph",
        "description": "Workflow graph and facade controllers orchestrating document ingestion, layout parsing, markdown generation, and state persistence.",
        "patterns": [
            "file:src/graph.py",
            "file:src/parse.py"
        ]
    },
    {
        "id": "layer:layout-and-vision-engine",
        "name": "Layout Analysis & Document Vision",
        "description": "Core computer vision and document layout algorithms handling PDF rasterization, image deskewing, reading order, table extraction, figure cropping, and export serialization.",
        "patterns": [
            "file:src/layout.py",
            "file:src/annotate.py",
            "file:src/figures.py",
            "file:src/markdown.py",
            "file:src/export.py",
            "file:src/output_names.py",
            "file:src/preprocess.py"
        ]
    },
    {
        "id": "layer:model-and-inference",
        "name": "Model Access & Telemetry Core",
        "description": "LLM client wrappers, prompt template resolvers, Pydantic domain models, token usage ledgers, and content filter safety diagnostics.",
        "patterns": [
            "file:src/llm.py",
            "file:src/prompts.py",
            "file:src/models.py",
            "file:src/diagnostics.py",
            "file:src/usage.py",
            "file:src/__init__.py"
        ]
    },
    {
        "id": "layer:evaluation-and-benchmarks",
        "name": "Evaluation & Quality Benchmarks",
        "description": "Automated evaluation CLI scripts measuring layout extraction IoU, prompt variations, image resolution trade-offs, and QA accuracy.",
        "patterns": [
            "file:scripts/evaluate_chat.py",
            "file:scripts/evaluate_layout.py",
            "file:scripts/evaluate_prompts.py",
            "file:scripts/evaluate_resolution.py"
        ]
    },
    {
        "id": "layer:testing-and-fixtures",
        "name": "Test Suite & Mocks",
        "description": "Unit tests, integration test suites, mock LLM client fixtures, synthetic invoice generators, and test evaluation datasets.",
        "patterns": [
            "file:tests/__init__.py",
            "file:tests/fake_llm.py",
            "file:tests/fixtures/make_invoice_png.py",
            "document:tests/fixtures/chat-evaluation.md",
            "file:tests/test_annotate.py",
            "file:tests/test_chat.py",
            "file:tests/test_cli.py",
            "file:tests/test_cli_extraction.py",
            "file:tests/test_diagnostics.py",
            "file:tests/test_graph.py",
            "file:tests/test_launcher.py",
            "file:tests/test_layout_evaluation.py",
            "file:tests/test_layout_structure.py",
            "file:tests/test_markdown.py",
            "file:tests/test_output_names.py",
            "file:tests/test_parse.py",
            "file:tests/test_preprocess.py",
            "file:tests/test_prompt_evaluation.py",
            "file:tests/test_prompts.py",
            "file:tests/test_resolution_evaluation.py",
            "file:tests/test_ui_diagnostics.py",
            "file:tests/test_usage.py"
        ]
    },
    {
        "id": "layer:documentation-and-prompts",
        "name": "Documentation & Runtime Prompts",
        "description": "System architecture guides, technical runbooks, research evaluations, compliance policies, and runtime system prompt templates.",
        "patterns": [
            "document:README.md",
            "document:docs/ARCHITECTURE.md",
            "document:docs/COMPLIANCE.md",
            "document:docs/CONTENT-FILTER-DIAGNOSTICS.md",
            "document:docs/CONTRIBUTING.md",
            "document:docs/LAYOUT-EVALUATION.md",
            "document:docs/MODEL.md",
            "document:docs/PROMPT-EVALUATION.md",
            "document:docs/PROMPTS.md",
            "document:docs/RUNBOOK.md",
            "document:docs/SOL-RESOLUTION-EVALUATION.md",
            "document:prompts/runtime/chat-answer.md",
            "document:prompts/runtime/chat-verify.md",
            "document:prompts/runtime/parse-page-structured.md",
            "document:prompts/runtime/parse-page.md"
        ]
    },
    {
        "id": "layer:configuration-and-build",
        "name": "Configuration & Build Environment",
        "description": "Environment settings, dependencies specifications, pyproject.toml packaging, and architecture configs.",
        "patterns": [
            "config:.env.example",
            "config:pyproject.toml",
            "document:requirements.txt",
            "document:requirements-dev.txt",
            "config:groundmark-architecture.json",
            "config:groundmark-architecture.visual-check.json"
        ]
    }
]

assigned = set()
layers = []

for l in layers_spec:
    layer_nodes = []
    for node_id in l["patterns"]:
        if node_id not in all_file_nodes:
            print(f"Warning: Node {node_id} not in all_file_nodes")
        if node_id in assigned:
            print(f"Error: Node {node_id} assigned multiple times")
        assigned.add(node_id)
        layer_nodes.append(node_id)
    
    layers.append({
        "id": l["id"],
        "name": l["name"],
        "description": l["description"],
        "nodeIds": layer_nodes
    })

unassigned = all_file_nodes - assigned
if unassigned:
    print(f"Error: Unassigned file nodes: {unassigned}")
else:
    print(f"SUCCESS: All {len(all_file_nodes)} file nodes cleanly partitioned into {len(layers)} layers!")

out_path = INTERMEDIATE / "layers.json"
out_path.write_text(json.dumps(layers, indent=2), encoding="utf-8")
print(f"Wrote {len(layers)} layers to {out_path.name}")
