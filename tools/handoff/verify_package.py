"""Verify an extracted private handoff; missing optional material is reported separately."""
import hashlib
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
bad, missing_optional, checked = [], 0, 0
for record in manifest["files"]:
    path = root / record["path"]
    if not path.is_file():
        if record["archive"] == "02-history-materials.zip":
            missing_optional += 1
        else:
            bad.append((record["path"], "missing"))
        continue
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != record["sha256"]:
        bad.append((record["path"], "sha256 mismatch"))
    checked += 1
    if checked % 1000 == 0:
        print("Verified", checked, "files", flush=True)
print("Verified:", checked, "Optional files not extracted:", missing_optional, "Failures:", len(bad))
for issue in bad:
    print(*issue)
raise SystemExit(bool(bad))
