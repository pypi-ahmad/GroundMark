import fs from 'node:fs';

const root = process.cwd();
const extracted = JSON.parse(fs.readFileSync(`${root}/.ua/tmp/ua-file-extract-results-14.json`, 'utf8'));
const batches = JSON.parse(fs.readFileSync(`${root}/.ua/intermediate/batches.json`, 'utf8'));
const batch = batches.batches.find((item) => item.batchIndex === 14);
if (!extracted.scriptCompleted || extracted.results.length !== batch.files.length) {
  throw new Error('Structural extraction did not return all six assigned files.');
}

const fileInfo = {
  'src/markdown.py': {
    summary: 'Converts structured parse results into escaped Markdown and HTML, including tables, lists, headings, and figure links. It also writes standalone exports and bundles Markdown with its figures.',
    tags: ['document-rendering', 'markdown', 'html-export', 'figures'],
    area: 'rendering',
  },
  'src/output_names.py': {
    summary: 'Builds safe, source-derived output basenames and deterministic figure names. It reserves timestamped artifact families while avoiding collisions across output folders and concurrent runs.',
    tags: ['artifact-naming', 'filenames', 'collision-handling', 'utc-timestamps'],
    area: 'artifact-naming',
  },
  'src/ui/app.py': {
    summary: 'Defines the Streamlit document-parsing interface, grounded chat state, upload preview, token-usage display, and figure-asset helpers. The UI delegates parsing and rendering to the application modules.',
    tags: ['streamlit-ui', 'document-parsing', 'grounded-chat', 'usage-metrics'],
    area: 'user-interface',
  },
  'tests/test_cli_extraction.py': {
    summary: 'Exercises CLI extraction and export behavior with local fixtures and model calls stubbed out. Coverage includes format selection, validation failures, partial parsing, diagnostics, and output naming.',
    tags: ['test', 'cli-extraction', 'exports', 'regression'],
    area: 'cli-extraction',
  },
  'tests/test_graph.py': {
    summary: 'Checks the parse graph lifecycle using a fake document parser, including status and error reporting, artifact persistence, concurrent-run isolation, usage accounting, and filtered pages.',
    tags: ['test', 'graph-lifecycle', 'artifacts', 'regression'],
    area: 'graph-lifecycle',
  },
  'tests/test_output_names.py': {
    summary: 'Verifies safe source stems, UTC timestamp reservations, collision detection, lock cleanup, and figure-link resolution when rendering legacy and current parse artifacts.',
    tags: ['test', 'artifact-naming', 'collision-handling', 'rendering'],
    area: 'artifact-naming',
  },
};

