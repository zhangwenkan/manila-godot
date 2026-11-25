"""Read-only S23 disk audit. Run again after export/import; never invokes Blender/Godot."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "demo/tropical_harbor_3d/assets/reference"
LOG = ROOT / "demo/tropical_harbor_3d/captures/rock_path_sample_20261123"


def digest(path: Path, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def read_glb(path: Path):
    raw = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", raw)
    assert magic == b"glTF" and version == 2 and length == len(raw)
    chunks = {}
    offset = 12
    while offset < len(raw):
        size, kind = struct.unpack_from("<II", raw, offset)
        chunks[kind] = raw[offset + 8:offset + 8 + size]
        offset += 8 + size
    return json.loads(chunks[0x4E4F534A]), chunks[0x004E4942]


def accessor(document, binary, index):
    item = document["accessors"][index]
    assert "sparse" not in item, "Sparse accessors need explicit handling"
    view = document["bufferViews"][item["bufferView"]]
    code, size = {5121: ("B", 1), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}[item["componentType"]]
    channels = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[item["type"]]
    stride = view.get("byteStride", size * channels)
    offset = view.get("byteOffset", 0) + item.get("byteOffset", 0)
    values = [struct.unpack_from("<" + code * channels, binary, offset + i * stride) for i in range(item["count"])]
    if item.get("normalized"):
        divisor = {5121: 255, 5123: 65535}[item["componentType"]]
        values = [tuple(x / divisor for x in row) for row in values]
    return values


def max_error(actual, expected):
    return max(abs(a - b) for actual_row, expected_row in zip(actual, expected)
               for a, b in zip(actual_row, expected_row))


def audit():
    report = {"read_only": True, "visual_accepted": False}
    baseline = json.loads((LOG / "before_hashes.json").read_text(encoding="utf-8-sig"))
    hashes = []
    for row in baseline:
        path = ROOT / row["path"].replace("\\", "/")
        current = digest(path) if path.exists() else None
        hashes.append({"path": row["path"], "sha256": current, "unchanged": current == row["sha256"]})
    report["baseline_hashes"] = hashes
    report["preserved_glbs_ok"] = all(row["unchanged"] for row in hashes
        if row["path"].endswith(".glb") and not row["path"].endswith("terrain.glb"))

    document, binary = read_glb(ART / "terrain.glb")
    # Exported terrain is already Y-up; unexpected node transforms must be inspected.
    nodes = document.get("nodes", [])
    report["unhandled_node_transforms"] = [node for node in nodes
        if any(key in node for key in ("matrix", "translation", "rotation", "scale"))]
    primitive = document["meshes"][0]["primitives"][0]
    attributes = primitive["attributes"]
    positions = accessor(document, binary, attributes["POSITION"])
    colors = accessor(document, binary, attributes["COLOR_0"])
    uv0 = accessor(document, binary, attributes["TEXCOORD_0"])
    uv1 = accessor(document, binary, attributes["TEXCOORD_1"])
    uv_errors = {}
    for span in (37, 45):
        expected0 = [((p[0] - 8) / 26, 1 - (p[2] - 10) / span) for p in positions]
        expected1 = [((p[2] - 10) / span, 1 - (p[1] - .7) / 4.4) for p in positions]
        uv_errors[str(span)] = {"uv0_max_error": max_error(uv0, expected0),
                                "uv1_max_error": max_error(uv1, expected1)}
    region = [i for i, p in enumerate(positions) if 8 < p[0] < 34 and 10 < p[2] < 55]
    rock_region = [i for i in region if colors[i][1] > .05]
    report["terrain"] = {
        "sha256": digest(ART / "terrain.glb"),
        "vertices": len(positions), "triangles": document["accessors"][primitive["indices"]]["count"] // 3,
        "material": document["materials"][primitive["material"]].get("name"),
        "uv_errors": uv_errors, "uv45_ok": max(uv_errors["45"].values()) < 2e-5,
        "active_region_vertices": len(region),
        "old_vertex_rock_region_count": len(rock_region),
        "old_vertex_rock_region_height_range": [min(positions[i][1] for i in rock_region), max(positions[i][1] for i in rock_region)],
        "old_vertex_rock_height_outside_atlas": sum(not (.7 <= positions[i][1] <= 5.1) for i in rock_region),
    }

    imports = {}
    for name in ("S23_LandUse", "S23_Rock_Height", "S23_Rock_Albedo", "S23_Path_Albedo"):
        path = ART / (name + ".png")
        header = path.read_bytes()[:33]
        width, height, bits, color_type = struct.unpack_from(">IIBB", header, 16)
        settings = (ART / (name + ".png.import")).read_text(encoding="utf-8")
        parameters = dict(re.findall(r"^([^=\r\n]+)=([^\r\n]+)$", settings, re.M))
        dest = re.search(r'^path(?:\.[^=]+)?="res://([^"]+)"$', settings, re.M)
        imported = ROOT / dest.group(1) if dest else None
        cache_hash = None
        if imported:
            # Both name.ctex and name.s3tc.ctex use the common name.md5 sibling.
            stem = str(imported).removesuffix(".ctex").removesuffix(".s3tc").removesuffix(".bptc")
            md5_file = Path(stem + ".md5")
            if md5_file.exists():
                matched = re.search(r'source_md5="([a-f0-9]+)"', md5_file.read_text())
                cache_hash = matched.group(1) if matched else None
        source_md5 = digest(path, "md5")
        imports[name] = {
            "size": [width, height], "png_bit_depth": bits, "png_color_type": color_type,
            "sha256": digest(path), "source_md5": source_md5,
            "imported_file_exists": bool(imported and imported.exists()),
            "cache_source_md5": cache_hash, "cache_matches_current_png": cache_hash == source_md5,
            "parameters": {key: parameters.get(key) for key in (
                "compress/mode", "compress/normal_map", "mipmaps/generate", "process/fix_alpha_border",
                "process/premult_alpha", "process/hdr_as_srgb", "process/size_limit", "detect_3d/compress_to")},
        }
    report["textures"] = imports
    report["surfaces_metadata"] = json.loads((LOG / "surfaces.json").read_text(encoding="utf-8"))

    cache = json.loads((ART / "shore_relief_height.json").read_text())
    report["height_cache"] = {key: cache.get(key) for key in ("columns", "rows", "step", "d0", "z0")}
    report["height_cache"].update({"count": len(cache["heights"]),
        "finite": all(math.isfinite(value) for value in cache["heights"]),
        "dimensions_match": len(cache["heights"]) == cache["columns"] * cache["rows"]})
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional report output; assets are never changed")
    args = parser.parse_args()
    result = audit()
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
