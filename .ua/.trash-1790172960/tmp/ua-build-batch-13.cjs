const fs = require('node:fs');

const nodes = [];
const edges = [];
const nodeIds = new Set();
function addNode(node) {
  if (nodeIds.has(node.id)) throw new Error(`duplicate node ${node.id}`);
  nodeIds.add(node.id);
  nodes.push(node);
}
function edge(source, target, type, weight) {
  edges.push({ source, target, type, direction: 'forward', weight });
}
function file(type, path, summary, tags, complexity) {
  const name = path.split('/').at(-1);
  addNode({ id: `${type}:${path}`, type, name, filePath: path, summary, tags, complexity });
  return `${type}:${path}`;
}
function symbol(type, path, name, lineRange, summary, tags, complexity) {
  const id = `${type}:${path}:${name}`;
  addNode({ id, type, name, filePath: path, lineRange, summary, tags, complexity });
  return id;
}
function contains(fileId, symbolId, exported = false) {
  edge(fileId, symbolId, 'contains', 1.0);
  if (exported) edge(fileId, symbolId, 'exports', 0.8);
}

const claim = file('config', 'openwiki/.claims/workflows/artifacts-and-exports.json',
  'Machine-readable, source-linked claims for the artifact and export workflow, including run isolation, collision-safe names, partial output, figure crops, annotations, and CLI outcomes.',
  ['configuration', 'claims', 'evidence', 'exports'], 'moderate');
const archIndex = file('document', 'openwiki/architecture/index.md',
  'Navigation index linking to the repository’s parsing-pipeline architecture page.',
  ['documentation', 'architecture', 'index'], 'simple');
const archDoc = file('document', 'openwiki/architecture/parsing-pipeline.md',
  'Describes the fixed preprocess-to-parse graph, run-local state, sequential page requests, diagnostic outcomes, and preservation of partial extraction results.',
  ['documentation', 'architecture', 'parsing', 'diagnostics'], 'moderate');
const conceptIndex = file('document', 'openwiki/concepts/index.md',
  'Navigation index linking to the layout and rendering concept page.',
  ['documentation', 'concepts', 'index'], 'simple');
const layoutDoc = file('document', 'openwiki/concepts/layout-and-rendering.md',
  'Documents the stable ParseResult layout contract, structural validation, ordering and escaping rules, table/list fallbacks, and safe figure rendering.',
  ['documentation', 'layout', 'rendering', 'markdown'], 'moderate');
const chatDoc = file('document', 'openwiki/features/document-chat.md',
  'Explains document-only chat over successful parsed pages, exact-quote evidence checks, independent answer verification, and fail-closed UI behavior.',
  ['documentation', 'chat', 'grounding', 'verification'], 'simple');
const featureIndex = file('document', 'openwiki/features/index.md',
  'Navigation index linking to the grounded document chat feature page.',
  ['documentation', 'features', 'index'], 'simple');
const operationsDoc = file('document', 'openwiki/operations/development-and-testing.md',
  'Summarizes uv-based setup, deterministic tests and packaging, plus separately authorized live evaluation harnesses and their bounds.',
  ['documentation', 'development', 'testing', 'evaluation'], 'simple');
const operationsIndex = file('document', 'openwiki/operations/index.md',
  'Navigation index linking to the development, testing, and evaluation guidance.',
  ['documentation', 'operations', 'index'], 'simple');
const exportsDoc = file('document', 'openwiki/workflows/artifacts-and-exports.md',
  'Describes one-parse selective exports, run and destination ownership, collision-safe artifact naming, figure and annotation handling, and partial-result status.',
  ['documentation', 'exports', 'artifacts', 'workflow'], 'moderate');
const workflowIndex = file('document', 'openwiki/workflows/index.md',
  'Navigation index linking to the artifacts and exports workflow page.',
  ['documentation', 'workflows', 'index'], 'simple');

const annotateFile = file('file', 'src/annotate.py',
  'Rerasterizes the parsed page interval and overlays labels for valid normalized block boxes, optionally saving a multi-page PDF, per-page PNGs, and count metadata.',
  ['annotation', 'pdf', 'image-processing', 'validation'], 'moderate');
const bboxFn = symbol('function', 'src/annotate.py', '_bbox_is_valid', [30, 37],
  'Accepts only normalized boxes with coordinates inside 0–1 and positive width and height.',
  ['validation', 'bounding-box', 'utility'], 'simple');
