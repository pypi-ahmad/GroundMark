const fs = require('node:fs');
const { execFileSync } = require('node:child_process');

const scan = JSON.parse(fs.readFileSync('.ua/intermediate/scan-result.json', 'utf8'));
const graph = JSON.parse(fs.readFileSync('.ua/intermediate/assembled-graph.json', 'utf8'));
const sourceFilePaths = scan.files.map(file => file.path);
if (sourceFilePaths.length !== scan.totalFiles) throw new Error('Scan inventory count mismatch');
const gitCommitHash = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
if (graph.project.gitCommitHash !== gitCommitHash) throw new Error('Graph commit hash does not match current HEAD');

const backupPath = '.ua/intermediate/fingerprints-before-refresh.json';
if (fs.existsSync(backupPath)) throw new Error(`Refusing to overwrite ${backupPath}`);
fs.copyFileSync('.ua/fingerprints.json', backupPath);
fs.copyFileSync('.ua/intermediate/assembled-graph.json', '.ua/knowledge-graph.json');

const fingerprintInput = {
  projectRoot: process.cwd(),
  sourceFilePaths,
  gitCommitHash,
};
fs.writeFileSync('.ua/intermediate/fingerprint-input.json', `${JSON.stringify(fingerprintInput, null, 2)}\n`);
console.log(JSON.stringify({ graphSaved: '.ua/knowledge-graph.json', sourceFilePaths: sourceFilePaths.length, gitCommitHash, fingerprintsBackedUp: backupPath }));
