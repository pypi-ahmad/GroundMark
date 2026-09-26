const fs = require('node:fs');
const path = require('node:path');

const intermediate = path.resolve('.ua/intermediate');
const batches = JSON.parse(fs.readFileSync(path.join(intermediate, 'batches.json'), 'utf8'));
const expected = new Set(batches.batches.map(batch => batch.batchIndex));
const names = fs.readdirSync(intermediate).filter(name => /^batch-\d+(?:-part-\d+)?\.json$/.test(name));
const covered = new Set();

for (const name of names) {
  const index = Number(name.match(/^batch-(\d+)/)[1]);
  if (!expected.has(index)) throw new Error(`Unexpected batch output ${name}`);
  const fragment = JSON.parse(fs.readFileSync(path.join(intermediate, name), 'utf8'));
  if (!Array.isArray(fragment.nodes) || !Array.isArray(fragment.edges)) throw new Error(`Invalid graph fragment ${name}`);
  for (const node of fragment.nodes) {
    if (node.filePath) covered.add(`${index}|${node.filePath.replace(/\\/g, '/')}`);
  }
}

const missingBatches = [...expected].filter(index => !names.some(name => name === `batch-${index}.json` || name.startsWith(`batch-${index}-part-`)));
const missingFiles = [];
for (const batch of batches.batches) {
  for (const file of batch.files) {
    if (!covered.has(`${batch.batchIndex}|${file.path}`)) missingFiles.push(`${batch.batchIndex}:${file.path}`);
  }
}
if (missingBatches.length || missingFiles.length) throw new Error(JSON.stringify({ missingBatches, missingFiles }));
console.log(JSON.stringify({ expectedBatches: expected.size, outputs: names.length, changedFilesCovered: covered.size, ok: true }));

const changed = new Set(fs.readFileSync('.ua/tmp/changed-files.txt', 'utf8').split(/\r?\n/).filter(Boolean).map(file => file.replace(/\\/g, '/')));
const oldGraph = JSON.parse(fs.readFileSync('.ua/knowledge-graph.json', 'utf8'));
const removedIds = new Set(oldGraph.nodes.filter(node => node.filePath && changed.has(node.filePath.replace(/\\/g, '/'))).map(node => node.id));
const nodes = oldGraph.nodes.filter(node => !removedIds.has(node.id));
const edges = oldGraph.edges.filter(edge => !removedIds.has(edge.source) && !removedIds.has(edge.target));
const outputPath = path.join(intermediate, 'batch-existing.json');
fs.writeFileSync(outputPath, `${JSON.stringify({ nodes, edges }, null, 2)}\n`);
console.log(JSON.stringify({ prunedNodes: oldGraph.nodes.length - nodes.length, prunedEdges: oldGraph.edges.length - edges.length, retainedNodes: nodes.length, retainedEdges: edges.length, output: outputPath }));
