# Graph Report - GroundMark  (2026-09-23)

## Corpus Check
- Large corpus: 228 files · ~698,803 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 793 nodes · 1773 edges · 53 communities (43 shown, 10 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 123 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Layout and Export Core
- Diagnostics and Schemas
- Parse Result Models
- Evaluation Pipelines
- CLI Extraction Tests
- System Concepts
- Document Preprocessing
- Streamlit State Tests
- Document Chat Runtime
- Project Documentation
- Parsing Workflow Diagrams
- Architecture Components
- Runtime Prompt Loading
- LangGraph Pipeline
- Usage and Navigation
- Extraction Data Flow
- Parse Lifecycle Dark
- Parse Lifecycle Light
- Parse Lifecycle Large Dark
- Parse Lifecycle Large Light
- Execution Lifecycle
- Chat Sequence Dark
- Chat Sequence Light
- Chat Sequence Large
- Chat Evaluation Policy
- Parser Prompt Contracts
- Workflow State Dark
- Parse Chat Sequence
- Workflow State Light
- Architecture Visual Checks
- Dataflow Visual Checks
- Lifecycle Visual Checks
- Sequence Visual Checks
- Workflow Visual Checks
- Grounded Chat Documentation
- Development Operations
- Artifact Export Documentation
- UA Validation Scripts
- Dependency Metadata
- Invoice Test Fixture
- OpenWiki Automation
- OKF Project Knowledge
- Chat Verification Policy
- Parsing Architecture Wiki
- Layout Rendering Wiki
- Source Package Marker
- UI Package Marker
- Test Package Marker
- Changed File Inventory
- Filter Diagnostics Report
- Contribution Guide
- Model Contract
- GroundMark Package

## God Nodes (most connected - your core abstractions)
1. `ParsePage` - 64 edges
2. `ParseResult` - 60 edges
3. `ParseBlock` - 40 edges
4. `parse_to_markdown()` - 30 edges
5. `preprocess_pages()` - 27 edges
6. `parse_to_html()` - 26 edges
7. `ExtractionCallError` - 20 edges
8. `parse_document()` - 20 edges
9. `PageDiagnostic` - 18 edges
10. `BBox` - 18 edges

## Surprising Connections (you probably didn't know these)
- `Evidence Context` --semantically_similar_to--> `Chat Evidence`  [INFERRED] [semantically similar]
  docs/diagrams/groundmark-parse-chat-sequence.png → graphify-out/memory/query_20260923_085416_4fb1df1d_why_does_parsepage_act_as_the_primary_cross_cuttin.md
- `Layout Model` --semantically_similar_to--> `ParseResult`  [INFERRED] [semantically similar]
  docs/diagrams/groundmark-document-extraction-data-flow.png → openwiki/concepts/layout-and-rendering.md
- `ParsePage` --semantically_similar_to--> `ParsePage`  [INFERRED] [semantically similar]
  graphify-out/memory/query_20260923_085416_4fb1df1d_why_does_parsepage_act_as_the_primary_cross_cuttin.md → openwiki/concepts/layout-and-rendering.md
- `GroundMark Core Architecture` --conceptually_related_to--> `GroundMark Quickstart`  [INFERRED]
  docs/diagrams/groundmark.png → openwiki/quickstart.md
- `compare()` --uses--> `ParsePage`  [INFERRED]
  scripts/evaluate_layout.py → src/layout.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **GroundMark Documentation Contract** — readme_groundmark, docs_architecture_groundmark_architecture, docs_compliance_data_and_output_boundaries, docs_model_model_contract, docs_prompts_prompt_contract, docs_runbook_runbook [EXTRACTED 1.00]
- **GroundMark Recorded Evaluations** — docs_content_filter_diagnostics_content_filter_diagnostics, docs_layout_evaluation_layout_comparison, docs_prompt_evaluation_prompt_evaluation, docs_sol_resolution_evaluation_sol_resolution_comparison [EXTRACTED 1.00]
- **GroundMark Visual Architecture Family** — docs_diagrams_groundmark_architecture_visual_check_1440x900_dark_groundmark_architecture, docs_diagrams_groundmark_architecture_visual_check_1440x900_light_groundmark_architecture, docs_diagrams_groundmark_architecture_visual_check_2048x1320_dark_groundmark_architecture, docs_diagrams_groundmark_architecture_visual_check_2048x1320_light_groundmark_architecture, docs_diagrams_groundmark_dataflow_visual_check_1440x900_dark_document_extraction_data_flow, docs_diagrams_groundmark_dataflow_visual_check_1440x900_light_document_extraction_data_flow, docs_diagrams_groundmark_dataflow_visual_check_2048x1320_dark_document_extraction_data_flow, docs_diagrams_groundmark_dataflow_visual_check_2048x1320_light_document_extraction_data_flow, docs_diagrams_groundmark_document_execution_lifecycle_document_execution_lifecycle [INFERRED 0.85]
- **Document Execution Lifecycle** — docs_diagrams_groundmark_lifecycle_submitted, docs_diagrams_groundmark_lifecycle_preprocess, docs_diagrams_groundmark_lifecycle_visual_parse, docs_diagrams_groundmark_lifecycle_validating, docs_diagrams_groundmark_lifecycle_exported [EXTRACTED 1.00]
- **Document Execution Lifecycle** — docs_diagrams_groundmark_lifecycle_visual_check_1440x900_dark_submitted, docs_diagrams_groundmark_lifecycle_visual_check_1440x900_dark_preprocess, docs_diagrams_groundmark_lifecycle_visual_check_1440x900_dark_visual_parse, docs_diagrams_groundmark_lifecycle_visual_check_1440x900_dark_validating, docs_diagrams_groundmark_lifecycle_visual_check_1440x900_dark_exported [EXTRACTED 1.00]
- **Document Execution Lifecycle** — docs_diagrams_groundmark_lifecycle_visual_check_1440x900_light_submitted, docs_diagrams_groundmark_lifecycle_visual_check_1440x900_light_preprocess, docs_diagrams_groundmark_lifecycle_visual_check_1440x900_light_visual_parse, docs_diagrams_groundmark_lifecycle_visual_check_1440x900_light_validating, docs_diagrams_groundmark_lifecycle_visual_check_1440x900_light_exported [EXTRACTED 1.00]
- **Document Execution Lifecycle** — docs_diagrams_groundmark_lifecycle_visual_check_2048x1320_dark_submitted, docs_diagrams_groundmark_lifecycle_visual_check_2048x1320_dark_preprocess, docs_diagrams_groundmark_lifecycle_visual_check_2048x1320_dark_visual_parse, docs_diagrams_groundmark_lifecycle_visual_check_2048x1320_dark_validating, docs_diagrams_groundmark_lifecycle_visual_check_2048x1320_dark_exported [EXTRACTED 1.00]
- **Document Execution Lifecycle** — docs_diagrams_groundmark_lifecycle_visual_check_2048x1320_light_submitted, docs_diagrams_groundmark_lifecycle_visual_check_2048x1320_light_preprocess, docs_diagrams_groundmark_lifecycle_visual_check_2048x1320_light_visual_parse, docs_diagrams_groundmark_lifecycle_visual_check_2048x1320_light_validating, docs_diagrams_groundmark_lifecycle_visual_check_2048x1320_light_exported [EXTRACTED 1.00]
- **Parse and Grounded Chat** — docs_diagrams_groundmark_sequence_graph, docs_diagrams_groundmark_sequence_gpt_6_sol, docs_diagrams_groundmark_sequence_chat_engine, docs_diagrams_groundmark_sequence_gpt_6_luna [EXTRACTED 1.00]
- **Parse and Grounded Chat** — docs_diagrams_groundmark_parse_chat_sequence_graph, docs_diagrams_groundmark_parse_chat_sequence_gpt_6_sol, docs_diagrams_groundmark_parse_chat_sequence_chat_engine, docs_diagrams_groundmark_parse_chat_sequence_gpt_6_luna [EXTRACTED 1.00]
- **Parse and Grounded Chat** — docs_diagrams_groundmark_sequence_visual_check_1440x900_dark_graph, docs_diagrams_groundmark_sequence_visual_check_1440x900_dark_gpt_6_sol, docs_diagrams_groundmark_sequence_visual_check_1440x900_dark_chat_engine, docs_diagrams_groundmark_sequence_visual_check_1440x900_dark_gpt_6_luna [EXTRACTED 1.00]
- **Parse and Grounded Chat** — docs_diagrams_groundmark_sequence_visual_check_1440x900_light_graph, docs_diagrams_groundmark_sequence_visual_check_1440x900_light_gpt_6_sol, docs_diagrams_groundmark_sequence_visual_check_1440x900_light_chat_engine, docs_diagrams_groundmark_sequence_visual_check_1440x900_light_gpt_6_luna [EXTRACTED 1.00]
- **Document Extraction Data Flow** — docs_diagrams_groundmark_dataflow_document_input, docs_diagrams_groundmark_dataflow_rasterizer, docs_diagrams_groundmark_dataflow_gpt_6_sol, docs_diagrams_groundmark_dataflow_layout_model, docs_diagrams_groundmark_dataflow_text_formats [EXTRACTED 1.00]
- **Document Extraction Data Flow** — docs_diagrams_groundmark_document_extraction_data_flow_document_input, docs_diagrams_groundmark_document_extraction_data_flow_rasterizer, docs_diagrams_groundmark_document_extraction_data_flow_gpt_6_sol, docs_diagrams_groundmark_document_extraction_data_flow_layout_model, docs_diagrams_groundmark_document_extraction_data_flow_text_formats [EXTRACTED 1.00]
- **Document Parsing Workflow** — docs_diagrams_groundmark_workflow_submit, docs_diagrams_groundmark_workflow_preprocess, docs_diagrams_groundmark_workflow_sol_parse, docs_diagrams_groundmark_workflow_export, docs_diagrams_groundmark_workflow_present [EXTRACTED 1.00]
- **Document Parsing Workflow** — docs_diagrams_groundmark_document_parsing_workflow_submit, docs_diagrams_groundmark_document_parsing_workflow_preprocess, docs_diagrams_groundmark_document_parsing_workflow_sol_parse, docs_diagrams_groundmark_document_parsing_workflow_export, docs_diagrams_groundmark_document_parsing_workflow_present [EXTRACTED 1.00]
- **GroundMark Architecture** — docs_diagrams_groundmark_architecture_streamlit_ui, docs_diagrams_groundmark_architecture_pipeline_graph, docs_diagrams_groundmark_architecture_parser_engine, docs_diagrams_groundmark_architecture_artifact_renderer, docs_diagrams_groundmark_architecture_chat_engine [EXTRACTED 1.00]
- **ParsePage Cross Cutting Bridge** — graphify_out_memory_query_20260923_085416_4fb1df1d_why_does_parsepage_act_as_the_primary_cross_cuttin_parsepage, graphify_out_memory_query_20260923_085416_4fb1df1d_why_does_parsepage_act_as_the_primary_cross_cuttin_parseblock, graphify_out_memory_query_20260923_085416_4fb1df1d_why_does_parsepage_act_as_the_primary_cross_cuttin_rendering, graphify_out_memory_query_20260923_085416_4fb1df1d_why_does_parsepage_act_as_the_primary_cross_cuttin_chat_evidence, graphify_out_memory_query_20260923_085416_4fb1df1d_why_does_parsepage_act_as_the_primary_cross_cuttin_evaluation_harnesses [EXTRACTED 1.00]
- **Parsing Pipeline** — openwiki_architecture_parsing_pipeline_preprocessing, openwiki_architecture_parsing_pipeline_sequential_model_calls, openwiki_architecture_parsing_pipeline_page_diagnostics, openwiki_architecture_parsing_pipeline_partial_extraction [EXTRACTED 1.00]
- **Layout Model and Rendering** — openwiki_concepts_layout_and_rendering_parseresult, openwiki_concepts_layout_and_rendering_parsepage, openwiki_concepts_layout_and_rendering_parseblock, openwiki_concepts_layout_and_rendering_structural_invariants, openwiki_concepts_layout_and_rendering_rendering_immutability [EXTRACTED 1.00]
- **GroundMark Document Chat Verification** — openwiki_features_document_chat_grounded_document_chat, prompts_runtime_chat_answer_document_only_answer_policy, prompts_runtime_chat_verify_independent_verification_policy, tests_fixtures_chat_evaluation_chat_evaluation_cases [EXTRACTED 1.00]
- **GroundMark Layout Extraction Contract** — prompts_runtime_parse_page_structured_structured_page_transcription, prompts_runtime_parse_page_page_transcription, docs_diagrams_groundmark_core_pipeline [INFERRED 0.85]
- **GroundMark Export Lifecycle** — openwiki_workflows_artifacts_and_exports_artifacts_export_lifecycle, openwiki_quickstart_terminal_extraction_mode, docs_diagrams_groundmark_artifact_outputs [INFERRED 0.85]

## Communities (53 total, 10 thin omitted)

### Community 0 - "Layout and Export Core"
Cohesion: 0.06
Nodes (89): base64, cache_data, Figures, html, io, math, _bbox_is_valid(), Draws every parsed block's bbox onto a rasterized copy of each page and saves… (+81 more)

### Community 1 - "Diagnostics and Schemas"
Cohesion: 0.05
Nodes (84): ChatOpenAI, dataclasses, HumanMessage, langchain_core_messages, langchain_openai, openai, os, pydantic (+76 more)

### Community 2 - "Parse Result Models"
Cohesion: 0.06
Nodes (56): field_validator, model_validator, main(), Bounded live evaluation using synthetic document data and Markdown cases., annotate_document(), Path, Draw every block's bbox onto a rasterized copy of each page and save a multi-…, _extract() (+48 more)

### Community 3 - "Evaluation Pipelines"
Cohesion: 0.05
Nodes (55): collections, concurrent_futures, Counter, hashlib, html_parser, HTMLParser, scripts, compare() (+47 more)

### Community 4 - "CLI Extraction Tests"
Cohesion: 0.06
Nodes (36): argparse, contextlib, datetime, dotenv, importlib_metadata, json, pathlib, pytest (+28 more)

### Community 5 - "System Concepts"
Cohesion: 0.07
Nodes (44): Annotator, Document Input, gpt-6-sol, Layout JSON, Layout Model, Rasterizer, SHA Hasher, Text Formats (+36 more)

### Community 6 - "Document Preprocessing"
Cohesion: 0.10
Nodes (35): pil, _cap_long_edge(), count_pages(), preprocess(), preprocess_pages(), PreprocessError, Exception, Image (+27 more)

### Community 7 - "Streamlit State Tests"
Cohesion: 0.09
Nodes (16): Clipboard controls for Markdown and JSON artifacts. Must not: assign…, streamlit, streamlit_testing_v1, Minimal stand-in for a ChatOpenAI client, used by tests that exercise src.llm's…, fixture, parametrize, AppTest regressions: Sol only, upload identity, and rerun-safe previews., test_chat_submission_reruns_and_reset() (+8 more)

### Community 8 - "Document Chat Runtime"
Cohesion: 0.19
Nodes (21): httpx, answer_document_question(), ChatResult, document_pages(), client_for(), document(), draft(), parametrize (+13 more)

### Community 9 - "Project Documentation"
Cohesion: 0.11
Nodes (18): GroundMark Architecture, Data and Output Boundaries, GroundMark Architecture Dark 1440x900, GroundMark Architecture Light 1440x900, GroundMark Architecture Dark 2048x1320, GroundMark Architecture Light 2048x1320, Document Extraction Data Flow Dark 1440x900, Document Extraction Data Flow Light 1440x900 (+10 more)

### Community 10 - "Parsing Workflow Diagrams"
Cohesion: 0.12
Nodes (16): Deterministic Parsing Pipeline, Failure Isolation, Multi-Format Export, GroundMark Parsing Workflow 1440 Dark, Deterministic Parsing Pipeline, Failure Isolation, Multi-Format Export, GroundMark Parsing Workflow 1440 Light (+8 more)

### Community 11 - "Architecture Components"
Cohesion: 0.21
Nodes (12): Annotator, Artifact Renderer, Chat Engine, Document Input, gpt-6-luna, gpt-6-sol, Grounding Model, Local Files (+4 more)

### Community 12 - "Runtime Prompt Loading"
Cohesion: 0.29
Nodes (10): Loads a prompt template from prompts/runtime/<name>.md and fills in its…, render_prompt(), parametrize, Tests for src.prompts.render_prompt -- template resolution relative to the…, test_all_runtime_templates_render_without_reformatting_data(), test_chat_policies_load_outside_project(), test_detailed_prompt_stays_in_markdown_and_preserves_contract(), test_prompt_missing_placeholder_fails() (+2 more)

### Community 13 - "LangGraph Pipeline"
Cohesion: 0.25
Nodes (10): collections_abc, langgraph_config, langgraph_graph, build_graph(), GraphState, node_parse(), node_preprocess(), Defines and runs the pipeline: `preprocess -> parse -> END`.… (+2 more)

### Community 14 - "Usage and Navigation"
Cohesion: 0.22
Nodes (9): GroundMark Core Architecture, Artifact Outputs, GroundMark Core Pipeline, Evidence Verification Boundary, OpenWiki Index, GroundMark Quickstart, Partial Page Results, Streamlit UI Mode (+1 more)

### Community 15 - "Extraction Data Flow"
Cohesion: 0.33
Nodes (9): Annotator, Document Input, gpt-6-sol, Layout JSON, Layout Model, Rasterizer, SHA Hasher, Text Formats (+1 more)

### Community 16 - "Parse Lifecycle Dark"
Cohesion: 0.33
Nodes (9): Exported, Page Failed, Page Filtered, Parse Failed, Partial Output, Preprocess, Submitted, Validating (+1 more)

### Community 17 - "Parse Lifecycle Light"
Cohesion: 0.33
Nodes (9): Exported, Page Failed, Page Filtered, Parse Failed, Partial Output, Preprocess, Submitted, Validating (+1 more)

### Community 18 - "Parse Lifecycle Large Dark"
Cohesion: 0.33
Nodes (9): Exported, Page Failed, Page Filtered, Parse Failed, Partial Output, Preprocess, Submitted, Validating (+1 more)

### Community 19 - "Parse Lifecycle Large Light"
Cohesion: 0.33
Nodes (9): Exported, Page Failed, Page Filtered, Parse Failed, Partial Output, Preprocess, Submitted, Validating (+1 more)

### Community 20 - "Execution Lifecycle"
Cohesion: 0.33
Nodes (9): Exported, Page Failed, Page Filtered, Parse Failed, Partial Output, Preprocess, Submitted, Validating (+1 more)

### Community 21 - "Chat Sequence Dark"
Cohesion: 0.31
Nodes (9): Chat Engine, Evidence Context, gpt-6-luna, gpt-6-sol, Graph, Parsed Artifacts, Streamlit UI, User (+1 more)

### Community 22 - "Chat Sequence Light"
Cohesion: 0.31
Nodes (9): Chat Engine, Evidence Context, gpt-6-luna, gpt-6-sol, Graph, Parsed Artifacts, Streamlit UI, User (+1 more)

### Community 23 - "Chat Sequence Large"
Cohesion: 0.31
Nodes (9): Chat Engine, Evidence Context, gpt-6-luna, gpt-6-sol, Graph, Parsed Artifacts, Streamlit UI, User (+1 more)

### Community 24 - "Chat Evaluation Policy"
Cohesion: 0.25
Nodes (8): Document-Only Answer Policy, Exact Excerpt Evidence, Injection Resistance, Question Classification, Chat Evaluation Cases, Document-Grounded Cases, Injection Attack Cases, Scope Rejection Cases

### Community 25 - "Parser Prompt Contracts"
Cohesion: 0.29
Nodes (7): Basic Block Contract, Page Transcription, Source Image Priority, Layout Block Contract, Reading Order Fidelity, Structure Metadata, Structured Page Transcription

### Community 26 - "Workflow State Dark"
Cohesion: 0.40
Nodes (6): Export, Filtered, Preprocess, Present, Sol Parse, Submit

### Community 27 - "Parse Chat Sequence"
Cohesion: 0.47
Nodes (6): Sequential Parse Flow, GroundMark Parse and Chat Sequence Dark, Verified Chat Flow, Sequential Parse Flow, GroundMark Parse and Chat Sequence Light, Verified Chat Flow

### Community 28 - "Workflow State Light"
Cohesion: 0.47
Nodes (6): Export, Filtered, Preprocess, Present, Sol Parse, Submit

### Community 29 - "Architecture Visual Checks"
Cohesion: 0.40
Nodes (5): Architecture Visual Check, Dark 1440x900, Dark 2048x1320, Light 1440x900, Light 2048x1320

### Community 30 - "Dataflow Visual Checks"
Cohesion: 0.40
Nodes (5): Dark 1440x900, Dark 2048x1320, Dataflow Visual Check, Light 1440x900, Light 2048x1320

### Community 31 - "Lifecycle Visual Checks"
Cohesion: 0.40
Nodes (5): Dark 1440x900, Dark 2048x1320, Lifecycle Visual Check, Light 1440x900, Light 2048x1320

### Community 32 - "Sequence Visual Checks"
Cohesion: 0.40
Nodes (5): Dark 1440x900, Dark 2048x1320, Light 1440x900, Light 2048x1320, Sequence Visual Check

### Community 33 - "Workflow Visual Checks"
Cohesion: 0.40
Nodes (5): Dark 1440x900, Dark 2048x1320, Light 1440x900, Light 2048x1320, Workflow Visual Check

### Community 34 - "Grounded Chat Documentation"
Cohesion: 0.40
Nodes (5): Fail-Closed Chat Boundary, Grounded Document Chat, Parsed Page Evidence, Two-Call Verification, Features Index

### Community 35 - "Development Operations"
Cohesion: 0.40
Nodes (5): Deterministic Test Suite, Development, Testing, and Evaluation, Live Evaluation Bounds, UV Packaging Workflow, Operations Index

### Community 36 - "Artifact Export Documentation"
Cohesion: 0.40
Nodes (5): Artifacts and Export Lifecycle, Collision-Safe Basename, Independent Export Boundaries, Partial Export Completion, Workflows Index

### Community 37 - "UA Validation Scripts"
Cohesion: 0.40
Nodes (3): ref_fs, fs, fs

### Community 38 - "Dependency Metadata"
Cohesion: 0.50
Nodes (4): Development Requirements, pytest 9.1.1, Pyproject Dependency Source, Runtime Requirements

### Community 39 - "Invoice Test Fixture"
Cohesion: 0.50
Nodes (4): Sample Invoice, Invoice Line Items, Invoice Metadata, Invoice Totals

### Community 40 - "OpenWiki Automation"
Cohesion: 0.67
Nodes (3): OpenWiki Update Workflow, OpenWiki Agent Guidance, OpenWiki Guidance Reference

### Community 41 - "OKF Project Knowledge"
Cohesion: 0.67
Nodes (3): Concepts, Open Knowledge Format v0.2, Project Knowledge

### Community 42 - "Chat Verification Policy"
Cohesion: 0.67
Nodes (3): Candidate Evidence Approval, Independent Verification Policy, Uncertainty Rejection

## Knowledge Gaps
- **75 isolated node(s):** `fs`, `fs`, `groundmark`, `OpenWiki Update Workflow`, `Changed File Inventory` (+70 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 226 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ParsePage` connect `Parse Result Models` to `Layout and Export Core`, `Diagnostics and Schemas`, `Evaluation Pipelines`, `CLI Extraction Tests`, `Streamlit State Tests`, `Document Chat Runtime`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Why does `ParseResult` connect `Parse Result Models` to `Layout and Export Core`, `Diagnostics and Schemas`, `Streamlit State Tests`, `Document Chat Runtime`, `LangGraph Pipeline`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Why does `preprocess_pages()` connect `Document Preprocessing` to `Layout and Export Core`, `Diagnostics and Schemas`, `Parse Result Models`, `Evaluation Pipelines`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `ParsePage` (e.g. with `compare()` and `main()`) actually correct?**
  _`ParsePage` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `ParseResult` (e.g. with `annotate_document()` and `document_pages()`) actually correct?**
  _`ParseResult` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `ParseBlock` (e.g. with `_cells()` and `_heading_level()`) actually correct?**
  _`ParseBlock` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `parse_to_markdown()` (e.g. with `export_result()` and `ParseResult`) actually correct?**
  _`parse_to_markdown()` has 3 INFERRED edges - model-reasoned connections that need verification._