const annotateFn = symbol('function', 'src/annotate.py', 'annotate_document', [40, 129],
  'Rasterizes the covered pages, draws labels for valid block boxes, and optionally writes annotated PDF, page images, and a metadata sidecar.',
  ['annotation', 'pdf', 'image-processing', 'artifacts'], 'moderate');
contains(annotateFile, bboxFn, true);
contains(annotateFile, annotateFn, true);

const exportFile = file('file', 'src/export.py',
  'Writes independently selected JSON, Markdown, HTML, ZIP, figure, and annotation outputs from one ParseResult while retaining successful artifacts when another export fails.',
  ['exports', 'artifacts', 'serialization', 'partial-results'], 'moderate');
const exportFn = symbol('function', 'src/export.py', 'export_result', [15, 88],
  'Creates the output directory, attempts selected renderers and annotations independently, and returns paths, warnings, and export errors.',
  ['exports', 'artifacts', 'serialization', 'error-handling'], 'moderate');
contains(exportFile, exportFn, true);

const figuresFile = file('file', 'src/figures.py',
  'Extracts source-matched figure crops using page-position names and reloads only verified PNG crops; unavailable crops become warnings rather than extraction failures.',
  ['figures', 'image-processing', 'validation', 'artifacts'], 'moderate');
const extractFiguresFn = symbol('function', 'src/figures.py', 'extract_figures', [17, 49],
  'Checks source identity and bounding boxes before cropping figures, optionally persists PNGs, and reports crop failures as warnings.',
  ['figures', 'image-processing', 'validation', 'artifacts'], 'simple');
const loadFiguresFn = symbol('function', 'src/figures.py', 'load_figures', [52, 70],
  'Loads expected figure assets and accepts only files that Pillow verifies as PNG images.',
  ['figures', 'image-processing', 'validation'], 'simple');
contains(figuresFile, extractFiguresFn, true);
contains(figuresFile, loadFiguresFn, true);

const graphFile = file('file', 'src/graph.py',
  'Defines the two-node preprocess-to-parse LangGraph and its run entry point, which initializes isolated state, validates options, streams progress, and returns extraction status and artifacts.',
  ['entry-point', 'langgraph', 'pipeline', 'run-isolation'], 'moderate');
const stateClass = symbol('class', 'src/graph.py', 'GraphState', [32, 60],
  'Typed state contract for document identity, parse results, output settings, diagnostics, usage, and generated artifact paths.',
  ['state', 'type-definition', 'pipeline'], 'simple');
const preprocessFn = symbol('function', 'src/graph.py', 'node_preprocess', [63, 77],
  'Preprocesses the source and fills document hash, run identity, output destination, model, filename, and start-time defaults.',
  ['pipeline', 'preprocessing', 'run-isolation'], 'simple');
const parseFn = symbol('function', 'src/graph.py', 'node_parse', [80, 130],
  'Runs page parsing and export orchestration, records filtered and failed pages, and converts exceptions or partial results into explicit run status.',
  ['pipeline', 'parsing', 'diagnostics', 'exports'], 'moderate');
const buildFn = symbol('function', 'src/graph.py', 'build_graph', [133, 142],
  'Connects preprocess and parse nodes between LangGraph START and END and compiles the graph.',
  ['langgraph', 'pipeline', 'factory'], 'simple');
const runFn = symbol('function', 'src/graph.py', 'run_graph', [145, 183],
  'Validates model and rendering options, creates isolated run state, streams graph execution, and returns final state with run-local usage.',
  ['entry-point', 'pipeline', 'run-isolation', 'validation'], 'simple');
const mainFn = symbol('function', 'src/graph.py', '_main', [186, 204],
  'Implements the module CLI for parsing a document path and printing status, errors, and token totals.',
  ['cli', 'entry-point', 'pipeline'], 'simple');
contains(graphFile, stateClass, true);
contains(graphFile, preprocessFn, true);
contains(graphFile, parseFn, true);
contains(graphFile, buildFn, true);
contains(graphFile, runFn, true);
contains(graphFile, mainFn, true);

