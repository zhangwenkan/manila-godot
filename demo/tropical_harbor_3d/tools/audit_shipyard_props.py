"""Read-only GLB and texture verification for the shipyard prop refinement."""
import hashlib
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT / "captures/shipyard_props_20261111"

def read_glb(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<III", data)
    assert magic == 0x46546C67 and version == 2 and length == len(data)
    n, kind = struct.unpack_from("<II", data, 12)
    assert kind == 0x4E4F534A
    document = json.loads(data[20:20 + n])
    binary_start = 20 + n
    bn, bt = struct.unpack_from("<II", data, binary_start)
    assert bt == 0x004E4942
    return document, data[binary_start + 8:binary_start + 8 + bn]

doc, binary = read_glb(ROOT / "assets/coast/shipyard_combined.glb")
old, _ = read_glb(CAP / "before_props.glb")
def statistics(d):
    return {
        "nodes": len(d["nodes"]), "meshes": len(d["meshes"]),
        "materials": len(d["materials"]),
        "triangles": sum(d["accessors"][p["indices"]]["count"] // 3
                         for m in d["meshes"] for p in m["primitives"]),
    }
report = {"before": statistics(old), "after": statistics(doc), "textures": [], "prop_materials": []}
for material in doc["materials"]:
    if "_Props_" not in material["name"]:
        continue
    item = {"name": material["name"], "normal": material.get("normalTexture"),
            "pbr": material.get("pbrMetallicRoughness")}
    report["prop_materials"].append(item)
    if "WornSteel" not in material["name"]:
        assert material.get("normalTexture"), material["name"]
        assert material["pbrMetallicRoughness"].get("baseColorTexture")
        assert material["pbrMetallicRoughness"].get("metallicRoughnessTexture")
for im in doc["images"]:
    if "_Props_" not in im.get("name", ""):
        continue
    name = re.sub(r"\.\d{3}$", "", im["name"])
    source = ROOT / "assets/coast/textures" / (name + ".png")
    bv = doc["bufferViews"][im["bufferView"]]
    start = bv.get("byteOffset", 0)
    embedded = binary[start:start + bv["byteLength"]]
    same = hashlib.sha256(embedded).digest() == hashlib.sha256(source.read_bytes()).digest()
    assert same, name
    report["textures"].append({"name": name, "matches_source_png": same, "bytes": len(embedded)})
assert len(report["textures"]) == 9
assert len(report["prop_materials"]) == 4
(CAP / "asset_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
