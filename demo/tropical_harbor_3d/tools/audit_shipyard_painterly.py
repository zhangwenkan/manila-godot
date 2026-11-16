"""Read-only evidence: preserve shipyard geometry and verify exported painted textures."""
import hashlib
import json
from pathlib import Path
import re
import struct
import argparse

ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT / "captures/shipyard_painterly_20261111"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=CAP)
args = parser.parse_args()


def read_glb(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<III", data)
    assert (magic, version, length) == (0x46546C67, 2, len(data))
    count, kind = struct.unpack_from("<II", data, 12)
    assert kind == 0x4E4F534A
    document = json.loads(data[20:20 + count])
    offset = 20 + count
    size, kind = struct.unpack_from("<II", data, offset)
    assert kind == 0x004E4942
    return document, data[offset + 8:offset + 8 + size]


def accessor_bytes(doc, binary, index):
    accessor = doc["accessors"][index]
    view = doc["bufferViews"][accessor["bufferView"]]
    components = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[accessor["type"]]
    width = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}[accessor["componentType"]] * components
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    stride = view.get("byteStride", width)
    if stride == width:
        return binary[offset:offset + width * accessor["count"]]
    return b"".join(binary[offset + i * stride:offset + i * stride + width] for i in range(accessor["count"]))


def geometry(doc, binary):
    result = {}
    for node in doc["nodes"]:
        if "mesh" not in node:
            continue
        entries = []
        for primitive in doc["meshes"][node["mesh"]]["primitives"]:
            attributes = dict(primitive["attributes"])
            attributes["indices"] = primitive["indices"]
            entries.append({key: hashlib.sha256(accessor_bytes(doc, binary, index)).hexdigest()
                            for key, index in attributes.items()})
        result[node["name"]] = {"transform": {key: node.get(key) for key in ("matrix", "translation", "rotation", "scale")},
                                "primitives": entries}
    return result


before, before_binary = read_glb(CAP / "before_painterly.glb")
after, after_binary = read_glb(ROOT / "assets/coast/shipyard_combined.glb")
assert geometry(before, before_binary) == geometry(after, after_binary), "Geometry / UV / normal / transform changed"
textures = []
for entry in after["images"]:
    name = re.sub(r"\.\d{3}$", "", entry["name"]).removesuffix(".png")
    if not name.startswith("Shipyard_Painterly_"):
        continue
    source = ROOT / "assets/coast/textures" / (name + ".png")
    view = after["bufferViews"][entry["bufferView"]]
    start = view.get("byteOffset", 0)
    embedded = after_binary[start:start + view["byteLength"]]
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert digest == hashlib.sha256(embedded).hexdigest(), name
    textures.append({"name": name, "sha256": digest, "matches_source_png": True})
assert len(textures) >= 7
report = {
    "geometry_uv_normals_transforms_byte_identical": True,
    "meshes": len(after["meshes"]),
    "materials": len(after["materials"]),
    "triangles": sum(after["accessors"][p["indices"]]["count"] // 3 for m in after["meshes"] for p in m["primitives"]),
    "textures": textures,
    "material_bindings": after["materials"],
}
args.output.mkdir(parents=True, exist_ok=True)
(args.output / "asset_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({key: value for key, value in report.items() if key not in ("textures", "material_bindings")}))
print("VERIFIED_PAINTED_TEXTURES", len(textures))

