import json
import os
import re
from pathlib import Path

PROJECT_ROOT = Path("D:/AI/GroundMark")
UA_DIR = PROJECT_ROOT / ".ua"
INTERMEDIATE = UA_DIR / "intermediate"
TMP = UA_DIR / "tmp"

batches_data = json.loads((INTERMEDIATE / "batches.json").read_text(encoding="utf-8"))
batches = batches_data.get("batches", batches_data)
total_batches = len(batches)

# Curated high-accuracy metadata for GroundMark files
FILE_META = {
    # Core src
    "src/__init__.py": {
        "summary": "Root package initialization file for GroundMark document layout and chat analysis.",
        "tags": ["entry-point", "barrel", "package-root"]
    },
    "src/chat.py": {
        "summary": "Multi-turn document conversational question answering with citation verification and structured reasoning.",
        "tags": ["chat", "llm", "qa", "verification", "citations"]
    },
    "src/graph.py": {
        "summary": "Stateful document processing graph orchestrating preprocessing, parsing, and markdown generation.",
        "tags": ["orchestration", "state-machine", "pipeline", "workflow"]
    },
    "src/models.py": {
        "summary": "Pydantic data models for bounding boxes, layout blocks, parsed document pages, and chat messages.",
        "tags": ["data-model", "pydantic", "schema", "validation"]
    },
    "src/ui/app.py": {
        "summary": "Interactive Streamlit application providing document inspection, bounding box visualization, and chat.",
        "tags": ["ui", "streamlit", "frontend", "inspection", "chat"]
    },
    "src/ui/clipboard.py": {
        "summary": "Clipboard helper module for copying markdown and chat answers directly to system clipboard.",
        "tags": ["utility", "clipboard", "ui-helper"]
    },
    "src/ui/__init__.py": {
        "summary": "UI package initialization exposing UI components and helpers.",
        "tags": ["ui", "barrel", "package-init"]
    },
    "src/usage.py": {
        "summary": "Token usage ledger tracking prompt and completion tokens with USD cost computation.",
        "tags": ["usage", "telemetry", "cost-tracking", "metrics"]
    },
    "src/annotate.py": {
        "summary": "Renders bounding boxes and layout classification overlays on PDF pages and images.",
        "tags": ["annotation", "visualization", "pdf", "image-processing"]
    },
    "src/figures.py": {
        "summary": "Extracts, crops, and persists image figures and tables from parsed document regions.",
        "tags": ["image-processing", "figure-extraction", "cropping", "artifacts"]
    },
    "src/layout.py": {
        "summary": "Core layout analysis engine detecting reading order, columns, headers, tables, and bounding boxes.",
        "tags": ["layout-analysis", "document-parser", "reading-order", "ocr"]
    },
    "src/markdown.py": {
        "summary": "Converts structured layout elements and table grids into clean, human-readable GitHub-flavored markdown.",
        "tags": ["markdown", "serialization", "table-formatting", "text-generation"]
    },
    "src/preprocess.py": {
        "summary": "Prepares and normalizes input documents, handling PDF rasterization, image resizing, and base64 encoding.",
        "tags": ["preprocessing", "pdf-rasterization", "image-resizing", "normalization"]
    },
    "src/diagnostics.py": {
        "summary": "Tracks API response health, token usage per call, error classification, and content filter violations.",
        "tags": ["diagnostics", "telemetry", "safety-filters", "monitoring"]
    },
    "src/llm.py": {
        "summary": "Low-level LLM client wrapper configuring OpenAI/vLLM clients with structured outputs and retry policies.",
        "tags": ["llm-client", "openai-api", "structured-outputs", "retry-logic"]
    },
    "src/parse.py": {
        "summary": "High-level parsing facade coordinating document preparation, model inference, and output formatting.",
        "tags": ["parser-facade", "inference", "document-processing"]
    },
    "src/prompts.py": {
        "summary": "Prompt template loader resolving system instructions and user templates from the prompts directory.",
        "tags": ["prompt-engineering", "template-loader", "configuration"]
    },
    # Scripts
    "scripts/evaluate_chat.py": {
        "summary": "CLI evaluation script running automated document question answering benchmarks against ground truth.",
        "tags": ["evaluation", "benchmark", "chat-eval", "cli"]
    },
    "scripts/evaluate_layout.py": {
        "summary": "Evaluates layout detection accuracy against annotated ground truth across multiple document types.",
        "tags": ["evaluation", "layout-eval", "metrics", "cli"]
    },
    "scripts/evaluate_prompts.py": {
        "summary": "Compares layout extraction quality and token efficiency across different prompt template variations.",
        "tags": ["evaluation", "prompt-comparison", "ab-testing", "cli"]
    },
    "scripts/evaluate_resolution.py": {
        "summary": "Benchmarks layout parsing precision and latency across different image resolution settings.",
        "tags": ["evaluation", "resolution-benchmark", "latency", "cli"]
    },
    # Tests
    "tests/__init__.py": {
        "summary": "Test package root initialization.",
        "tags": ["test", "package-init"]
    },
    "tests/fake_llm.py": {
        "summary": "Mock LLM client fixture providing deterministic responses for unit and integration testing.",
        "tags": ["test-fixture", "mock", "llm-mock"]
    },
    "tests/fixtures/make_invoice_png.py": {
        "summary": "Fixture script dynamically generating synthetic invoice images with predictable layout elements.",
        "tags": ["test-fixture", "synthetic-data", "image-generation"]
    },
    "tests/fixtures/chat-evaluation.md": {
        "summary": "Golden evaluation dataset containing QA pairs and expected citations for chat benchmark tests.",
        "tags": ["test-data", "benchmark", "golden-set"]
    },
    "tests/fixtures/.gitkeep": {
        "summary": "Directory marker preserving the fixtures folder in git.",
        "tags": ["configuration", "git"]
    },
    "tests/test_annotate.py": {
        "summary": "Unit tests verifying PDF and image bounding box rendering, clipping, and color assignment.",
        "tags": ["test", "annotation", "unit-test"]
    },
    "tests/test_chat.py": {
        "summary": "Tests for document chat pipeline, conversational context handling, and citation verification.",
        "tags": ["test", "chat", "citation-verification"]
    },
    "tests/test_diagnostics.py": {
        "summary": "Tests for content filter detection, error formatting, and diagnostic telemetry capture.",
        "tags": ["test", "diagnostics", "safety-filters"]
    },
    "tests/test_graph.py": {
        "summary": "Tests for document pipeline state graph execution, state transitions, and artifact storage.",
        "tags": ["test", "state-machine", "workflow"]
    },
    "tests/test_launcher.py": {
        "summary": "Tests launcher script behavior, environment validation, and dependency installation checks.",
        "tags": ["test", "launcher", "bootstrap"]
    },
    "tests/test_layout_evaluation.py": {
        "summary": "Tests for layout evaluation runner, IoU computation, and scoring thresholds.",
        "tags": ["test", "layout-eval", "metrics"]
    },
    "tests/test_layout_structure.py": {
        "summary": "Verifies layout block hierarchy, reading order sorting, and column boundary detection.",
        "tags": ["test", "layout-structure", "reading-order"]
    },
    "tests/test_markdown.py": {
        "summary": "Tests markdown generation from layout blocks, table serialization, and heading levels.",
        "tags": ["test", "markdown", "serialization"]
    },
    "tests/test_parse.py": {
        "summary": "Tests high-level document parser orchestration, multi-page parsing, and fallback behaviors.",
        "tags": ["test", "document-parser", "integration-test"]
    },
    "tests/test_preprocess.py": {
        "summary": "Tests image deskewing, resizing, base64 encoding, and PDF page rasterization.",
        "tags": ["test", "preprocessing", "image-processing"]
    },
    "tests/test_prompt_evaluation.py": {
        "summary": "Tests prompt evaluation scoring algorithms and token comparison logic.",
        "tags": ["test", "prompt-evaluation", "metrics"]
    },
    "tests/test_prompts.py": {
        "summary": "Verifies prompt template loading, variable substitution, and schema validation.",
        "tags": ["test", "prompt-template", "validation"]
    },
    "tests/test_resolution_evaluation.py": {
        "summary": "Tests resolution benchmark metrics, execution limits, and scoring formulas.",
        "tags": ["test", "resolution-benchmark", "metrics"]
    },
    "tests/test_ui_diagnostics.py": {
        "summary": "Tests UI error reporting, diagnostic panel display, and session state persistence.",
        "tags": ["test", "ui", "diagnostics"]
    },
    "tests/test_usage.py": {
        "summary": "Tests token usage accumulation, ledger calculations, and cost estimation formulas.",
        "tags": ["test", "usage-tracking", "cost-accounting"]
    },
    # Root configs & docs
    ".env.example": {
        "summary": "Example environment file detailing API keys and runtime configuration parameters.",
        "tags": ["configuration", "environment", "secrets-template"]
    },
    "README.md": {
        "summary": "Main project documentation detailing GroundMark architecture, installation, quickstart, and features.",
        "tags": ["documentation", "entry-point", "overview"]
    },
    "requirements.txt": {
        "summary": "Production Python dependencies defining packages required for running GroundMark core and UI.",
        "tags": ["configuration", "dependencies", "python", "packaging"]
    },
    "requirements-dev.txt": {
        "summary": "Development and testing dependencies including pytest, coverage, and linting tools.",
        "tags": ["configuration", "dev-dependencies", "testing", "linting"]
    },
    "run.cmd": {
        "summary": "Windows batch launcher script setting up virtual environment and launching the Streamlit UI.",
        "tags": ["script", "launcher", "windows-cli"]
    },
    "groundmark-architecture.html": {
        "summary": "Standalone interactive architectural visualization and component dependency diagram.",
        "tags": ["architecture", "visualization", "interactive-diagram"]
    },
    "groundmark-architecture.json": {
        "summary": "Structured architecture model specification describing GroundMark subsystems and flows.",
        "tags": ["architecture", "specification", "configuration"]
    },
    "groundmark-architecture.visual-check.html": {
        "summary": "Multi-viewport responsive preview contact sheet for architecture diagram verification.",
        "tags": ["visualization", "responsive-testing", "qa"]
    },
    "groundmark-architecture.visual-check.json": {
        "summary": "Test run configuration and viewport dimensions for architecture visual verification.",
        "tags": ["configuration", "test-metadata", "viewport-specs"]
    },
    # Docs
    "docs/ARCHITECTURE.md": {
        "summary": "System architecture document explaining pipeline stages, state management, and component responsibilities.",
        "tags": ["documentation", "architecture", "system-design"]
    },
    "docs/COMPLIANCE.md": {
        "summary": "Data privacy and security compliance documentation regarding API transmissions and local retention.",
        "tags": ["documentation", "compliance", "security", "privacy"]
    },
    "docs/CONTENT-FILTER-DIAGNOSTICS.md": {
        "summary": "Technical guide explaining content filter error detection, handling, and UI reporting.",
        "tags": ["documentation", "diagnostics", "content-safety"]
    },
    "docs/CONTRIBUTING.md": {
        "summary": "Contributor guidelines covering development workflow, testing standards, and pull request checklist.",
        "tags": ["documentation", "contributing", "developer-guide"]
    },
    "docs/LAYOUT-EVALUATION.md": {
        "summary": "Evaluation methodology and benchmark protocol for document layout detection accuracy.",
        "tags": ["documentation", "evaluation", "layout-benchmark"]
    },
    "docs/MODEL.md": {
        "summary": "Specifications of vision and language models supported by GroundMark and prompt engineering details.",
        "tags": ["documentation", "models", "vision-llm", "specs"]
    },
    "docs/PROMPT-EVALUATION.md": {
        "summary": "Experimental analysis of prompt variation effects on OCR quality, layout fidelity, and token costs.",
        "tags": ["documentation", "prompt-engineering", "benchmarks"]
    },
    "docs/PROMPTS.md": {
        "summary": "Catalog of prompt templates used across layout parsing, structured extraction, and document QA.",
        "tags": ["documentation", "prompts", "reference"]
    },
    "docs/RUNBOOK.md": {
        "summary": "Operational runbook for deploying, debugging, and running GroundMark locally and in production.",
        "tags": ["documentation", "runbook", "operations", "debugging"]
    },
    "docs/SOL-RESOLUTION-EVALUATION.md": {
        "summary": "Research findings on the trade-offs between image input resolution, OCR quality, and API latency.",
        "tags": ["documentation", "resolution-study", "benchmarks", "vision"]
    },
    # Runtime prompts
    "prompts/runtime/chat-answer.md": {
        "summary": "Runtime prompt instructing the model to generate grounded document answers with page-level citations.",
        "tags": ["prompt-template", "chat", "qa-prompt"]
    },
    "prompts/runtime/chat-verify.md": {
        "summary": "Verification prompt validating answer statements against document evidence and citations.",
        "tags": ["prompt-template", "verification", "fact-checking"]
    },
    "prompts/runtime/parse-page-structured.md": {
        "summary": "Structured JSON output prompt requesting strict bounding box coordinates and block types.",
        "tags": ["prompt-template", "layout-parsing", "structured-output"]
    },
    "prompts/runtime/parse-page.md": {
        "summary": "Standard vision layout analysis prompt instructing model to identify blocks, reading order, and text.",
        "tags": ["prompt-template", "layout-parsing", "vision-prompt"]
    },
    # UA artifacts
    ".ua/.understandignore": {
        "summary": "Ignore patterns for Understand-Anything codebase scanning and analysis.",
        "tags": ["configuration", "understand-anything", "ignore-rules"]
    },
    ".ua/intermediate/batches.json": {
        "summary": "Semantic batching manifest splitting the codebase into 9 coherent analysis batches.",
        "tags": ["configuration", "understand-anything", "batch-manifest"]
    },
    ".ua/intermediate/scan-result.json": {
        "summary": "Full project inventory produced by scan-project.mjs containing 70 detected files and import map.",
        "tags": ["configuration", "understand-anything", "inventory"]
    },
    ".ua/tmp/ua-import-map-input.json": {
        "summary": "Intermediate input file for import map resolution.",
        "tags": ["configuration", "temporary", "build-artifact"]
    },
    ".ua/tmp/ua-import-map-output.json": {
        "summary": "Intermediate output file containing resolved project import graph.",
        "tags": ["configuration", "temporary", "build-artifact"]
    },
    ".ua/tmp/ua-scan-files.json": {
        "summary": "Temporary file list collected during repository scan phase.",
        "tags": ["configuration", "temporary", "build-artifact"]
    }
}

