# Graph Report - GroundMark  (2026-09-27)

## Corpus Check
- Large corpus: 321 files · ~768,441 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 1302 nodes · 3414 edges · 93 communities (76 shown, 17 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 277 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

Token accounting: the Gemini credential was rejected, so 70 uncached content files were processed by agent-based extraction. Agent token usage was unavailable to Graphify; the recorded 0/0 is **unmetered**, not zero consumption.

Graph health: the extraction diagnostic found 306 dangling-endpoint edges, 6 self-loops, 289 directed and 290 undirected same-endpoint edge collapses. The graph is navigable, but these counts limit completeness and relation fidelity.

## Community Hubs (Navigation)
- Document Run Pipeline
- PDF Image Dependencies
- CLI HTML Dependencies
- Layout Reconciliation Policy
- Architecture Tooling Batch
- Diagnostic Data Models
- Architecture Diagram Images
- Reconciliation Test Fixtures
- Streamlit Clipboard Inspection
- Architecture Documentation
- Interactive Diagram Set
- Document Evidence Chat
- CLI Extraction Tests
- LangGraph Chat Integration
- Layout Runtime Configuration
- Structured Parse Models
- Offline Layout Evaluation
- Layout Guide Projection
- Graph Execution Pipeline
- Layout Detector Tests
- Chat Evaluation Scripts
- Evaluation Metrics Utilities
- Network Configuration Safety
- Document Export Pipeline
- Evaluation Scripts Index
- Prompt Context Construction
- Layout Integration Tests
- Runtime Prompt Loading
- Usage Ledger Display
- HTML Rendering Models
- ONNX Layout Decoder
- Structured Layout Tests
- Graph Build Automation
- Evaluation Replay Artifacts
- Polygon Geometry Helpers
- Document Page Evidence
- Diagnostic Integration Tests
- CLI Environment Loading
- Output File Naming
- Runtime Device Protocol
- Graph Incremental Merge
- Graph Batch Generation
- Annotation Geometry Rendering
- Chat Provider Filters
- Release Artifact Checks
- Layout Failure Diagnostics
- Detector Runtime Recovery
- Reconciliation Invariants
- Fallback Integration Tests
- Graph Import Analysis
- Table Cell Validation
- Architecture Layer Assignment
- Page Artifact Concepts
- Document Answer Policy
- Graph Build Metadata
- Artifact Reference Validation
- Graph Save Preparation
- Graph Tool Scratch Files
- Graph Scan Assembly
- ONNX Error Boundary Tests
- Architecture Input Builder
- Architecture Image Checks
- Dataflow Image Checks
- Lifecycle Image Checks
- Sequence Image Checks
- Workflow Image Checks
- Architecture Analyzer Tool
- Legacy Table Safeguards
- Tensor Conversion Helpers
- Graph Tour Builder
- Python Project Dependencies
- Sample Invoice Evidence
- Unexpected Graph Failures
- Table Rectangularization
- OKF Project Knowledge
- Evidence Approval Policy
- Label Validation Logic
- Launcher Integration Tests
- Detector Execution Backend
- Graph Node Utilities
- CI Release Workflows
- Local Remote Data Boundary
- Source Package Marker
- UI Package Marker
- Test Package Marker
- Graph Edge Helpers
- Dependabot Updates
- Changed Files Manifest
- Changed File Inventory
- OpenWiki Agent Instructions
- OpenWiki Guide Reference
- Content Filter Diagnostics
- Project Root Node

## God Nodes (most connected - your core abstractions)
1. `ParsePage` - 77 edges
2. `ParseResult` - 77 edges
3. `ParseBlock` - 47 edges
4. `region()` - 45 edges
5. `convert_layout()` - 39 edges
6. `parse_document()` - 38 edges
7. `block()` - 36 edges
8. `reconcile_page()` - 35 edges
9. `parse_to_markdown()` - 35 edges
10. `parse_to_html()` - 33 edges

## Surprising Connections (you probably didn't know these)
- `GroundMark architecture diagram` --semantically_similar_to--> `Extraction pipeline`  [INFERRED] [semantically similar]
  docs/diagrams/groundmark-architecture.html → openwiki/architecture/extraction-pipeline.md
- `GroundMark extraction data flow` --semantically_similar_to--> `Extraction pipeline`  [INFERRED] [semantically similar]
  docs/diagrams/groundmark-dataflow.html → openwiki/architecture/extraction-pipeline.md
- `GroundMark parsing workflow` --semantically_similar_to--> `Extraction pipeline`  [INFERRED] [semantically similar]
  docs/diagrams/groundmark-workflow.html → openwiki/architecture/extraction-pipeline.md
- `Whole-page visual parsing` --semantically_similar_to--> `Sol parsing and Luna chat model contract`  [INFERRED] [semantically similar]
  README.md → docs/MODEL.md
- `GroundMark execution lifecycle` --semantically_similar_to--> `Partial-safe page extraction`  [INFERRED] [semantically similar]
  docs/diagrams/groundmark-lifecycle.html → openwiki/architecture/extraction-pipeline.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **ParsePage Cross Cutting Bridge** — graphify_out_memory_query_20260923_085416_4fb1df1d_why_does_parsepage_act_as_the_primary_cross_cuttin_parsepage, graphify_out_memory_query_20260923_085416_4fb1df1d_why_does_parsepage_act_as_the_primary_cross_cuttin_parseblock, graphify_out_memory_query_20260923_085416_4fb1df1d_why_does_parsepage_act_as_the_primary_cross_cuttin_rendering, graphify_out_memory_query_20260923_085416_4fb1df1d_why_does_parsepage_act_as_the_primary_cross_cuttin_chat_evidence, graphify_out_memory_query_20260923_085416_4fb1df1d_why_does_parsepage_act_as_the_primary_cross_cuttin_evaluation_harnesses [EXTRACTED 1.00]
- **GroundMark page parse path** — docs_architecture_page_pipeline, docs_layout_v3_authoritative_reconciliation, readme_visual_parsing, docs_prompts_prompt_contract [EXTRACTED 1.00]
- **Page extraction views** — docs_diagrams_groundmark_architecture_groundmark_architecture, docs_diagrams_groundmark_dataflow_groundmark_data_flow, docs_diagrams_groundmark_workflow_groundmark_parsing_workflow, openwiki_architecture_extraction_pipeline_extraction_pipeline [INFERRED 0.85]
- **Layout evidence views** — docs_v3_integration_completion_v3_onnx_integration_completion, openwiki_concepts_layout_v3_pp_doclayoutv3_detection_and_reconciliation, openwiki_testing_verification_tests_and_evaluation_boundaries [INFERRED 0.85]

## Communities (93 total, 17 thin omitted)

### Community 0 - "Document Run Pipeline"
Cohesion: 0.07
Nodes (48): GraphState, node_preprocess(), Run inputs, parser diagnostics, usage ledger, and selected artifact paths., Validate/hash the input and establish run identity and export ownership. Accept…, _cap_long_edge(), count_pages(), inspect_source(), _iter_pdf_pages() (+40 more)

### Community 1 - "PDF Image Dependencies"
Cohesion: 0.08
Nodes (38): base64, hashlib, io, pil, pypdfium2, _bbox_is_valid(), Draw reconciled full contours and explicit detector-only inspection overlays.…, max_figure_bytes() (+30 more)

### Community 2 - "CLI HTML Dependencies"
Cohesion: 0.09
Nodes (25): argparse, Counter, html_parser, HTMLParser, openai, Paid Sol profile comparison; token F1 does not measure V3 correspondence,…, main(), plain_text() (+17 more)

### Community 3 - "Layout Reconciliation Policy"
Cohesion: 0.13
Nodes (28): collections, math, BlockDecision, GuideContour, _LayoutMetadata, MatchEvidence, NormalizedLayoutPage, NormalizedLayoutRegion (+20 more)

### Community 4 - "Architecture Tooling Batch"
Cohesion: 0.06
Nodes (32): annotateFile, annotateFn, archDoc, archIndex, bboxFn, buildFn, chatDoc, claim (+24 more)

### Community 5 - "Diagnostic Data Models"
Cohesion: 0.11
Nodes (24): ExtractionCallError, FilterAnnotation, PageDiagnostic, BaseModel, A failed extraction call carrying a safe PageDiagnostic., ParsePage, Check at the page boundary as well as when loading an artifact., FakeLLM (+16 more)

### Community 6 - "Architecture Diagram Images"
Cohesion: 0.11
Nodes (30): architecture diagram (dark visual check), architecture diagram (light visual check), architecture diagram (dark visual check), architecture diagram (light visual check), GroundMark architecture: V3 layout, Sol transcription, reconciliation, outputs, and chat, dataflow diagram (dark visual check), dataflow diagram (light visual check), dataflow diagram (dark visual check) (+22 more)

### Community 7 - "Reconciliation Test Fixtures"
Cohesion: 0.22
Nodes (28): LegacyBlock, block(), parametrize, Synthetic offline geometry, matching, and existing-consumer contracts., reconcile(), region(), test_accepted_review_flags_round_trip_and_tampered_evidence_is_rejected(), test_actual_legacy_artifact_fields_load_without_new_policy_reinterpretation() (+20 more)

### Community 8 - "Streamlit Clipboard Inspection"
Cohesion: 0.09
Nodes (18): Clipboard controls for Markdown and JSON artifacts. Must not: assign…, streamlit, streamlit_testing_v1, fixture, parametrize, AppTest regressions: Sol only, upload identity, and rerun-safe previews., test_chat_submission_reruns_and_reset(), test_cpu_recovery_updates_readiness_on_reruns_without_inference() (+10 more)

### Community 9 - "Architecture Documentation"
Cohesion: 0.09
Nodes (29): GroundMark architecture, Sol fallback after layout failure, Preprocess parse and export pipeline, Contributor contracts, Contributor change and review runbook, Developer guide, Page processing ownership boundaries, Detailed layout remains experimental (+21 more)

### Community 10 - "Interactive Diagram Set"
Cohesion: 0.09
Nodes (29): GroundMark architecture diagram, GroundMark extraction data flow, GroundMark execution lifecycle, GroundMark parse and chat sequence, GroundMark parsing workflow, ONNX graph and official decode parity, Unmeasured correspondence and order quality, V3 ONNX integration completion (+21 more)

### Community 11 - "Document Evidence Chat"
Cohesion: 0.16
Nodes (24): httpx, answer_document_question(), ChatResult, Answer from parsed evidence, with local quote checks and Luna verification.…, User-facing answer/status with per-call usage and safe diagnostics., client_for(), document(), draft() (+16 more)

### Community 12 - "CLI Extraction Tests"
Cohesion: 0.12
Nodes (22): main(), Launch the UI or extract a document using parsed CLI arguments. argv defaults…, extraction(), page(), fixture, parametrize, Exercise real preprocessing and exports without model requests., test_env_file_and_environment_precedence() (+14 more)

### Community 13 - "LangGraph Chat Integration"
Cohesion: 0.12
Nodes (22): langgraph_config, langgraph_graph, re, _call(), Draft, Evidence, _normalize(), _payload() (+14 more)

### Community 14 - "Layout Runtime Configuration"
Cohesion: 0.12
Nodes (20): FallbackReason, detector(), layout_config(), LayoutConfig, V3 device policy and optional verified local model directory., Read only when the standalone layout runtime is requested., Path, Reuse a complete pinned user-cache snapshot; download only on a miss. (+12 more)

### Community 15 - "Structured Parse Models"
Cohesion: 0.19
Nodes (24): html, max_table_cells(), Return the positive expanded-table cell budget; invalid settings raise…, ParseBlock, TableCell, _cell_html(), _cells(), _heading_level() (+16 more)

### Community 16 - "Offline Layout Evaluation"
Cohesion: 0.18
Nodes (23): pydantic, checked_file(), comparison_manifest(), contour_mask_iou(), file_ref(), FileRef, Labels, main() (+15 more)

### Community 17 - "Layout Guide Projection"
Cohesion: 0.19
Nodes (23): page_overlays(), Yield inspection references and geometry; never infer correspondence., convert_layout(), Validate and normalize one runtime result without changing its pixels., test_complex_contour_is_full_when_it_fits_and_simplified_only_for_budget(), test_dense_layout_and_tiny_boxes_fit_without_geometry_mutation(), test_prompt_projection_is_bounded_complete_and_keeps_only_useful_polygons(), page() (+15 more)

### Community 18 - "Graph Execution Pipeline"
Cohesion: 0.11
Nodes (21): build_graph(), node_parse(), Path, Return the compiled preprocess-to-parse graph; construction makes no calls., Run extraction and return final state with diagnostics and artifact paths. Page…, Parse selected pages and export them into GraphState updates. Preserve usable…, run_graph(), End-to-end tests for the active `preprocess -> parse -> END` graph… (+13 more)

### Community 19 - "Layout Detector Tests"
Cohesion: 0.21
Nodes (18): concurrent_futures, FakeBackend, image(), parametrize, Standalone layout tests: injected backends, no weights, downloads, or Sol., runtime(), test_cpu_failure_is_typed_actionable_and_not_cached(), test_cpu_mode_does_not_even_query_cuda() (+10 more)

### Community 20 - "Chat Evaluation Scripts"
Cohesion: 0.14
Nodes (8): json, os, pathlib, main(), Bounded live evaluation using synthetic document data and Markdown cases., Run the synthetic live chat cases and save results; return 0 only if all pass.…, subprocess, Windows launcher delegates environment setup and arguments to uv.

### Community 21 - "Evaluation Metrics Utilities"
Cohesion: 0.13
Nodes (21): compare(), main(), metric_gate(), Path, Parse --live and output arguments, then dispatch the budgeted comparison., Require five complete pairs, no candidate F1 regression, and some improvement., Called only after explicit live authorization; limits may be lowered, not…, corpus() (+13 more)

### Community 22 - "Network Configuration Safety"
Cohesion: 0.18
Nodes (20): dataclasses, ipaddress, ConfigError, is_loopback_host(), max_pages(), ValueError, Validated security limits shared by CLI, UI, and model clients., Return the supplied host, or raise ConfigError for a non-loopback bind. (+12 more)

### Community 23 - "Document Export Pipeline"
Cohesion: 0.15
Nodes (21): Figures, export_result(), write(), Path, Write selected artifacts from one extraction, preserving usable partial output., Write selected artifacts and return paths, warnings, and export errors. source…, _blocks(), markdown_bundle() (+13 more)

### Community 24 - "Evaluation Scripts Index"
Cohesion: 0.14
Nodes (19): scripts, compare(), metric_gate(), Path, Require five paired parsed pages with no per-page candidate F1 regression., Run one authorized baseline/candidate phase and persist its manifest. output is…, LegacyParsePage, Original request contract, retained until detailed extraction passes source… (+11 more)

### Community 25 - "Prompt Context Construction"
Cohesion: 0.13
Nodes (19): collections_abc, HumanMessage, itertools, operator, max_parse_output_tokens(), Return the positive Sol output-token cap; invalid settings raise ConfigError., layout_inspection_summary(), One content-free summary for progress and saved-result inspection. (+11 more)

### Community 26 - "Layout Integration Tests"
Cohesion: 0.23
Nodes (19): copy, payload(), capture_calls(), parametrize, Active-path tests with in-memory V3 and LLM fakes; no paid or local inference., regions(), test_active_graph_reconciles_before_json_annotations_crops_and_chat(), test_cli_reports_safe_device_timings_and_matches() (+11 more)

### Community 27 - "Runtime Prompt Loading"
Cohesion: 0.15
Nodes (17): pytest, Loads a prompt template from prompts/runtime/<name>.md and fills in its…, Load a packaged or checkout template and format the supplied values. name is an…, render_prompt(), fake_layout_runtime(), forbid_native_layout_initialization(), fixture, Opt-in fakes and a guard against accidental native inference in unit tests. (+9 more)

### Community 28 - "Usage Ledger Display"
Cohesion: 0.14
Nodes (19): src, _main(), Display session token totals and estimates, marking unreported usage., show_usage(), cost_usd(), Token/cost accounting using explicitly owned per-run ledgers. The graph owns…, Return a normalized usage entry and append it to entries when supplied.…, Sum token categories from a run/session ledger; unknown usage stays flagged on… (+11 more)

### Community 29 - "HTML Rendering Models"
Cohesion: 0.19
Nodes (19): BlockStructure, _main(), parse_to_html(), Return self-contained escaped HTML, embedding any supplied figure bytes. view…, Validate saved JSON and write adjacent full-view Markdown; return its Path.…, render_and_save(), Tests for src.markdown's Markdown/HTML rendering of a `ParseResult` -- reading…, _sample_result() (+11 more)

### Community 30 - "ONNX Layout Decoder"
Cohesion: 0.13
Nodes (16): _decode_onnx(), LayoutExecutionError, LayoutRegion, Image, Standalone PP-DocLayoutV3 runtime; no parser, UI, or Sol dependencies. Optional…, Validate associated decoded arrays, allowing native rank gaps and ties., Consume all exported outputs with one shared selection/order index., Raised only around native execution, never preprocessing or decoding. (+8 more)

### Community 31 - "Structured Layout Tests"
Cohesion: 0.26
Nodes (19): ListItem, block(), document(), parametrize, Structure contracts and their visible rendering consequences., structure(), test_clean_only_hides_running_furniture_and_chat_keeps_all_text(), test_figure_crop_bundle_and_fallback() (+11 more)

### Community 32 - "Graph Build Automation"
Cohesion: 0.10
Nodes (18): analyzedFiles, batches, commit, duplicateLayerRefs, { execFileSync }, fileLevelIds, finalGraph, fs (+10 more)

### Community 33 - "Evaluation Replay Artifacts"
Cohesion: 0.17
Nodes (18): _Metadata, evaluate(), Persist replay evidence in a new directory; supplied labels are never inferred., LayoutPageArtifact, Reject legacy-only gates and inconsistent active coverage settings. Raises:…, check_reconciliation(), _complex_components(), _rank() (+10 more)

### Community 34 - "Polygon Geometry Helpers"
Cohesion: 0.17
Nodes (16): cv2, numpy, angle_between_vectors(), extract_custom_vertices(), extract_polygon_points_by_masks(), is_convex(), mask2polygon(), _normalize_layout_polygon() (+8 more)

### Community 35 - "Document Page Evidence"
Cohesion: 0.18
Nodes (13): document_pages(), Return nonempty text/table evidence keyed by successful source page. Accept a…, LayoutInferenceError, LayoutPageResult, LayoutReadiness, Actual verified device, CPU fallback reason, preparation time, and reuse., Safe page failure; only native execution errors qualify for recovery., One page's immutable pixel regions and runtime/model provenance. (+5 more)

### Community 36 - "Diagnostic Integration Tests"
Cohesion: 0.31
Nodes (15): call_response(), completion(), invoke(), parametrize, Tests for src.llm's `_invoke_structured` diagnostic mapping and the secret-…, test_create_retains_strict_schema_messages_settings_and_usage(), test_http_errors_are_safe_and_not_retried(), test_live_evaluator_disables_retries_on_actual_client() (+7 more)

### Community 37 - "CLI Environment Loading"
Cohesion: 0.15
Nodes (14): contextlib, dotenv, importlib_metadata, _extract(), _print_progress(), Launch the UI or extract a document using the installed application., Only local status values and counts enter stderr, never page content., layout_ready_summary() (+6 more)

### Community 38 - "Output File Naming"
Cohesion: 0.22
Nodes (14): datetime, _occupied(), Path, Original source names and UTC timestamps for generated artifacts., Return a Windows-safe source stem, bounded to 120 characters., Reserve one output family across concurrent writers; retain no lock on success., reserve_basename(), source_stem() (+6 more)

### Community 39 - "Runtime Device Protocol"
Cohesion: 0.14
Nodes (6): Device, Protocol, LayoutBackend, _OnnxBackend, Inject this small backend contract instead of importing ML libraries., test_onnx_provider_must_be_present_and_have_actual_graph_assignment()

### Community 40 - "Graph Incremental Merge"
Cohesion: 0.12
Nodes (15): batches, changed, covered, edges, expected, fs, intermediate, missingBatches (+7 more)

### Community 41 - "Graph Batch Generation"
Cohesion: 0.13
Nodes (14): batch, batches, chunkSize, edges, extracted, fileInfo, filePaths, functionSummaries (+6 more)

### Community 42 - "Annotation Geometry Rendering"
Cohesion: 0.29
Nodes (12): annotate_document(), Path, Draw selected geometry and return optional PDF and metadata Paths. Pillow…, BBox, ParseResult, BaseModel, Tests for src.annotate's PDF/PNG box-drawing -- feeds `ParseResult` fixtures…, test_annotated_pdf_is_created() (+4 more)

### Community 43 - "Chat Provider Filters"
Cohesion: 0.22
Nodes (12): ChatOpenAI, langchain_core_messages, langchain_openai, filter_annotations(), Extract recognized category annotations from a provider metadata dictionary.…, _build_llm(), ExtractConfigError, _invoke_structured() (+4 more)

### Community 44 - "Release Artifact Checks"
Cohesion: 0.23
Nodes (12): _check(), _check_bytes(), main(), _manifest(), Path, Check the exact release manifest and source/prompt bytes against the checkout., Verify one wheel and sdist in directory against checkout bytes and manifest.…, tarfile (+4 more)

### Community 45 - "Layout Failure Diagnostics"
Cohesion: 0.18
Nodes (11): LayoutStage, layout_failure_diagnostic(), layout_failure_summary(), Exception, Actionable display text generated only from validated codes., Map local failures to allowlisted metadata, retaining any paid-call usage., LayoutModelUnavailable, RuntimeError (+3 more)

### Community 46 - "Detector Runtime Recovery"
Cohesion: 0.22
Nodes (7): get_layout_runtime(), LayoutRuntime, Lazy, serialized predictor with injected model resolution and backend., Verify initialization/device once, before any paid page requests., Analyze one PIL image; return pixel regions and the actual device. Preparation…, One runtime per process; restart the process to change configuration., test_missing_dependencies_are_typed_and_actionable()

### Community 47 - "Reconciliation Invariants"
Cohesion: 0.22
Nodes (10): LayoutConversionError, RuntimeError, ValueError, Application defect, never an ordinary detector miss., Safe failure with no source text or native/provider exception details., ReconciliationInvariantError, parametrize, test_replay_distinguishes_fallback_from_application_defect() (+2 more)

### Community 48 - "Fallback Integration Tests"
Cohesion: 0.31
Nodes (9): build(), sol_page(), test_cli_fallback_is_visible_and_successful(), test_direct_page_falls_back_except_for_invalid_image(), test_graph_surfaces_initialization_remediation_without_gui_changes(), test_initialization_failure_uses_sol_without_retrying_v3(), test_legacy_json_loading_and_strict_schemas_remain_unchanged(), test_preflight_failure_passed_to_graph_does_not_retry_initialization() (+1 more)

### Community 49 - "Graph Import Analysis"
Cohesion: 0.22
Nodes (6): ref_node_fs, fs, input, scan, fs, [inputPath, outputPath]

### Community 50 - "Table Cell Validation"
Cohesion: 0.22
Nodes (8): expanded_table_cells(), Count cells after rectangular padding, including omitted trailing blanks., _main(), parse_document(), parse_payload(), Path, Layout-parse every page in [start_page, end_page] (1-based, inclusive;…, test_reconciliation_failure_retains_sol_page_and_paid_usage()

### Community 51 - "Architecture Layer Assignment"
Cohesion: 0.22
Nodes (7): fs, input, layerById, layers, outputIds, seen, structural

### Community 52 - "Page Artifact Concepts"
Cohesion: 0.46
Nodes (8): Annotation, Chat Evidence, Evaluation Harnesses, LegacyParsePage, ParseBlock, ParsePage, ParseResult, Rendering

### Community 53 - "Document Answer Policy"
Cohesion: 0.25
Nodes (8): Document-Only Answer Policy, Exact Excerpt Evidence, Injection Resistance, Question Classification, Chat Evaluation Cases, Document-Grounded Cases, Injection Attack Cases, Scope Rejection Cases

### Community 54 - "Graph Build Metadata"
Cohesion: 0.25
Nodes (7): ref_node_child_process, batches, { execFileSync }, fingerprintInput, fs, metadata, scan

### Community 55 - "Artifact Reference Validation"
Cohesion: 0.25
Nodes (4): model_validator, Reject detail inconsistent with the block role or table contents. Returns: This…, Enforce unique, in-range guide and one-to-one match references. Returns: This…, Check saved layout pages against parsed pages and diagnostics. Returns: This…

### Community 56 - "Graph Save Preparation"
Cohesion: 0.25
Nodes (7): { execFileSync }, fingerprintInput, fs, gitCommitHash, graph, scan, sourceFilePaths

### Community 57 - "Graph Tool Scratch Files"
Cohesion: 0.29
Nodes (4): ref_fs, fs, fs, fs

### Community 58 - "Graph Scan Assembly"
Cohesion: 0.29
Nodes (6): currentResult, excludedLanguageLabels, fs, imports, previous, scan

### Community 59 - "ONNX Error Boundary Tests"
Cohesion: 0.33
Nodes (3): invalid(), test_onnx_preprocessing_and_native_error_boundary(), fail()

### Community 60 - "Architecture Input Builder"
Cohesion: 0.33
Nodes (5): fileNodeIds, fileTypes, fs, graph, input

### Community 61 - "Architecture Image Checks"
Cohesion: 0.40
Nodes (5): Architecture Visual Check, Dark 1440x900, Dark 2048x1320, Light 1440x900, Light 2048x1320

### Community 62 - "Dataflow Image Checks"
Cohesion: 0.40
Nodes (5): Dark 1440x900, Dark 2048x1320, Dataflow Visual Check, Light 1440x900, Light 2048x1320

### Community 63 - "Lifecycle Image Checks"
Cohesion: 0.40
Nodes (5): Dark 1440x900, Dark 2048x1320, Lifecycle Visual Check, Light 1440x900, Light 2048x1320

### Community 64 - "Sequence Image Checks"
Cohesion: 0.40
Nodes (5): Dark 1440x900, Dark 2048x1320, Light 1440x900, Light 2048x1320, Sequence Visual Check

### Community 65 - "Workflow Image Checks"
Cohesion: 0.40
Nodes (5): Dark 1440x900, Dark 2048x1320, Light 1440x900, Light 2048x1320, Workflow Visual Check

### Community 66 - "Architecture Analyzer Tool"
Cohesion: 0.40
Nodes (3): ref_node_path, fs, path

### Community 67 - "Legacy Table Safeguards"
Cohesion: 0.40
Nodes (4): _bounded_blocks(), check_document_tables(), Reject a document whose rectangularized tables exceed the cell budget. Accept…, Upgrade saved legacy artifacts in memory, never live page responses.

### Community 69 - "Graph Tour Builder"
Cohesion: 0.40
Nodes (4): fs, graph, input, layers

### Community 70 - "Python Project Dependencies"
Cohesion: 0.50
Nodes (4): Development Requirements, pytest 9.1.1, Pyproject Dependency Source, Runtime Requirements

### Community 71 - "Sample Invoice Evidence"
Cohesion: 0.50
Nodes (4): Sample Invoice, Invoice Line Items, Invoice Metadata, Invoice Totals

### Community 72 - "Unexpected Graph Failures"
Cohesion: 0.50
Nodes (3): test_graph_unexpected_exception_does_not_leak_raw_text(), test_template_failure_retains_analysis_without_calling_sol(), fail()

### Community 74 - "OKF Project Knowledge"
Cohesion: 0.67
Nodes (3): Concepts, Open Knowledge Format v0.2, Project Knowledge

### Community 75 - "Evidence Approval Policy"
Cohesion: 0.67
Nodes (3): Candidate Evidence Approval, Independent Verification Policy, Uncertainty Rejection

### Community 77 - "Launcher Integration Tests"
Cohesion: 0.67
Nodes (3): skipif, parametrize, test_launcher_forwards_arguments_and_exit_status()

### Community 79 - "Graph Node Utilities"
Cohesion: 0.67
Nodes (3): addNode(), file(), symbol()

## Knowledge Gaps
- **173 isolated node(s):** `fs`, `fs`, `fs`, `previous`, `scan` (+168 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 499 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ParsePage` connect `Diagnostic Data Models` to `CLI HTML Dependencies`, `Layout Reconciliation Policy`, `Reconciliation Test Fixtures`, `Streamlit Clipboard Inspection`, `Document Evidence Chat`, `CLI Extraction Tests`, `Offline Layout Evaluation`, `Layout Guide Projection`, `Graph Execution Pipeline`, `Chat Evaluation Scripts`, `Evaluation Metrics Utilities`, `Document Export Pipeline`, `Evaluation Scripts Index`, `Prompt Context Construction`, `Layout Integration Tests`, `HTML Rendering Models`, `Structured Layout Tests`, `Evaluation Replay Artifacts`, `Diagnostic Integration Tests`, `Annotation Geometry Rendering`, `Fallback Integration Tests`, `Table Cell Validation`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Why does `ParseResult` connect `Annotation Geometry Rendering` to `Document Run Pipeline`, `PDF Image Dependencies`, `Layout Reconciliation Policy`, `Diagnostic Data Models`, `Reconciliation Test Fixtures`, `Streamlit Clipboard Inspection`, `Document Evidence Chat`, `LangGraph Chat Integration`, `Structured Parse Models`, `Layout Guide Projection`, `Graph Execution Pipeline`, `Chat Evaluation Scripts`, `Document Export Pipeline`, `Prompt Context Construction`, `Layout Integration Tests`, `HTML Rendering Models`, `Structured Layout Tests`, `Document Page Evidence`, `Diagnostic Integration Tests`, `Fallback Integration Tests`, `Table Cell Validation`, `Artifact Reference Validation`, `Legacy Table Safeguards`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `LayoutModelUnavailable` connect `Layout Failure Diagnostics` to `Evaluation Replay Artifacts`, `Streamlit Clipboard Inspection`, `LangGraph Chat Integration`, `Detector Runtime Recovery`, `Layout Runtime Configuration`, `Offline Layout Evaluation`, `Fallback Integration Tests`, `Layout Integration Tests`, `ONNX Layout Decoder`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `ParsePage` (e.g. with `compare()` and `main()`) actually correct?**
  _`ParsePage` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `ParseResult` (e.g. with `annotate_document()` and `document_pages()`) actually correct?**
  _`ParseResult` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `ParseBlock` (e.g. with `_cells()` and `_heading_level()`) actually correct?**
  _`ParseBlock` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `fs`, `fs`, `fs` to the rest of the system?**
  _173 weakly-connected nodes found - possible documentation gaps or missing edges._
