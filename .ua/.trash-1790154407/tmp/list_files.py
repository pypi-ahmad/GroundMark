import json
from pathlib import Path

scan = json.loads(Path('.ua/intermediate/scan-result.json').read_text(encoding='utf-8'))
for f in scan['files']:
    print(f"{f['path']:50} | {f['fileCategory']:8} | {f.get('sizeLines', 0):4} lines")