const functionSummaries = {
  _blocks: 'Iterates pages and blocks in page order, optionally filtering headers and footers, and assigns figure names.',
  _cell_html: 'Escapes table-cell text for HTML and converts line breaks to explicit HTML breaks.',
  _md_text: 'Escapes source text so its Markdown-like syntax is rendered as literal content.',
  _table_rows: 'Pads uneven table rows to a shared column count.',
  _cells: 'Uses recorded cell metadata when available and supplies a regular grid for legacy table artifacts.',
  _render_table_html: 'Renders table rows as escaped HTML while preserving header-cell and span metadata.',
  _render_table: 'Serializes a simple header-row table as escaped pipe-table Markdown.',
  _simple_table: 'Determines whether table-cell structure can be represented as a simple Markdown table.',
  _list_context: 'Matches list-item metadata against source text and returns surrounding label and tail text when recoverable.',
  _list_html: 'Renders list items as HTML while retaining labels and adjacent text.',
  _list_markdown: 'Renders compatible list structures as Markdown and falls back when source context is irregular.',
  _heading_level: 'Returns the heading level associated with a parsed block.',
  _render_block_html: 'Converts one parsed block into its escaped HTML representation.',
  _render_block: 'Converts one parsed block into Markdown, selecting specialized table, list, and figure handling as needed.',
  parse_to_markdown: 'Builds Markdown from the parsed pages and blocks, with optional figure data and output-basename handling.',
  parse_to_html: 'Builds HTML from the parsed pages and blocks, including escaped content and figure assets.',
  markdown_bundle: 'Packages a rendered Markdown document and its available figures into a ZIP artifact.',
  render_and_save: 'Loads a serialized parse result, renders Markdown, and writes the adjacent output file.',
  save_markdown_for_doc: 'Creates the output directory and saves a Markdown export for a document.',
  save_html_for_doc: 'Creates the output directory and saves an HTML export for a document.',
  source_stem: 'Extracts and sanitizes the uploaded filename stem, including Windows-reserved names and length limits.',
  artifact_name: 'Validates an artifact basename before appending its requested suffix.',
  figure_name: 'Creates a page-and-index figure filename, optionally prefixed by the reserved output basename.',
  _occupied: 'Checks output, annotation, and image directories for case-insensitive filename-family collisions.',
  reserve_basename: 'Reserves a UTC-timestamped output basename, retrying on lock or artifact collisions and cleaning up its lock.',
  clear_chat: 'Resets the Streamlit document-chat transcript in session state.',
  load_input_preview: 'Preprocesses a requested page range and decodes its base64 image previews.',
  show_usage: 'Aggregates session token totals and estimated cost, then displays usage metrics and any incomplete-usage notice.',
  figure_assets: 'Loads figure image bytes associated with a serialized parse result and output basename.',
  extraction: 'Builds a temporary image input and patches parsing dependencies so CLI tests run without model requests.',
  test_selected_formats_only: 'Checks that requested output formats are written without creating unrequested exports.',
  test_json_skips_presentation: 'Checks that JSON-only extraction does not invoke presentation rendering.',
  test_invalid_options_fail_before_extraction: 'Checks invalid CLI options are rejected before document extraction begins.',
  test_overwrite_preserves_unrelated_files: 'Checks overwrite behavior does not remove unrelated files from the output directory.',
  test_input_inside_output_is_rejected: 'Checks the CLI rejects an input file located inside its output directory.',
  test_missing_key_fails_before_extraction: 'Checks missing credentials fail before the parser is invoked.',
  test_env_file_and_environment_precedence: 'Checks environment-file values and existing environment variables follow the expected precedence.',
  test_missing_explicit_env_file: 'Checks a requested but missing environment file produces a clear failure.',
  test_requested_export_failure_keeps_other_outputs: 'Checks one failed export does not discard successfully generated output formats.',
  test_parse_failure_writes_only_requested_diagnostics: 'Checks parse failures write diagnostics only when that output was requested.',
  test_partial_parse_and_page_range: 'Checks page-range selection and partial parsing preserve the expected outputs and diagnostics.',
  test_rendering_view_does_not_filter_json: 'Checks clean/full rendering choices do not change the JSON parse result.',
  test_graph_uses_upload_name_and_start_time_for_every_format: 'Checks all requested exports share a basename derived from the uploaded name and graph start time.',
  test_parse_success_sets_status_and_artifacts: 'Checks a successful parse sets its status and creates the expected artifacts.',
  test_parse_failure_sets_status_and_error: 'Checks parser failures are reflected in the graph result status and error field.',
  test_overlapping_runs_isolate_usage_and_artifacts: 'Checks concurrent graph runs keep their usage records and artifacts isolated.',
  test_usage_survives_post_request_failure: 'Checks token usage recorded before a later request failure remains in the result.',
  test_graph_rejects_other_models_before_preprocessing: 'Checks unsupported models are rejected before document preprocessing.',
  test_direct_compiled_graph_initializes_run_state: 'Checks direct invocation of the compiled graph initializes its run state.',
  test_partial_parse_keeps_artifacts_and_reports_filtered_pages: 'Checks partial parsing preserves artifacts and reports filtered pages.',
  test_all_filtered_pages_fail_without_markdown_or_annotation: 'Checks fully filtered documents fail without creating Markdown or annotation outputs.',
  test_source_stem: 'Checks source filenames are sanitized into safe, bounded output stems.',
  test_utc_reservation_collision_and_cleanup: 'Checks UTC basename reservations advance on collisions and always clean up lock directories.',
  test_collision_with_annotation_or_image_only: 'Checks annotation and image artifacts also prevent reuse of a basename.',
  test_json_rerender_resolves_figure_paths_with_special_characters: 'Checks rerendering finds legacy and basename-prefixed figures when names contain special characters.',
};

