"""Independent stdlib-only audit of the exported lighthouse; never starts Blender/Godot."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import struct


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def multiply(a, b):
    return [[sum(a[row][k] * b[k][column] for k in range(4)) for column in range(4)] for row in range(4)]


def local_matrix(node):
    if "matrix" in node:
        return [[node["matrix"][column * 4 + row] for column in range(4)] for row in range(4)]
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    scale = node.get("scale", [1, 1, 1])
    position = node.get("translation", [0, 0, 0])
    r = [[1 - 2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
         [2*(x*y+z*w), 1 - 2*(x*x+z*z), 2*(y*z-x*w)],
         [2*(x*z-y*w), 2*(y*z+x*w), 1 - 2*(x*x+y*y)]]
    return [[r[i][j] * scale[j] for j in range(3)] + [position[i]] for i in range(3)] + [[0, 0, 0, 1]]


def point(matrix, p):
    return tuple(sum(matrix[row][column]*p[column] for column in range(3)) + matrix[row][3] for row in range(3))


def twice_area(a, b, c):
    u, v = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
    cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
    return math.sqrt(sum(value*value for value in cross))


def audit(root):
    root = Path(root).resolve()
    log = root / "captures/lighthouse_integration_20261126"
    path = root / "assets/reference/lighthouse.glb"
    export = json.loads((log / "lighthouse_export_last_completed.json").read_text(encoding="utf8"))
    placement = json.loads((log / "placement.json").read_text(encoding="utf8"))
    manifest = json.loads((log / "before_manifest.json").read_text(encoding="utf8"))
    data = path.read_bytes()
    magic, version, total, length, kind = struct.unpack_from("<4sIIII", data)
    assert magic == b"glTF" and version == 2 and total == len(data) and kind == 0x4E4F534A
    document = json.loads(data[20:20+length])
    binary_length, binary_kind = struct.unpack_from("<II", data, 20+length)
    assert binary_kind == 0x004E4942 and 28+length+binary_length <= len(data)
    binary = data[28+length:28+length+binary_length]
    formats = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
    widths = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}

    def accessor(index):
        item = document["accessors"][index]
        assert "sparse" not in item and "bufferView" in item
        view = document["bufferViews"][item["bufferView"]]
        assert view.get("buffer", 0) == 0
        fmt = "<" + formats[item["componentType"]] * widths[item["type"]]
        size = struct.calcsize(fmt)
        offset = view.get("byteOffset", 0) + item.get("byteOffset", 0)
        stride = view.get("byteStride", size)
        assert offset >= 0 and stride >= size and offset + max(item["count"]-1, 0)*stride + size <= len(binary)
        return [struct.unpack_from(fmt, binary, offset+i*stride) for i in range(item["count"])]

    nodes = document.get("nodes", [])
    parents = {child: index for index, node in enumerate(nodes) for child in node.get("children", [])}
    worlds = {}

    def world(index, visited=None):
        if index in worlds:
            return worlds[index]
        visited = set() if visited is None else set(visited)
        assert index not in visited
        visited.add(index)
        local = local_matrix(nodes[index])
        worlds[index] = multiply(world(parents[index], visited), local) if index in parents else local
        return worlds[index]

    assemblies = [index for index, node in enumerate(nodes) if node.get("name") == "L26_Assembly"]
    emitters = [index for index, node in enumerate(nodes) if node.get("name") == "L26_LampEmitter"]

    def under_root(index):
        seen = set()
        while index in parents and index not in seen:
            seen.add(index)
            index = parents[index]
            if index in assemblies:
                return True
        return False

    points, errors, primitives, triangles = [], [], 0, 0
    degenerate = 0
    min_area = float("inf")
    mesh_rows = []
    for index, node in enumerate(nodes):
        if "mesh" not in node:
            continue
        if not under_root(index):
            errors.append("mesh_outside_assembly:" + str(index))
        matrix = world(index)
        mesh = document["meshes"][node["mesh"]]
        count = 0
        for primitive in mesh["primitives"]:
            primitives += 1
            assert primitive.get("mode", 4) == 4
            attrs = primitive["attributes"]
            p = accessor(attrs["POSITION"])
            world_points = [point(matrix, q) for q in p]
            if not all(math.isfinite(value) for q in world_points for value in q):
                errors.append("nonfinite_position:" + str(index))
            points.extend(world_points)
            if "TEXCOORD_0" not in attrs:
                errors.append("missing_uv:" + str(index))
            for name, attribute in attrs.items():
                if name.startswith("TEXCOORD_") or name in {"NORMAL", "TANGENT"}:
                    values = accessor(attribute)
                    if len(values) != len(p) or not all(math.isfinite(value) for row in values for value in row):
                        errors.append("invalid_attribute:" + str(index) + ":" + name)
            indices = [row[0] for row in accessor(primitive["indices"])] if "indices" in primitive else list(range(len(p)))
            assert len(indices) % 3 == 0 and min(indices) >= 0 and max(indices) < len(p)
            count += len(indices)//3
            for i in range(0, len(indices), 3):
                area = twice_area(*(world_points[indices[i+j]] for j in range(3)))
                min_area = min(min_area, area)
                degenerate += int(area <= 1e-12)
        triangles += count
        mesh_rows.append({"name": node.get("name"), "triangles": count, "world_matrix": matrix})
    center = placement["center_godot"]
    lo = [min(p[i] for p in points) for i in range(3)]
    hi = [max(p[i] for p in points) for i in range(3)]
    radius = max(math.hypot(p[0]-center[0], p[2]-center[2]) for p in points)
    root_position = [world(assemblies[0])[i][3] for i in range(3)] if len(assemblies) == 1 else None
    emitter_position = [world(emitters[0])[i][3] for i in range(3)] if len(emitters) == 1 else None
    images = []
    for image in document.get("images", []):
        assert "uri" not in image and "bufferView" in image
        view = document["bufferViews"][image["bufferView"]]
        start = view.get("byteOffset", 0)
        payload = binary[start:start+view["byteLength"]]
        assert len(payload) == view["byteLength"] and payload
        images.append({"name": image.get("name"), "mime_type": image.get("mimeType"), "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)})
    materials = document.get("materials", [])
    appearance = [{"name": mat.get("name"), "alphaMode": mat.get("alphaMode", "OPAQUE"),
                   "baseColorFactor": mat.get("pbrMetallicRoughness", {}).get("baseColorFactor", [1, 1, 1, 1]),
                   "emissiveFactor": mat.get("emissiveFactor", [0, 0, 0]), "extensions": mat.get("extensions", {})} for mat in materials]
    by_material = {mat["name"]: mat for mat in appearance}
    glass_names = ("L26_LanternGlass", "L26_LensGlass")
    glass_ok = all(name in by_material and by_material[name]["alphaMode"] == "BLEND" and by_material[name]["baseColorFactor"][3] < 1 for name in glass_names)
    emission_ok = "L26_LampCore" in by_material and max(by_material["L26_LampCore"]["emissiveFactor"]) > 0
    protected = [row for row in manifest if Path(row["relative"]).suffix.lower() == ".glb" or Path(row["relative"]).name == "shore_relief_height.json"]
    changed_files = [row["relative"] for row in protected if sha(root / row["relative"]) != row["sha256"]]
    runtime_glbs = {path.name for path in (root / "assets/reference").glob("*.glb") if path.name != "lighthouse.glb"}
    before_glbs = {Path(row["relative"]).name for row in protected if Path(row["relative"]).suffix.lower() == ".glb"}
    export_asset = export["glb"]["asset"]
    source_sha = sha(root / "source/harbor_shore_control_mcp.blend")
    expected_images = sorted((row["name"], row["sha256"]) for row in export_asset["image_table"])
    actual_images = sorted((row["name"], row["sha256"]) for row in images)
    checks = {
        "completed_export_report": export.get("status") == "completed" and export.get("source_saved") is True,
        "runtime_asset_matches_export": sha(path) == export_asset["sha256"],
        "disk_source_matches_export": source_sha == export.get("source_sha256"),
        "geometry_uv_normal_finite": not errors,
        "triangles_non_degenerate": not degenerate,
        "counts_match_export": len(document["meshes"]) == export_asset["meshes"] and triangles == export_asset["triangles"] and len(materials) == export_asset["materials"] and len(images) == export_asset["embedded_images"],
        "embedded_image_payloads_match_export": actual_images == expected_images,
        "unique_assembly_and_emitter": len(assemblies) == 1 and len(emitters) == 1,
        "root_placement_matches": root_position is not None and max(abs(root_position[i]-center[i]) for i in range(3)) < 1e-5,
        "emitter_placement_matches": emitter_position is not None and max(abs(emitter_position[i]-placement["emitter_godot"][i]) for i in range(3)) < 1e-5,
        "emitter_under_assembly": len(emitters) == 1 and under_root(emitters[0]),
        "glass_and_lamp_materials_present": glass_ok and emission_ok,
        "no_animation_light_camera": not document.get("animations") and not document.get("cameras") and "KHR_lights_punctual" not in document.get("extensions", {}),
        "old_17_glbs_and_height_unchanged": len(before_glbs) == 17 and not changed_files and runtime_glbs == before_glbs,
        "source_export_restored": all(export.get(key) is True for key in ("source_objects_restored", "source_materials_restored", "selection_restored", "active_restored", "visibility_restored")),
    }
    report = {"passed": all(checks.values()), "checks": checks, "source_sha256": source_sha, "asset_sha256": sha(path),
              "mesh_count": len(document["meshes"]), "triangles": triangles, "materials": appearance, "images": images,
              "geometry_errors": errors, "degenerate_triangles": degenerate, "minimum_triangle_twice_area": min_area,
              "root_godot": root_position, "emitter_godot": emitter_position,
              "actual_evaluated_bounds_godot": [lo, hi], "actual_evaluated_dimensions": [hi[i]-lo[i] for i in range(3)],
              "actual_evaluated_horizontal_radius": radius, "raw_source_radius_reported": placement["horizontal_radius"],
              "preflight_radius": 2.5, "radius_limit_note": "The r=2.5 site preflight does not cover the raw-source radius 3.01156 m or the evaluated final-GLB radius 3.00639 m. Actual runtime GLB collision/sweep testing belongs to the separate runtime audit.",
              "old_glbs": len(before_glbs), "changed_protected_files": changed_files, "meshes": mesh_rows,
              "visual_accepted": False, "does_not_verify": ["Live Blender memory independently from its export report", "Runtime collisions or camera occlusion", "Visual quality"]}
    (log / "independent_asset_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    print(json.dumps({key: report[key] for key in ("passed", "checks", "mesh_count", "triangles", "actual_evaluated_bounds_godot", "actual_evaluated_horizontal_radius", "asset_sha256", "source_sha256")}))
    return report


if __name__ == "__main__":
    audit(Path(__file__).resolve().parents[2] / "demo/tropical_harbor_3d")