// OpenWiki navigation and source relationships are emitted only for concrete referenced files.
edge(archIndex, archDoc, 'documents', 0.5);
edge(archDoc, graphFile, 'documents', 0.5);
edge(archDoc, 'file:src/preprocess.py', 'documents', 0.5);
edge(archDoc, 'file:src/parse.py', 'documents', 0.5);
edge(archDoc, 'file:src/diagnostics.py', 'documents', 0.5);
edge(conceptIndex, layoutDoc, 'documents', 0.5);
edge(layoutDoc, figuresFile, 'documents', 0.5);
edge(layoutDoc, 'file:src/layout.py', 'documents', 0.5);
edge(layoutDoc, 'file:src/markdown.py', 'documents', 0.5);
edge(featureIndex, chatDoc, 'documents', 0.5);
edge(chatDoc, 'file:src/chat.py', 'documents', 0.5);
edge(chatDoc, 'file:src/ui/app.py', 'documents', 0.5);
edge(chatDoc, 'document:prompts/runtime/chat-answer.md', 'documents', 0.5);
edge(chatDoc, 'document:prompts/runtime/chat-verify.md', 'documents', 0.5);
edge(operationsIndex, operationsDoc, 'documents', 0.5);
edge(operationsDoc, 'document:docs/CONTRIBUTING.md', 'documents', 0.5);
edge(operationsDoc, 'document:docs/RUNBOOK.md', 'documents', 0.5);
edge(operationsDoc, 'config:pyproject.toml', 'documents', 0.5);
edge(exportsDoc, annotateFile, 'documents', 0.5);
edge(exportsDoc, exportFile, 'documents', 0.5);
edge(exportsDoc, figuresFile, 'documents', 0.5);
edge(exportsDoc, graphFile, 'documents', 0.5);
edge(exportsDoc, 'file:src/cli.py', 'documents', 0.5);
edge(exportsDoc, 'file:src/output_names.py', 'documents', 0.5);
edge(workflowIndex, exportsDoc, 'documents', 0.5);
for (const target of [annotateFile, exportFile, figuresFile, graphFile, 'file:src/cli.py', 'file:src/output_names.py']) {
  edge(claim, target, 'documents', 0.5);
}

// Calls are grounded in the deterministic call graph, with only project symbols represented as nodes.
edge(annotateFn, bboxFn, 'calls', 0.8);
edge(annotateFn, 'function:src/preprocess.py:preprocess_pages', 'calls', 0.8);
edge(annotateFn, 'function:src/output_names.py:artifact_name', 'calls', 0.8);
edge(exportFn, 'function:src/output_names.py:artifact_name', 'calls', 0.8);
edge(exportFn, extractFiguresFn, 'calls', 0.8);
edge(exportFn, annotateFn, 'calls', 0.8);
edge(exportFn, 'function:src/markdown.py:parse_to_markdown', 'calls', 0.8);
edge(exportFn, 'function:src/markdown.py:parse_to_html', 'calls', 0.8);
edge(exportFn, 'function:src/markdown.py:markdown_bundle', 'calls', 0.8);
edge(extractFiguresFn, 'function:src/preprocess.py:preprocess_pages', 'calls', 0.8);
edge(extractFiguresFn, bboxFn, 'calls', 0.8);
edge(extractFiguresFn, 'function:src/output_names.py:figure_name', 'calls', 0.8);
edge(loadFiguresFn, 'function:src/output_names.py:figure_name', 'calls', 0.8);
edge(preprocessFn, 'function:src/preprocess.py:preprocess', 'calls', 0.8);
edge(parseFn, 'function:src/parse.py:parse_document', 'calls', 0.8);
edge(parseFn, 'function:src/output_names.py:reserve_basename', 'calls', 0.8);
edge(parseFn, exportFn, 'calls', 0.8);
edge(buildFn, preprocessFn, 'calls', 0.8);
edge(buildFn, parseFn, 'calls', 0.8);
edge(runFn, buildFn, 'calls', 0.8);
edge(mainFn, runFn, 'calls', 0.8);
edge(mainFn, 'function:src/usage.py:totals', 'calls', 0.8);

const result = { nodes, edges };
const missingLocal = edges.filter(e => !nodeIds.has(e.source) && !e.source.startsWith('file:') && !e.source.startsWith('config:') && !e.source.startsWith('document:'));
if (missingLocal.length) throw new Error(`invalid local edge sources: ${JSON.stringify(missingLocal)}`);
const outputPath = '.ua/intermediate/batch-13.json';
fs.writeFileSync(outputPath, JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify({ outputPath, nodes: nodes.length, edges: edges.length, nodeTypes: nodes.reduce((a, n) => (a[n.type] = (a[n.type] || 0) + 1, a), {}), edgeTypes: edges.reduce((a, e) => (a[e.type] = (a[e.type] || 0) + 1, a), {}) }, null, 2));
