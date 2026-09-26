import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path("D:/AI/GroundMark")
UA_DIR = PROJECT_ROOT / ".ua"
INTERMEDIATE = UA_DIR / "intermediate"
TMP = UA_DIR / "tmp"
SKILL_DIR = Path("C:/Users/ahmad/.agents/skills/understand")

batches_data = json.loads((INTERMEDIATE / "batches.json").read_text(encoding="utf-8"))
batches = batches_data.get("batches", batches_data)
total_batches = len(batches)

print(f"[Phase 2/7] Analyzing files — 70 files in {total_batches} batches...")

for i, batch in enumerate(batches):
    input_data = {
        "projectRoot": str(PROJECT_ROOT),
        "batchFiles": batch.get("files", []),
        "batchImportData": batch.get("batchImportData", {})
    }
    input_path = TMP / f"ua-file-analyzer-input-{i}.json"
    output_path = TMP / f"ua-file-extract-results-{i}.json"
    
    input_path.write_text(json.dumps(input_data, indent=2), encoding="utf-8")
    
    file_names = [f["path"] for f in batch.get("files", [])]
    preview = ", ".join(file_names[:3]) + ("..." if len(file_names) > 3 else "")
    print(f"Analyzing batch {i + 1}/{total_batches} (files: {preview})")
    
    cmd = [
        "node",
        str(SKILL_DIR / "extract-structure.mjs"),
        str(input_path),
        str(output_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error extracting batch {i}: {res.stderr}", file=sys.stderr)
        sys.exit(1)
    if not output_path.exists() or output_path.stat().st_size == 0:
        print(f"Error: missing extract output for batch {i}", file=sys.stderr)
        sys.exit(1)

print(f"Structural extraction complete for all {total_batches} batches.")
