const fs = require('node:fs');
const path = require('node:path');

function fail(message) { throw new Error(message); }
try {
  const [inputPath, outputPath] = process.argv.slice(2);
  if (!inputPath || !outputPath) fail('Usage: node ua-arch-analyze.js <input.json> <output.json>');
  const input = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  const nodes = input.fileNodes;
  if (!Array.isArray(nodes) || !Array.isArray(input.importEdges) || !Array.isArray(input.allEdges)) fail('Input must contain fileNodes, importEdges, and allEdges arrays');
  const byId = new Map(nodes.map(n => [n.id, n]));
  if (byId.size !== nodes.length) fail('Duplicate file node IDs');
  const clean = value => String(value || '').replace(/\\/g, '/').replace(/^\.\//, '');
  const paths = nodes.map(n => clean(n.filePath));
  const pathSegments = paths.map(p => p.split('/').filter(Boolean));
  let common = [];
  if (pathSegments.length) {
    for (let i = 0; ; i++) {
      const segment = pathSegments[0][i];
      if (!segment || pathSegments.some(parts => parts[i] !== segment)) break;
      common.push(segment);
    }
  }
  const parentDirectories = new Set(pathSegments.map(parts => parts.slice(0, -1).join('/')));
  const allFlat = parentDirectories.size <= 1;
  const groups = {};
  const groupOf = new Map();
  const flatGroup = n => {
    const p = clean(n.filePath);
    const base = path.posix.basename(p);
    if (/^(test_|.*\.test\.|.*\.spec\.)/i.test(base)) return 'test';
    if (/\.config\./i.test(base) || /^(config|settings)(\.|$)/i.test(base)) return 'config';
    return path.posix.extname(base).slice(1).toLowerCase() || '(no-extension)';
  };
  nodes.forEach((n, idx) => {
    const parts = pathSegments[idx];
    let group;
    if (allFlat) group = flatGroup(n);
    else if (parts.length <= 1) group = '(root)';
    else if (parts.length <= common.length) group = '(root)';
    else group = parts[common.length];
    groups[group] ||= [];
    groups[group].push(n.id);
    groupOf.set(n.id, group);
  });
  const typeGroups = {};
  nodes.forEach(n => { (typeGroups[n.type] ||= []).push(n.id); });
  const fanIn = Object.fromEntries(nodes.map(n => [n.id, 0]));
  const fanOut = Object.fromEntries(nodes.map(n => [n.id, 0]));
  const groupOut = new Map(Object.keys(groups).map(g => [g, new Set()]));
  const groupIn = new Map(Object.keys(groups).map(g => [g, new Set()]));
  const pairCounts = new Map();
  const intra = Object.fromEntries(Object.keys(groups).map(g => [g, { internalEdges: 0, totalEdges: 0, density: 0 }]));
  for (const edge of input.importEdges) {
    if (!byId.has(edge.source) || !byId.has(edge.target)) continue;
    fanOut[edge.source]++;
    fanIn[edge.target]++;
    const from = groupOf.get(edge.source), to = groupOf.get(edge.target);
    if (from !== to) {
      groupOut.get(from).add(to);
      groupIn.get(to).add(from);
      const key = `${from}\0${to}`;
      pairCounts.set(key, (pairCounts.get(key) || 0) + 1);
    }
    intra[from].totalEdges++;
    if (from === to) intra[from].internalEdges++;
    else intra[to].totalEdges++;
  }
  for (const stat of Object.values(intra)) stat.density = stat.totalEdges ? stat.internalEdges / stat.totalEdges : 0;
  const interGroupImports = [...pairCounts].map(([key, count]) => {
    const [from, to] = key.split('\0'); return { from, to, count };
  }).sort((a,b) => b.count-a.count || a.from.localeCompare(b.from) || a.to.localeCompare(b.to));
  const dependencyDirection = [];
  const unordered = new Set();
  for (const edge of interGroupImports) {
    const pair = [edge.from, edge.to].sort().join('\0');
    if (unordered.has(pair)) continue;
    unordered.add(pair);
    const forward = pairCounts.get(`${edge.from}\0${edge.to}`) || 0;
    const reverse = pairCounts.get(`${edge.to}\0${edge.from}`) || 0;
    if (forward >= reverse) dependencyDirection.push({ dependent: edge.from, dependsOn: edge.to, count: forward, reverseCount: reverse });
    else dependencyDirection.push({ dependent: edge.to, dependsOn: edge.from, count: reverse, reverseCount: forward });
  }
  const cross = new Map();
  for (const e of input.allEdges) {
    const source = byId.get(e.source), target = byId.get(e.target);
    if (!source || !target) continue;
    const key = `${source.type}\0${target.type}\0${e.type}`;
    cross.set(key, (cross.get(key) || 0) + 1);
  }
  const crossCategoryEdges = [...cross].map(([key, count]) => {
    const [fromType, toType, edgeType] = key.split('\0'); return { fromType, toType, edgeType, count };
  }).sort((a,b) => b.count-a.count || a.fromType.localeCompare(b.fromType));
  const patterns = {};
  const patternMap = {
    api: 'api', routes: 'api', controllers: 'api', endpoints: 'api', handlers: 'api', routers: 'api', controller: 'api', serializers: 'api', blueprints: 'api',
    services: 'service', core: 'service', lib: 'service', domain: 'service', logic: 'service', internal: 'service', signals: 'service', composables: 'service', mailers: 'service', jobs: 'service', channels: 'service',
    models: 'data', db: 'data', data: 'data', persistence: 'data', repository: 'data', entities: 'data', migrations: 'data', entity: 'data', sql: 'data', database: 'data', schema: 'data',
    components: 'ui', views: 'ui', pages: 'ui', ui: 'ui', layouts: 'ui', screens: 'ui',
    middleware: 'middleware', plugins: 'middleware', interceptors: 'middleware', guards: 'middleware',
    utils: 'utility', helpers: 'utility', common: 'utility', shared: 'utility', tools: 'utility', pkg: 'utility', templatetags: 'utility',
    config: 'config', constants: 'config', env: 'config', settings: 'config', management: 'config', commands: 'config',
    __tests__: 'test', test: 'test', tests: 'test', spec: 'test', specs: 'test',
    types: 'types', interfaces: 'types', schemas: 'types', contracts: 'types', dtos: 'types', dto: 'types', request: 'types', response: 'types',
    hooks: 'hooks', store: 'state', state: 'state', reducers: 'state', actions: 'state', slices: 'state', assets: 'assets', static: 'assets', public: 'assets', cmd: 'entry', bin: 'entry',
    docs: 'documentation', documentation: 'documentation', wiki: 'documentation', deploy: 'infrastructure', deployment: 'infrastructure', infra: 'infrastructure', infrastructure: 'infrastructure',
    '.github': 'ci-cd', '.gitlab': 'ci-cd', '.circleci': 'ci-cd', k8s: 'infrastructure', kubernetes: 'infrastructure', helm: 'infrastructure', charts: 'infrastructure', terraform: 'infrastructure', tf: 'infrastructure', docker: 'infrastructure'
  };
  for (const group of Object.keys(groups)) {
    const lc = group.toLowerCase();
    patterns[group] = patternMap[lc] || (lc.includes('test') ? 'test' : 'other');
  }
  const filePattern = n => {
    const p = clean(n.filePath), base = path.posix.basename(p);
    if (/^(test_.*|.*\.test\.[^.]+|.*\.spec\.[^.]+|.*_test\.go|.*Test\.java|.*_spec\.rb|.*Test\.php|.*Tests\.cs)$/i.test(base)) return 'test';
    if (base.endsWith('.d.ts')) return 'types';
    if (/^(index\.(ts|js)|__init__\.py)$/i.test(base)) return 'entry';
    if (/^(wsgi|asgi)\.py$/i.test(base)) return 'config';
    if (/^(Cargo\.toml|go\.mod|Gemfile|pom\.xml|build\.gradle|composer\.json)$/i.test(base)) return 'config';
    if (/^(Dockerfile|docker-compose\..*)$/i.test(base) || /\.(tf|tfvars)$/i.test(base)) return 'infrastructure';
    if (/^\.github\/workflows\//i.test(p) || /^\.gitlab-ci\.yml$/i.test(p) || /^Jenkinsfile$/i.test(base)) return 'ci-cd';
    if (/\.sql$/i.test(base)) return 'data';
    if (/\.(graphql|gql|proto)$/i.test(base)) return 'types';
    if (/\.(md|rst)$/i.test(base)) return 'documentation';
    if (base === 'Makefile') return 'infrastructure';
    return null;
  };
  const specialByGroup = {};
  for (const n of nodes) {
    const pat = filePattern(n);
    if (pat) (specialByGroup[groupOf.get(n.id)] ||= []).push({ id: n.id, pattern: pat });
  }
  const infraFiles = nodes.filter(n => {
    const p = clean(n.filePath), b = path.posix.basename(p);
    return /(^|\/)(Dockerfile|docker-compose\.)/i.test(p) || /\.(tf|tfvars)$/i.test(b) || /(^|\/)(k8s|kubernetes|helm|charts)\//i.test(p) || /(^|\/)(\.github|\.gitlab|\.circleci)\//i.test(p) || b === 'Jenkinsfile' || /\.gitlab-ci\.yml$/i.test(b);
  }).map(n => n.filePath);
  const deploymentTopology = {
    hasDockerfile: nodes.some(n => /^Dockerfile(?:\.|$)/i.test(path.posix.basename(clean(n.filePath)))),
    hasCompose: nodes.some(n => /^docker-compose\./i.test(path.posix.basename(clean(n.filePath)))),
    hasK8s: nodes.some(n => /(^|\/)(k8s|kubernetes|helm|charts)\//i.test(clean(n.filePath))),
    hasTerraform: nodes.some(n => /\.(tf|tfvars)$/i.test(clean(n.filePath))),
    hasCI: nodes.some(n => /^\.github\/workflows\//i.test(clean(n.filePath)) || /^\.gitlab-ci\.yml$/i.test(clean(n.filePath)) || /(^|\/)Jenkinsfile$/i.test(clean(n.filePath))),
    infraFiles
  };
  const schemaFiles = nodes.filter(n => /\.(sql|graphql|gql|proto|prisma)$/i.test(clean(n.filePath))).map(n => n.filePath);
  const migrationFiles = nodes.filter(n => /(^|\/)migrations?\//i.test(clean(n.filePath))).map(n => n.filePath);
  const dataModelFiles = nodes.filter(n => /(^|\/)(models?|entities|entity|schemas?)\//i.test(clean(n.filePath)) && !/\.(md|rst)$/i.test(clean(n.filePath))).map(n => n.filePath);
  const apiHandlerFiles = nodes.filter(n => /(^|\/)(routes?|routers?|controllers?|handlers?|endpoints?)\//i.test(clean(n.filePath))).map(n => n.filePath);
  const docs = nodes.filter(n => n.type === 'document' || /\.(md|rst)$/i.test(clean(n.filePath)));
  const docsGroups = new Set();
  for (const doc of docs) {
    const group = groupOf.get(doc.id);
    docsGroups.add(group);
    for (const e of input.allEdges) if (e.source === doc.id && byId.has(e.target) && /document|related/i.test(e.type)) docsGroups.add(groupOf.get(e.target));
  }
  const undocumentedGroups = Object.keys(groups).filter(g => !docsGroups.has(g));
  const fileStats = {
    totalFileNodes: nodes.length,
    filesPerGroup: Object.fromEntries(Object.entries(groups).map(([g, ids]) => [g, ids.length])),
    nodeTypeCounts: Object.fromEntries(Object.entries(typeGroups).map(([t, ids]) => [t, ids.length]))
  };
  const result = {
    scriptCompleted: true,
    commonPathPrefix: common.length ? `${common.join('/')}/` : '',
    directoryGroups: groups,
    nodeTypeGroups: typeGroups,
    crossCategoryEdges,
    nonCodeConnections: input.allEdges.filter(e => byId.has(e.source) && byId.has(e.target) && byId.get(e.source).type !== 'file' && byId.get(e.target).type === 'file').map(e => ({ source: e.source, target: e.target, edgeType: e.type })),
    interGroupImports,
    intraGroupDensity: intra,
    patternMatches: patterns,
    filePatternMatches: specialByGroup,
    deploymentTopology,
    dataPipeline: { schemaFiles, migrationFiles, dataModelFiles, apiHandlerFiles },
    docCoverage: { groupsWithDocs: docsGroups.size, totalGroups: Object.keys(groups).length, coverageRatio: Object.keys(groups).length ? docsGroups.size / Object.keys(groups).length : 0, undocumentedGroups },
    dependencyDirection,
    fileStats,
    fileFanIn: fanIn,
    fileFanOut: fanOut
  };
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
} catch (err) {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
}
