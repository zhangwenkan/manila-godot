"""Read-only audit of the reference harbor's exported GLB assets."""
from pathlib import Path
import argparse
import hashlib
import json
import struct

ART = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=ART / "captures/reference_rebuild_20261116")
args = parser.parse_args()
results = []
for path in sorted((ART / "assets/reference").glob("*.glb")):
    blob = path.read_bytes()
    assert blob[:4] == b"glTF"
    size = struct.unpack_from("<I", blob, 12)[0]
    doc = json.loads(blob[20:20 + size])
    triangles = 0
    for mesh in doc.get("meshes", []):
        for primitive in mesh["primitives"]:
            attributes = primitive["attributes"]
            assert "POSITION" in attributes and "NORMAL" in attributes and "TEXCOORD_0" in attributes, path.name
            assert doc["accessors"][attributes["POSITION"]]["count"] > 0, path.name
            triangles += doc["accessors"][primitive["indices"]]["count"] // 3
    assert doc.get("meshes") and doc.get("nodes"), path.name
    results.append({
        "file": path.name, "sha256": hashlib.sha256(blob).hexdigest(),
        "bytes": len(blob), "meshes": len(doc["meshes"]), "triangles": triangles,
        "materials": len(doc.get("materials", [])), "images": len(doc.get("images", [])),
    })
expected = {"boat", "cargo_ginseng", "cargo_jade", "cargo_nutmeg", "cargo_silk",
            "coast", "town", "cargo_port", "foliage", "ocean", "rocks", "terrain"}
assert {Path(row["file"]).stem for row in results} == expected, "Runtime export set must match the harbor assembly"
target = args.output
target.mkdir(parents=True, exist_ok=True)
(target / "asset_audit.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(json.dumps(results, indent=2))
