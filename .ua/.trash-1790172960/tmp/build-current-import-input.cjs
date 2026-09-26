const fs = require('node:fs');

const scan = JSON.parse(fs.readFileSync('.ua/intermediate/scan-current.json', 'utf8'));
const input = {
  projectRoot: process.cwd(),
  files: scan.files.map(({ path, language, fileCategory }) => ({ path, language, fileCategory })),
};
fs.writeFileSync('.ua/tmp/ua-import-map-input-current.json', `${JSON.stringify(input, null, 2)}\n`);
console.log(JSON.stringify({ projectRoot: input.projectRoot, files: input.files.length }));