const nodes = [];
const edges = [];
for (const result of extracted.results) {
  const path = result.path;
  const info = fileInfo[path];
  const fileId = `file:${path}`;
  const fileComplexity = result.nonEmptyLines > 200 ? 'complex' : result.nonEmptyLines >= 50 ? 'moderate' : 'simple';
  nodes.push({
    id: fileId,
    type: 'file',
    name: path.split('/').at(-1),
    filePath: path,
    summary: info.summary,
    tags: info.tags,
    complexity: fileComplexity,
  });

  const exported = new Set((result.exports ?? []).map((item) => item.name));
  for (const fn of result.functions ?? []) {
    const lineCount = fn.endLine - fn.startLine + 1;
    const isPublicPythonName = !fn.name.startsWith('_');
    const isPytestTest = fn.name.startsWith('test_') || fn.name === 'extraction';
    if (lineCount < 10 && !isPublicPythonName && !isPytestTest) continue;
    const fnId = `function:${path}:${fn.name}`;
    const fnSummary = functionSummaries[fn.name];
    if (!fnSummary) throw new Error(`Missing grounded function summary for ${path}:${fn.name}`);
    nodes.push({
      id: fnId,
      type: 'function',
      name: fn.name,
      filePath: path,
      lineRange: [fn.startLine, fn.endLine],
      summary: fnSummary,
      tags: path.startsWith('tests/')
        ? ['test', 'pytest', info.area]
        : ['function', info.area, path === 'src/markdown.py' ? 'document-rendering' : 'application-logic'],
      complexity: lineCount > 50 ? 'complex' : lineCount >= 10 ? 'moderate' : 'simple',
    });
    edges.push({ source: fileId, target: fnId, type: 'contains', direction: 'forward', weight: 1.0 });
    if (exported.has(fn.name) && !fn.name.startsWith('_') && !fn.name.startsWith('test_') && fn.name !== 'extraction') {
      edges.push({ source: fileId, target: fnId, type: 'exports', direction: 'forward', weight: 0.8 });
    }
  }
}

for (const file of batch.files) {
  for (const targetPath of batch.batchImportData[file.path] ?? []) {
    edges.push({ source: `file:${file.path}`, target: `file:${targetPath}`, type: 'imports', direction: 'forward', weight: 0.7 });
  }
}

const validTypes = new Set(['contains', 'imports', 'calls', 'inherits', 'implements', 'exports', 'depends_on', 'tested_by']);
const nodeIds = new Set(nodes.map((node) => node.id));
if (nodeIds.size !== nodes.length) throw new Error('Duplicate node IDs in batch 14.');
for (const node of nodes) {
  if (!node.id || !node.type || !node.name || !node.summary || !node.tags?.length || !['simple', 'moderate', 'complex'].includes(node.complexity)) {
    throw new Error(`Node missing required fields: ${JSON.stringify(node)}`);
  }
}
for (const edge of edges) {
  if (!validTypes.has(edge.type) || edge.direction !== 'forward' || ![0.5, 0.6, 0.7, 0.8, 0.9, 1.0].includes(edge.weight)) {
    throw new Error(`Malformed edge: ${JSON.stringify(edge)}`);
  }
  if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) throw new Error(`Dangling edge: ${JSON.stringify(edge)}`);
}

const filePaths = batch.files.map((file) => file.path).sort((a, b) => a.localeCompare(b));
const partCount = Math.ceil(Math.max(nodes.length / 60, edges.length / 120));
const chunkSize = Math.ceil(filePaths.length / partCount);
const parts = [];
for (let index = 0; index < filePaths.length; index += chunkSize) {
  const fileSet = new Set(filePaths.slice(index, index + chunkSize));
  const partNodes = nodes.filter((node) => fileSet.has(node.filePath));
  const partIds = new Set(partNodes.map((node) => node.id));
  const partEdges = edges.filter((edge) => partIds.has(edge.source));
  const partIdSet = new Set(partNodes.map((node) => node.id));
  for (const edge of partEdges) {
    if (!partIdSet.has(edge.source) || !partIdSet.has(edge.target)) {
      throw new Error(`Split produced a cross-part or dangling edge: ${JSON.stringify(edge)}`);
    }
  }
  parts.push({ nodes: partNodes, edges: partEdges });
}

for (const stale of fs.readdirSync(`${root}/.ua/intermediate`).filter((name) => /^batch-14(?:-part-\d+)?\.json$/.test(name))) {
  fs.unlinkSync(`${root}/.ua/intermediate/${stale}`);
}
for (let index = 0; index < parts.length; index++) {
  const suffix = parts.length === 1 ? '' : `-part-${index + 1}`;
  const path = `${root}/.ua/intermediate/batch-14${suffix}.json`;
  fs.writeFileSync(path, `${JSON.stringify(parts[index], null, 2)}\n`, 'utf8');
  JSON.parse(fs.readFileSync(path, 'utf8'));
}

console.log(JSON.stringify({ filesAnalyzed: extracted.results.length, filesSkipped: extracted.filesSkipped, nodeCount: nodes.length, edgeCount: edges.length, parts: parts.map((part) => ({ nodes: part.nodes.length, edges: part.edges.length })) }, null, 2));
