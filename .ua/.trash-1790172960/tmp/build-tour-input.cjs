const fs = require('node:fs');

const graph = JSON.parse(fs.readFileSync('.ua/intermediate/assembled-graph.json', 'utf8'));
const layers = JSON.parse(fs.readFileSync('.ua/intermediate/layers.json', 'utf8'));
const input = {
  nodes: graph.nodes.map(({ id, type, name, filePath, summary }) => ({ id, type, name, filePath, summary })),
  edges: graph.edges,
  layers: layers.map(({ id, name, description }) => ({ id, name, description })),
};
fs.writeFileSync('.ua/tmp/ua-tour-input.json', `${JSON.stringify(input, null, 2)}\n`);
console.log(JSON.stringify({ nodes: input.nodes.length, edges: input.edges.length, layers: input.layers.length }));
