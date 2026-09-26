const fs = require('node:fs');

function fail(message) {
  console.error(message);
  process.exit(1);
}

const [inputPath, outputPath] = process.argv.slice(2);
if (!inputPath || !outputPath) fail('Usage: node ua-tour-analyze.js <input.json> <output.json>');

try {
  const graph = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  const nodes = graph.nodes;
  const edges = graph.edges;
  if (!Array.isArray(nodes) || !Array.isArray(edges) || !Array.isArray(graph.layers)) {
    fail('Input must contain nodes, edges, and layers arrays.');
  }
  const byId = new Map(nodes.map(node => [node.id, node]));
  const incoming = new Map(nodes.map(node => [node.id, new Set()]));
  const outgoing = new Map(nodes.map(node => [node.id, new Set()]));
  for (const edge of edges) {
    if (!byId.has(edge.source) || !byId.has(edge.target)) continue;
    incoming.get(edge.target).add(edge.source);
    outgoing.get(edge.source).add(edge.target);
  }
  const fanInRanking = nodes.map(node => ({ id: node.id, fanIn: incoming.get(node.id).size, name: node.name }))
    .sort((a, b) => b.fanIn - a.fanIn || a.id.localeCompare(b.id)).slice(0, 20);
  const fanOutRanking = nodes.map(node => ({ id: node.id, fanOut: outgoing.get(node.id).size, name: node.name }))
    .sort((a, b) => b.fanOut - a.fanOut || a.id.localeCompare(b.id)).slice(0, 20);
  const fanOutValues = nodes.map(n => outgoing.get(n.id).size).sort((a, b) => a - b);
  const fanInValues = nodes.map(n => incoming.get(n.id).size).sort((a, b) => a - b);
  const p90Out = fanOutValues[Math.max(0, Math.ceil(fanOutValues.length * 0.9) - 1)] || 0;
  const p25In = fanInValues[Math.max(0, Math.ceil(fanInValues.length * 0.25) - 1)] || 0;
  const candidates = [];
  for (const node of nodes) {
    const path = node.filePath || '';
    const name = node.name || path.split(/[\\/]/).pop() || node.id;
    let score = 0;
    if (node.type === 'file') {
      if (/^(index\.(ts|js)|main\.(ts|js|py|rs|go|cpp|c)|app\.(ts|js|py)|server\.(ts|js)|mod\.rs|manage\.py|wsgi\.py|asgi\.py|run\.py|__main__\.py|Application\.java|Main\.java|Program\.cs|config\.ru|index\.php|App\.swift|Application\.kt)$/i.test(name)) score += 3;
      if (path && path.split(/[\\/]/).length <= 2) score += 1;
      if (outgoing.get(node.id).size >= p90Out && p90Out > 0) score += 1;
      if (incoming.get(node.id).size <= p25In) score += 1;
    } else if (node.type === 'document') {
      if (path.replaceAll('\\', '/') === 'README.md') score += 5;
      else if (/^[^/]+\.md$/i.test(path.replaceAll('\\', '/'))) score += 2;
    }
    if (score > 0) candidates.push({ id: node.id, score, name, summary: node.summary || '' });
  }
  candidates.sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
  const codeCandidates = candidates.filter(candidate => byId.get(candidate.id).type === 'file');
  const start = codeCandidates[0]?.id;
  const adjacency = new Map(nodes.map(n => [n.id, new Set()]));
  for (const edge of edges) {
    if ((edge.type === 'imports' || edge.type === 'calls') && adjacency.has(edge.source) && adjacency.has(edge.target)) {
      adjacency.get(edge.source).add(edge.target);
    }
  }
  const order = [], depthMap = {};
  if (start) {
    const queue = [start];
    depthMap[start] = 0;
    for (let i = 0; i < queue.length; i++) {
      const current = queue[i];
      order.push(current);
      for (const neighbor of adjacency.get(current) || []) {
        if (!(neighbor in depthMap)) {
          depthMap[neighbor] = depthMap[current] + 1;
          queue.push(neighbor);
        }
      }
    }
  }
  const byDepth = {};
  for (const id of order) (byDepth[depthMap[id]] ||= []).push(id);
  const inventory = type => nodes.filter(n => n.type === type).map(n => ({ id: n.id, name: n.name, summary: n.summary || '' }));
  const infraTypes = new Set(['service', 'pipeline', 'resource']);
  const dataTypes = new Set(['table', 'schema', 'endpoint']);
  const nonCodeFiles = {
    documentation: inventory('document'),
    infrastructure: nodes.filter(n => infraTypes.has(n.type)).map(n => ({ id: n.id, name: n.name, type: n.type, summary: n.summary || '' })),
    data: nodes.filter(n => dataTypes.has(n.type)).map(n => ({ id: n.id, name: n.name, type: n.type, summary: n.summary || '' })),
    config: inventory('config')
  };
  const importCall = new Map(nodes.map(n => [n.id, new Set()]));
  for (const edge of edges) {
    if (edge.type === 'imports' || edge.type === 'calls') {
      if (importCall.has(edge.source) && importCall.has(edge.target)) importCall.get(edge.source).add(edge.target);
    }
  }
  const mutual = new Map(nodes.map(n => [n.id, new Set()]));
  for (const node of nodes) {
    for (const other of importCall.get(node.id)) {
      if (importCall.get(other)?.has(node.id)) mutual.get(node.id).add(other);
    }
  }
  const clusters = [];
  const covered = new Set();
  for (const node of nodes) {
    if (!mutual.get(node.id).size || covered.has(node.id)) continue;
    let group = new Set([node.id, ...mutual.get(node.id)]);
    let expanded = true;
    while (expanded && group.size < 5) {
      expanded = false;
      for (const candidate of nodes) {
        if (group.has(candidate.id)) continue;
        const connects = [...group].filter(id => mutual.get(candidate.id).has(id)).length;
        if (connects >= 2) { group.add(candidate.id); expanded = true; break; }
      }
    }
    if (group.size < 2) continue;
    const ids = [...group].sort();
    for (const id of ids) covered.add(id);
    let edgeCount = 0;
    for (const a of ids) for (const b of ids) if (a !== b && importCall.get(a).has(b)) edgeCount++;
    clusters.push({ nodes: ids, edgeCount });
  }
  clusters.sort((a, b) => b.edgeCount - a.edgeCount || b.nodes.length - a.nodes.length);
  const result = {
    scriptCompleted: true,
    entryPointCandidates: candidates.slice(0, 5),
    fanInRanking,
    fanOutRanking,
    bfsTraversal: { startNode: start || null, order, depthMap, byDepth },
    nonCodeFiles,
    clusters: clusters.slice(0, 10),
    layers: { count: graph.layers.length, list: graph.layers.map(({ id, name, description }) => ({ id, name, description })) },
    nodeSummaryIndex: Object.fromEntries(nodes.map(n => [n.id, { name: n.name, type: n.type, summary: n.summary || '' }])),
    totalNodes: nodes.length,
    totalEdges: edges.length
  };
  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2) + '\n', 'utf8');
} catch (error) {
  fail(error.stack || String(error));
}
