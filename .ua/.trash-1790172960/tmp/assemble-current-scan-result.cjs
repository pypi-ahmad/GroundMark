const fs = require('node:fs');

const previousPath = '.ua/intermediate/scan-result.json';
const backupPath = '.ua/intermediate/scan-result-before-refresh.json';
if (fs.existsSync(backupPath)) throw new Error(`Refusing to overwrite ${backupPath}`);
const previous = JSON.parse(fs.readFileSync(previousPath, 'utf8'));
const scan = JSON.parse(fs.readFileSync('.ua/intermediate/scan-current.json', 'utf8'));
const imports = JSON.parse(fs.readFileSync('.ua/intermediate/import-map-current.json', 'utf8'));
if (scan.files.length !== scan.totalFiles) throw new Error('Current scan file count mismatch');
if (Object.keys(imports.importMap).length !== scan.files.length) throw new Error('Import map does not cover the current inventory');

fs.copyFileSync(previousPath, backupPath);
const excludedLanguageLabels = new Set(['config', 'unknown', 'whl', 'txt']);
const currentResult = {
  ...previous,
  languages: Object.keys(scan.stats.byLanguage).filter(language => !excludedLanguageLabels.has(language)).sort(),
  files: scan.files,
  totalFiles: scan.totalFiles,
  filteredByIgnore: scan.filteredByIgnore,
  estimatedComplexity: scan.estimatedComplexity,
  stats: scan.stats,
  importMap: imports.importMap,
};
fs.writeFileSync(previousPath, `${JSON.stringify(currentResult, null, 2)}\n`);
console.log(JSON.stringify({ totalFiles: currentResult.totalFiles, importMapEntries: Object.keys(currentResult.importMap).length, languageCount: currentResult.languages.length, backupPath }));
