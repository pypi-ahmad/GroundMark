const fs = require('node:fs');

const input = JSON.parse(fs.readFileSync('.ua/tmp/ua-arch-input.json', 'utf8'));
const structural = JSON.parse(fs.readFileSync('.ua/tmp/ua-arch-results.json', 'utf8'));
if (!structural.scriptCompleted || structural.fileStats.totalFileNodes !== input.fileNodes.length) throw new Error('Structural results do not match input file-node count');

const layers = [
  { id: 'layer:user-interface', name: 'CLI & User Interface', description: 'Command-line and Streamlit entry points, UI helpers, and the Windows launcher that expose GroundMark workflows.', nodeIds: [] },
  { id: 'layer:document-chat', name: 'Document Chat & Reasoning', description: 'Conversational question answering and citation-grounding logic for parsed document pages.', nodeIds: [] },
  { id: 'layer:pipeline-orchestration', name: 'Pipeline Orchestration & State Graph', description: 'The parser facade, LangGraph execution graph, export coordination, and run-safe artifact naming.', nodeIds: [] },
  { id: 'layer:layout-and-vision-engine', name: 'Layout Analysis & Document Vision', description: 'Document raster preparation, layout and reading-order analysis, visual annotation, figure handling, and structured rendering.', nodeIds: [] },
  { id: 'layer:model-and-inference', name: 'Model Access & Telemetry Core', description: 'LLM access, prompt-template resolution, typed document models, API diagnostics, and token-cost accounting.', nodeIds: [] },
  { id: 'layer:evaluation-and-benchmarks', name: 'Evaluation & Quality Benchmarks', description: 'CLI benchmark runners and recorded evaluation reports for chat, layout, prompts, resolution, and diagnostics.', nodeIds: [] },
  { id: 'layer:testing-and-fixtures', name: 'Test Suite & Mocks', description: 'Automated regression tests, deterministic LLM substitutes, and synthetic or golden document fixtures.', nodeIds: [] },
  { id: 'layer:documentation-and-prompts', name: 'Documentation & Runtime Prompts', description: 'User and developer guides, OpenWiki and OKF indexes, architecture diagrams, and runtime instructions for parsing and grounded answers.', nodeIds: [] },
  { id: 'layer:configuration-and-build', name: 'Configuration & Build Environment', description: 'Python packaging and environment settings, dependency manifests, OpenWiki run metadata, and the documentation-refresh CI workflow.', nodeIds: [] }
];
const layerById = new Map(layers.map(layer => [layer.id, layer]));

function assign(node) {
  const p = String(node.filePath || '').replace(/\\/g, '/');
  const base = p.split('/').at(-1);
  if (p.startsWith('tests/')) return 'layer:testing-and-fixtures';
  if (p.startsWith('scripts/')) return 'layer:evaluation-and-benchmarks';
  if (p.startsWith('src/ui/') || p === 'src/cli.py' || p === 'run.cmd') return 'layer:user-interface';
  if (p === 'src/chat.py') return 'layer:document-chat';
  if (['src/graph.py', 'src/parse.py', 'src/export.py', 'src/output_names.py', 'src/__init__.py'].includes(p)) return 'layer:pipeline-orchestration';
  if (['src/layout.py', 'src/preprocess.py', 'src/annotate.py', 'src/figures.py', 'src/markdown.py'].includes(p)) return 'layer:layout-and-vision-engine';
  if (p.startsWith('src/')) return 'layer:model-and-inference';
  if (p.startsWith('docs/') && /evaluation|diagnostics/i.test(base)) return 'layer:evaluation-and-benchmarks';
  if (p.startsWith('openwiki/') && /^\.(last-update|page-manifest)\.json$/.test(base)) return 'layer:configuration-and-build';
  if (node.type === 'pipeline') return 'layer:configuration-and-build';
  if (p.startsWith('groundmark-architecture')) return 'layer:documentation-and-prompts';
  if (node.type === 'config' && !p.startsWith('docs/') && !p.startsWith('openwiki/.claims/')) return 'layer:configuration-and-build';
  if (p.startsWith('docs/') || p.startsWith('openwiki/') || p.startsWith('prompts/') || p.startsWith('knowledge/')) return 'layer:documentation-and-prompts';
  if (node.type === 'document' && /^(requirements|requirements-dev)\.txt$/.test(base)) return 'layer:configuration-and-build';
  if (node.type === 'document' || p === 'README.md' || p === 'AGENTS.md' || p === 'CLAUDE.md') return 'layer:documentation-and-prompts';
  return 'layer:configuration-and-build';
}

const seen = new Set();
for (const node of input.fileNodes) {
  if (!node.id || seen.has(node.id)) throw new Error(`Missing or duplicate input ID: ${node.id}`);
  seen.add(node.id);
  const id = assign(node);
  const layer = layerById.get(id);
  if (!layer) throw new Error(`Unknown layer ${id} for ${node.id}`);
  layer.nodeIds.push(node.id);
}

const outputIds = layers.flatMap(layer => layer.nodeIds);
if (layers.length < 3 || layers.length > 10) throw new Error(`Invalid layer count: ${layers.length}`);
if (layers.some(layer => !layer.nodeIds.length)) throw new Error(`Empty layer: ${layers.find(layer => !layer.nodeIds.length).id}`);
if (outputIds.length !== input.fileNodes.length || new Set(outputIds).size !== input.fileNodes.length || outputIds.some(id => !seen.has(id))) throw new Error('Layer assignments do not cover every file node exactly once');

fs.writeFileSync('.ua/intermediate/layers.json', `${JSON.stringify(layers, null, 2)}\n`, 'utf8');
console.log(JSON.stringify(layers.map(({ id, name, nodeIds }) => ({ id, name, count: nodeIds.length })), null, 2));