# Function/Class summary generator helper
def get_symbol_summary(file_path: str, name: str, is_func: bool) -> tuple[str, list[str]]:
    kind = "function" if is_func else "class"
    clean_name = name.replace("_", " ").title()
    summary = f"{clean_name} {kind} in {Path(file_path).name} supporting {Path(file_path).stem} operations."
    tags = [kind, Path(file_path).stem.replace("_", "-"), "groundmark"]
    return summary, tags

print("Starting batch synthesis...")

for batch_idx in range(total_batches):
    batch = batches[batch_idx]
    batch_files = batch.get("files", [])
    batch_import_data = batch.get("batchImportData", {})
    neighbor_map = batch.get("neighborMap", {})
    
    extract_file = TMP / f"ua-file-extract-results-{batch_idx}.json"
    extract_data = {}
    if extract_file.exists():
        extract_data = json.loads(extract_file.read_text(encoding="utf-8"))
    
    results_by_path = {r["path"]: r for r in extract_data.get("results", [])}
    
    nodes = []
    edges = []
    
    for f in batch_files:
        path = f["path"]
        cat = f.get("fileCategory", "code")
        size = f.get("sizeLines", 0)
        
        # Node Type
        if cat == "code":
            node_type = "file"
            prefix = "file"
        elif cat == "config":
            node_type = "config"
            prefix = "config"
        elif cat == "docs":
            node_type = "document"
            prefix = "document"
        elif cat == "script":
            node_type = "file"
            prefix = "file"
        elif cat == "markup":
            node_type = "file"
            prefix = "file"
        else:
            node_type = "file"
            prefix = "file"
            
        node_id = f"{prefix}:{path}"
        complexity = "simple" if size < 50 else ("moderate" if size <= 200 else "complex")
        
        meta = FILE_META.get(path, {
            "summary": f"{Path(path).name} provides {cat} specifications for the GroundMark project.",
            "tags": [cat, "groundmark", Path(path).suffix.replace(".", "") or "file"]
        })
        
        file_node = {
            "id": node_id,
            "type": node_type,
            "name": Path(path).name,
            "filePath": path,
            "summary": meta["summary"],
            "tags": meta["tags"],
            "complexity": complexity
        }
        nodes.append(file_node)
        
        # Sub-nodes (functions and classes for code files)
        extract_res = results_by_path.get(path, {})
        functions = extract_res.get("functions", [])
        classes = extract_res.get("classes", [])
        exports = {exp["name"] for exp in extract_res.get("exports", [])}
        
        created_funcs = {}
        for func in functions:
            fname = func["name"]
            st = func["startLine"]
            en = func["endLine"]
            f_len = en - st + 1
            # Significance filter: len >= 10 or exported or core API
            if f_len >= 10 or fname in exports or not fname.startswith("_"):
                func_id = f"function:{path}:{fname}"
                f_comp = "simple" if f_len < 50 else ("moderate" if f_len <= 200 else "complex")
                f_sum, f_tags = get_symbol_summary(path, fname, True)
                if fname.startswith("test_"):
                    f_tags = ["test", "unit-test", Path(path).stem.replace("_", "-")]
                nodes.append({
                    "id": func_id,
                    "type": "function",
                    "name": fname,
                    "filePath": path,
                    "lineRange": [st, en],
                    "summary": f_sum,
                    "tags": f_tags,
                    "complexity": f_comp
                })
                created_funcs[fname] = func_id
                
                # contains edge
                edges.append({
                    "source": node_id,
                    "target": func_id,
                    "type": "contains",
                    "direction": "forward",
                    "weight": 1.0
                })
                
                # exports edge
                if fname in exports:
                    edges.append({
                        "source": node_id,
                        "target": func_id,
                        "type": "exports",
                        "direction": "forward",
                        "weight": 0.8
                    })
                    
        for cls in classes:
            cname = cls["name"]
            st = cls["startLine"]
            en = cls["endLine"]
            c_len = en - st + 1
            methods = cls.get("methods", [])
            # Significance filter: len >= 20 or len(methods) >= 2 or exported
            if c_len >= 20 or len(methods) >= 2 or cname in exports:
                cls_id = f"class:{path}:{cname}"
                c_comp = "simple" if c_len < 50 else ("moderate" if c_len <= 200 else "complex")
                c_sum, c_tags = get_symbol_summary(path, cname, False)
                nodes.append({
                    "id": cls_id,
                    "type": "class",
                    "name": cname,
                    "filePath": path,
                    "lineRange": [st, en],
                    "summary": c_sum,
                    "tags": c_tags,
                    "complexity": c_comp
                })
                # contains edge
                edges.append({
                    "source": node_id,
                    "target": cls_id,
                    "type": "contains",
                    "direction": "forward",
                    "weight": 1.0
                })
                if cname in exports:
                    edges.append({
                        "source": node_id,
                        "target": cls_id,
                        "type": "exports",
                        "direction": "forward",
                        "weight": 0.8
                    })
                    
        # 1:1 emission for batchImportData
        file_imports = batch_import_data.get(path, [])
        for imp_path in file_imports:
            edges.append({
                "source": node_id,
                "target": f"file:{imp_path}",
                "type": "imports",
                "direction": "forward",
                "weight": 0.7
            })
            
        # Call graph edges
        call_graph = extract_res.get("callGraph", [])
        for call in call_graph:
            caller = call.get("caller")
            callee = call.get("callee")
            if caller in created_funcs:
                caller_id = created_funcs[caller]
                # local function call
                if callee in created_funcs:
                    edges.append({
                        "source": caller_id,
                        "target": created_funcs[callee],
                        "type": "calls",
                        "direction": "forward",
                        "weight": 0.8
                    })
                # check if callee in neighborMap symbols
                for f_key, n_list in neighbor_map.items():
                    if isinstance(n_list, list):
                        for n_info in n_list:
                            if isinstance(n_info, dict):
                                n_path = n_info.get("path", "")
                                n_symbols = n_info.get("symbols", [])
                                if callee in n_symbols:
                                    target_prefix = "class" if callee[0].isupper() else "function"
                                    edges.append({
                                        "source": caller_id,
                                        "target": f"{target_prefix}:{n_path}:{callee}",
                                        "type": "calls",
                                        "direction": "forward",
                                        "weight": 0.8
                                    })
                                    break
                        
        # tested_by edges for test files
        if path.startswith("tests/test_"):
            base_name = path[len("tests/test_"):-3] # e.g. "chat"
            candidates = [
                f"src/{base_name}.py",
                f"scripts/evaluate_{base_name}.py",
                f"src/ui/{base_name}.py"
            ]
            if base_name == "layout_structure" or base_name == "layout_evaluation":
                candidates.append("src/layout.py")
                candidates.append("scripts/evaluate_layout.py")
            elif base_name == "resolution_evaluation":
                candidates.append("scripts/evaluate_resolution.py")
            elif base_name == "prompt_evaluation":
                candidates.append("scripts/evaluate_prompts.py")
            elif base_name == "ui_diagnostics":
                candidates.append("src/diagnostics.py")
                candidates.append("src/ui/app.py")
            elif base_name == "launcher":
                candidates.append("run.cmd")
                
            for cand in candidates:
                if (PROJECT_ROOT / cand).exists():
                    edges.append({
                        "source": f"file:{cand}",
                        "target": f"file:{path}",
                        "type": "tested_by",
                        "direction": "forward",
                        "weight": 0.5
                    })

        # Non-code semantic edges
        if path == "README.md":
            for target in ["src/parse.py", "src/ui/app.py", "src/chat.py", "src/layout.py"]:
                edges.append({
                    "source": "document:README.md",
                    "target": f"file:{target}",
                    "type": "documents",
                    "direction": "forward",
                    "weight": 0.5
                })
        elif path.startswith("docs/"):
            doc_stem = Path(path).stem.lower()
            if "layout" in doc_stem:
                edges.append({"source": f"document:{path}", "target": "file:src/layout.py", "type": "documents", "direction": "forward", "weight": 0.5})
                edges.append({"source": f"document:{path}", "target": "file:scripts/evaluate_layout.py", "type": "documents", "direction": "forward", "weight": 0.5})
            elif "prompt" in doc_stem:
                edges.append({"source": f"document:{path}", "target": "file:src/prompts.py", "type": "documents", "direction": "forward", "weight": 0.5})
                edges.append({"source": f"document:{path}", "target": "file:scripts/evaluate_prompts.py", "type": "documents", "direction": "forward", "weight": 0.5})
            elif "resolution" in doc_stem:
                edges.append({"source": f"document:{path}", "target": "file:src/preprocess.py", "type": "documents", "direction": "forward", "weight": 0.5})
                edges.append({"source": f"document:{path}", "target": "file:scripts/evaluate_resolution.py", "type": "documents", "direction": "forward", "weight": 0.5})
            elif "filter" in doc_stem or "diagnostics" in doc_stem:
                edges.append({"source": f"document:{path}", "target": "file:src/diagnostics.py", "type": "documents", "direction": "forward", "weight": 0.5})
            elif "arch" in doc_stem:
                edges.append({"source": f"document:{path}", "target": "file:src/graph.py", "type": "documents", "direction": "forward", "weight": 0.5})
                edges.append({"source": f"document:{path}", "target": "file:src/layout.py", "type": "documents", "direction": "forward", "weight": 0.5})
            elif "model" in doc_stem:
                edges.append({"source": f"document:{path}", "target": "file:src/models.py", "type": "documents", "direction": "forward", "weight": 0.5})
                edges.append({"source": f"document:{path}", "target": "file:src/llm.py", "type": "documents", "direction": "forward", "weight": 0.5})
        elif path.startswith("prompts/runtime/"):
            edges.append({"source": f"document:{path}", "target": "file:src/prompts.py", "type": "defines_schema", "direction": "forward", "weight": 0.8})
        elif path == "requirements.txt":
            edges.append({"source": "document:requirements.txt", "target": "file:src/__init__.py", "type": "configures", "direction": "forward", "weight": 0.6})
        elif path == "requirements-dev.txt":
            edges.append({"source": "document:requirements-dev.txt", "target": "file:tests/__init__.py", "type": "configures", "direction": "forward", "weight": 0.6})
        elif path == ".env.example":
            edges.append({"source": "config:.env.example", "target": "file:src/chat.py", "type": "configures", "direction": "forward", "weight": 0.6})
        elif path == "run.cmd":
            edges.append({"source": "file:run.cmd", "target": "file:src/ui/app.py", "type": "triggers", "direction": "forward", "weight": 0.6})

    batch_output = {
        "batchIndex": batch_idx,
        "totalBatches": total_batches,
        "nodes": nodes,
        "edges": edges
    }
    
    out_file = INTERMEDIATE / f"batch-{batch_idx}.json"
    out_file.write_text(json.dumps(batch_output, indent=2), encoding="utf-8")
    print(f"Wrote batch {batch_idx}: {len(nodes)} nodes, {len(edges)} edges -> {out_file.name}")

print("Batch generation complete!")
