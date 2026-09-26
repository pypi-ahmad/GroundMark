const fs = require('node:fs');

const graph = JSON.parse(fs.readFileSync('.ua/intermediate/assembled-graph.json', 'utf8'));
const fileTypes = new Set(['file', 'config', 'document', 'service', 'pipeline', 'table', 'schema', 'resource', 'endpoint']);
const fileNodeIds = new Set(graph.nodes.filter(node => fileTypes.has(node.type)).map(node => node.id));
const input = {
  fileNodes: graph.nodes.filter(node => fileTypes.has(node.type)).map(({ id, type, name, filePath, summary, tags }) => ({ id, type, name, filePath, summary, tags })),
  importEdges: graph.edges.filter(edge => edge.type === 'imports' && fileNodeIds.has(edge.source) && fileNodeIds.has(edge.target)),
  allEdges: graph.edges.filter(edge => fileNodeIds.has(edge.source) && fileNodeIds.has(edge.target)),
};
fs.writeFileSync('.ua/tmp/ua-arch-input.json', `${JSON.stringify(input, null, 2)}\n`);
console.log(JSON.stringify({ fileNodes: input.fileNodes.length, importEdges: input.importEdges.length, allFileLevelEdges: input.allEdges.length }));
