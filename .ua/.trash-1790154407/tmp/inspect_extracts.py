import json
from pathlib import Path

for i in range(9):
    p = Path(f".ua/tmp/ua-file-extract-results-{i}.json")
    if p.exists():
        data = json.loads(p.read_text(encoding='utf-8'))
        print(f"Batch {i}: {len(data.get('results', []))} files analyzed")
        for res in data.get('results', []):
            funcs = [f['name'] for f in res.get('functions', [])]
            classes = [c['name'] for c in res.get('classes', [])]
            if funcs or classes:
                print(f"  {res['path']}: {len(funcs)} funcs ({funcs[:3]}...), {len(classes)} classes ({classes[:3]}...)")
