const fs = require('node:fs');
const { execFileSync } = require('node:child_process');

const graphPath = '.ua/intermediate/assembled-graph.json';
const graph = JSON.parse(fs.readFileSync(graphPath, 'utf8'));
const layersRaw = JSON.parse(fs.readFileSync('.ua/intermediate/layers.json', 'utf8'));
const tourRaw = JSON.parse(fs.readFileSync('.ua/intermediate/tour.json', 'utf8'));
const scan = JSON.parse(fs.readFileSync('.ua/intermediate/scan-result.json', 'utf8'));
const batches = JSON.parse(fs.readFileSync('.ua/intermediate/batches.json', 'utf8'));
const analyzedFiles = batches.batches.reduce((total, batch) => total + batch.files.length, 0);
const knownTypes = new Set(['file', 'config', 'document', 'service', 'pipeline', 'table', 'schema', 'resource', 'endpoint']);
const nodeIds = new Set(graph.nodes.map(node => node.id));
const prefixes = ['file:', 'config:', 'document:', 'service:', 'pipeline:', 'table:', 'schema:', 'resource:', 'endpoint:'];
const toNodeId = value => {
  if (typeof value !== 'string' || !value) return value;
  return prefixes.some(prefix => value.startsWith(prefix)) ? value : `file:${value.replace(/\\/g, '/')}`;
};

let layers = Array.isArray(layersRaw) ? layersRaw : layersRaw.layers;
if (!Array.isArray(layers)) throw new Error('layers.json is not an array or layers envelope');
layers = layers.map((layer, index) => {
  const nodeIdsRaw = layer.nodeIds ?? layer.nodes ?? [];
  return {
    id: layer.id || `layer:${String(layer.name || `layer-${index + 1}`).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')}`,
    name: String(layer.name || `Layer ${index + 1}`),
    description: String(layer.description || 'Project files grouped by architectural responsibility.'),
    nodeIds: (Array.isArray(nodeIdsRaw) ? nodeIdsRaw : []).map(value => toNodeId(typeof value === 'object' && value ? value.id : value).replace(/\\/g, '/')).filter(id => nodeIds.has(id)),
  };
});

let tour = Array.isArray(tourRaw) ? tourRaw : tourRaw.steps;
if (!Array.isArray(tour)) throw new Error('tour.json is not an array or steps envelope');
tour = tour.map((step, index) => {
  const refs = step.nodeIds ?? step.nodesToInspect ?? [];
  const normalized = {
    order: Number.isInteger(step.order) ? step.order : index + 1,
    title: String(step.title || `Tour Step ${index + 1}`),
    description: String(step.description || step.whyItMatters || 'This step introduces an important part of the project.'),
    nodeIds: (Array.isArray(refs) ? refs : []).map(toNodeId).filter(id => nodeIds.has(id)),
  };
  if (typeof step.languageLesson === 'string') normalized.languageLesson = step.languageLesson;
  return normalized;
}).sort((a, b) => a.order - b.order);
tour.forEach((step, index) => { step.order = index + 1; });

const commit = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
const finalGraph = {
  version: '1.0.0',
  project: {
    name: scan.projectName,
    languages: scan.languages,
    frameworks: scan.frameworks,
    description: scan.projectDescription,
    analyzedAt: new Date().toISOString(),
    gitCommitHash: commit,
  },
  nodes: graph.nodes,
  edges: graph.edges,
  layers,
  tour,
};

const fileLevelIds = new Set(finalGraph.nodes.filter(node => knownTypes.has(node.type)).map(node => node.id));
const layerRefs = layers.flatMap(layer => layer.nodeIds);
const duplicateLayerRefs = layerRefs.filter((id, index) => layerRefs.indexOf(id) !== index);
const missingLayerRefs = [...fileLevelIds].filter(id => !layerRefs.includes(id));
const invalidTourRefs = tour.flatMap(step => step.nodeIds.filter(id => !nodeIds.has(id)));
if (duplicateLayerRefs.length || missingLayerRefs.length || invalidTourRefs.length) {
  throw new Error(JSON.stringify({ duplicateLayerRefs, missingLayerRefs, invalidTourRefs }));
}

fs.writeFileSync(graphPath, `${JSON.stringify(finalGraph, null, 2)}\n`);
console.log(JSON.stringify({ project: finalGraph.project.name, filesInInventory: scan.totalFiles, analyzedFiles, nodes: finalGraph.nodes.length, edges: finalGraph.edges.length, layers: layers.length, tourSteps: tour.length, gitCommitHash: commit }));
