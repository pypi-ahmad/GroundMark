const fs = require('node:fs');
const { execFileSync } = require('node:child_process');

const backupPath = '.ua/intermediate/meta-before-refresh.json';
if (fs.existsSync(backupPath)) throw new Error(`Refusing to overwrite ${backupPath}`);
const batches = JSON.parse(fs.readFileSync('.ua/intermediate/batches.json', 'utf8'));
const scan = JSON.parse(fs.readFileSync('.ua/intermediate/scan-result.json', 'utf8'));
const fingerprintInput = JSON.parse(fs.readFileSync('.ua/intermediate/fingerprint-input.json', 'utf8'));
if (fingerprintInput.gitCommitHash !== execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()) throw new Error('Fingerprint input commit does not match current HEAD');
if (!fs.readFileSync('.ua/fingerprints.json', 'utf8').includes('"gitCommitHash"')) throw new Error('Fingerprint store missing commit hash');

fs.copyFileSync('.ua/meta.json', backupPath);
const metadata = {
  lastAnalyzedAt: new Date().toISOString(),
  gitCommitHash: fingerprintInput.gitCommitHash,
  version: '1.0.0',
  analyzedFiles: batches.batches.reduce((total, batch) => total + batch.files.length, 0),
};
fs.writeFileSync('.ua/meta.json', `${JSON.stringify(metadata, null, 2)}\n`);
console.log(JSON.stringify({ ...metadata, totalFilesInInventory: scan.totalFiles, fingerprintBaseline: '.ua/fingerprints.json' }));
