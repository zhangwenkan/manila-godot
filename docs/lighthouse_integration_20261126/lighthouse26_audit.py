"""Definition-only read-only checks shared by the lighthouse exporter and audit.

No Blender operation runs on import. The final audit writes one JSON report.
Only the new lighthouse is evaluated by the exporter; old objects use raw hashes.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import struct
from pathlib import Path

import numpy as np


COLLECTION = "Reference_Lighthouse"
ASSET = "lighthouse.glb"
TEMP = "L26_EXPORT_TEMP"
REQUIRED_MARKERS = {"L26_Assembly", "L26_LampEmitter"}


def json_value(value):
    """Match JSON snapshots without tuple/list differences in node links."""
    return json.loads(json.dumps(value, ensure_ascii=False))


def export_material_state(material, common):
    """Entry/exit signature also covers glass/render properties outside nodes.

    Historical materials_before.json deliberately retains the original common
    signature; this richer state is used only for this export's live snapshots.
    """
    properties = {}
    for name in ("diffuse_color", "metallic", "roughness", "surface_render_method", "blend_method",
                 "alpha_threshold", "use_transparency_overlap", "use_backface_culling",
                 "use_backface_culling_shadow", "use_backface_culling_lightprobe_volume",
                 "use_screen_refraction", "use_raytrace_refraction", "displacement_method"):
        if not hasattr(material, name):
            continue
        value = getattr(material, name)
        properties[name] = value if isinstance(value, (str, bool, int, float)) else list(value)
    return {"nodes": json_value(common.material_state(material)), "properties": properties}


def common_helpers(root):
    path = Path(root).parent.parent / "docs/pirate_island_20261125/pirate25_export.py"
    spec = importlib.util.spec_from_file_location("lighthouse26_common", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_session(expected_pid, expected_port, expected_source, log_path):
    import bpy
    source, log = Path(expected_source).resolve(), Path(log_path).resolve()
    if bpy.app.background or os.getpid() != expected_pid or Path(bpy.data.filepath).resolve() != source:
        raise RuntimeError("Wrong owned GUI Blender/source")
    if bpy.types.blendermcp_server.port != expected_port or bpy.context.mode != "OBJECT":
        raise RuntimeError("Wrong owned MCP port or object mode")
    session = json.loads((log / "session_start.json").read_text(encoding="utf8"))
    if session["pid"] != expected_pid or session["port"] != expected_port or Path(session["source"]).resolve() != source:
        raise RuntimeError("Current session differs from this round's snapshot")
    return source.parent.parent, source, log


def protection_checks(root, log, common):
    import bpy
    manifest = json.loads((log / "before_manifest.json").read_text(encoding="utf8"))
    files = {row["relative"]: row["sha256"] for row in manifest
             if Path(row["relative"]).suffix.lower() == ".glb" or row.get("preserve") is True}
    if any(Path(relative).name == ASSET for relative in files):
        raise RuntimeError("A newly authored lighthouse must not be in the pre-round assets")
    old_glbs = {relative for relative in files if Path(relative).parent.as_posix() == "assets/reference"
                and Path(relative).suffix.lower() == ".glb"}
    current_glbs = {path.relative_to(root).as_posix() for path in (root / "assets/reference").glob("*.glb") if path.name != ASSET}
    bad_files = [relative for relative, digest in files.items()
                 if not (root / relative).is_file() or common.sha256(root / relative) != digest]
    rows = json.loads((log / "objects_before.json").read_text(encoding="utf8"))
    bad_objects = []
    for row in rows:
        obj = bpy.data.objects.get(row["name"])
        memberships = set(row.get("collections", [row.get("collection")])) - {None}
        if obj is None or not memberships <= {collection.name for collection in obj.users_collection} or common.object_digest(obj) != row["digest"]:
            bad_objects.append(row["name"])
        elif "type" in row and obj.type != row["type"]:
            bad_objects.append(row["name"])
        elif "parent" in row and (obj.parent.name if obj.parent else None) != row["parent"]:
            bad_objects.append(row["name"])
    old_materials = json.loads((log / "materials_before.json").read_text(encoding="utf8"))
    bad_materials = [name for name, state in old_materials.items()
                     if bpy.data.materials.get(name) is None or json_value(common.material_state(bpy.data.materials[name])) != state]
    expected_names = {row["name"] for row in rows}
    current_names = {obj.name for collection in bpy.data.collections
                     if collection.name.startswith("Reference_") and collection.name != COLLECTION and not collection.hide_render
                     for obj in collection.all_objects}
    result = {"old_runtime_glbs": len(old_glbs), "protected_files": len(files), "old_source_objects": len(rows),
              "old_materials": len(old_materials), "runtime_file_set_preserved": old_glbs == current_glbs,
              "old_active_object_set_preserved": expected_names == current_names,
              "unexpected_old_collection_members": sorted(current_names - expected_names),
              "changed_files": bad_files, "changed_objects": bad_objects, "changed_materials": bad_materials}
    result["passed"] = result["runtime_file_set_preserved"] and result["old_active_object_set_preserved"] and not bad_files and not bad_objects and not bad_materials
    return result


def collection_state(collection, common):
    return {obj.name: {"digest": common.object_digest(obj), "type": obj.type,
                       "parent": obj.parent.name if obj.parent else None}
            for obj in collection.all_objects}


def mesh_check(mesh, matrix):
    """Inspect one raw/evaluated new mesh, never an old scene mesh."""
    p = np.empty((len(mesh.vertices), 3), np.float32)
    mesh.vertices.foreach_get("co", p.ravel())
    matrix = np.asarray(matrix, np.float64)
    world = p.astype(np.float64) @ matrix[:3, :3].T + matrix[:3, 3]
    mesh.calc_loop_triangles()
    triangles = np.empty(len(mesh.loop_triangles) * 3, np.int32)
    mesh.loop_triangles.foreach_get("vertices", triangles)
    triangles = triangles.reshape(-1, 3)
    if len(triangles):
        areas2 = np.linalg.norm(np.cross(world[triangles[:, 1]] - world[triangles[:, 0]],
                                        world[triangles[:, 2]] - world[triangles[:, 0]]), axis=1)
        degenerate = int(np.count_nonzero(areas2 <= 1e-12))
    else:
        degenerate = 0
    bad_uv, bad_uv_lengths = [], []
    for layer in mesh.uv_layers:
        values = np.empty(len(layer.data) * 2, np.float32)
        layer.data.foreach_get("uv", values)
        if not np.isfinite(values).all():
            bad_uv.append(layer.name)
        if len(layer.data) != len(mesh.loops):
            bad_uv_lengths.append(layer.name)
    result = {"vertices": len(p), "triangles": len(triangles), "uv_layers": [layer.name for layer in mesh.uv_layers],
              "finite_geometry": bool(np.isfinite(world).all() and np.isfinite(matrix).all()),
              "nonfinite_uv_layers": bad_uv, "wrong_length_uv_layers": bad_uv_lengths,
              "degenerate_triangles": degenerate}
    result["passed"] = result["finite_geometry"] and bool(result["uv_layers"]) and not bad_uv and not bad_uv_lengths and not degenerate and bool(len(triangles))
    return result


def read_glb(path):
    data = Path(path).read_bytes()
    magic, version, total, length, kind = struct.unpack_from("<4sIIII", data)
    if magic != b"glTF" or version != 2 or total != len(data) or kind != 0x4E4F534A:
        raise RuntimeError("Invalid lighthouse GLB")
    return data, json.loads(data[20:20 + length]), 20 + length


def node_world_matrices(document):
    from mathutils import Quaternion
    nodes = document.get("nodes", [])
    parents = {child: index for index, node in enumerate(nodes) for child in node.get("children", [])}
    cache = {}

    def world(index):
        if index in cache:
            return cache[index]
        node = nodes[index]
        if "matrix" in node:
            local = np.asarray(node["matrix"], np.float64).reshape(4, 4).T
        else:
            x, y, z, w = node.get("rotation", [0, 0, 0, 1])
            local = np.eye(4)
            local[:3, :3] = np.asarray(Quaternion((w, x, y, z)).to_matrix()) @ np.diag(node.get("scale", [1, 1, 1]))
            local[:3, 3] = node.get("translation", [0, 0, 0])
        cache[index] = world(parents[index]) @ local if index in parents else local
        return cache[index]

    return {index: world(index) for index in range(len(nodes))}


def glb_checks(path, common, expected_markers):
    data, document, binary_offset = read_glb(path)
    summary = common.glb_summary(path)
    summary["appearance_materials"] = [{"name": material.get("name"),
                                        "alphaMode": material.get("alphaMode", "OPAQUE"),
                                        "alphaCutoff": material.get("alphaCutoff", .5),
                                        "emissiveFactor": material.get("emissiveFactor", [0, 0, 0]),
                                        "emissiveTexture": material.get("emissiveTexture"),
                                        "extensions": material.get("extensions", {})}
                                       for material in document.get("materials", [])]
    binary_length, kind = struct.unpack_from("<II", data, binary_offset)
    if kind != 0x004E4942:
        raise RuntimeError("GLB binary chunk missing")
    binary = data[binary_offset + 8:binary_offset + 8 + binary_length]
    types = {5120: "i1", 5121: "u1", 5122: "<i2", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
    widths = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}

    def accessor(index):
        row = document["accessors"][index]
        if "sparse" in row or "bufferView" not in row:
            raise RuntimeError("Unsupported sparse/accessor-free lighthouse data")
        view = document["bufferViews"][row["bufferView"]]
        dtype, width = np.dtype(types[row["componentType"]]), widths[row["type"]]
        start = view.get("byteOffset", 0) + row.get("byteOffset", 0)
        stride = view.get("byteStride", dtype.itemsize * width)
        return np.ndarray((row["count"], width), dtype=dtype, buffer=binary, offset=start,
                          strides=(stride, dtype.itemsize)).copy()

    invalid = []
    degenerate = 0
    primitives = 0
    for mesh in document.get("meshes", []):
        for primitive in mesh["primitives"]:
            primitives += 1
            attributes = primitive["attributes"]
            p = accessor(attributes["POSITION"]).astype(np.float64)
            if not np.isfinite(p).all() or "TEXCOORD_0" not in attributes:
                invalid.append(mesh.get("name", "unnamed") + ":geometry_or_missing_uv")
            for name, index in attributes.items():
                if name.startswith("TEXCOORD_") and not np.isfinite(accessor(index)).all():
                    invalid.append(mesh.get("name", "unnamed") + ":" + name)
            idx = accessor(primitive["indices"]).ravel() if "indices" in primitive else np.arange(len(p))
            tri = idx.reshape(-1, 3)
            areas2 = np.linalg.norm(np.cross(p[tri[:, 1]] - p[tri[:, 0]], p[tri[:, 2]] - p[tri[:, 0]]), axis=1)
            degenerate += int(np.count_nonzero(areas2 <= 1e-12))
    worlds = node_world_matrices(document)
    nodes = document.get("nodes", [])
    parents = {child: index for index, node in enumerate(nodes) for child in node.get("children", [])}
    assemblies = [index for index, node in enumerate(nodes) if node.get("name") == "L26_Assembly"]

    def has_assembly_ancestor(index):
        visited = set()
        while index in parents and index not in visited:
            visited.add(index)
            index = parents[index]
            if index in assemblies:
                return True
        return False

    unparented_geometry = [node.get("name", str(index)) for index, node in enumerate(nodes)
                          if "mesh" in node and not has_assembly_ancestor(index)]
    emitter_indices = [index for index, node in enumerate(nodes) if node.get("name") == "L26_LampEmitter"]
    assembly_hierarchy = len(assemblies) == 1 and not unparented_geometry and len(emitter_indices) == 1 and has_assembly_ancestor(emitter_indices[0])
    marker_rows = []
    for name, expected in expected_markers.items():
        hits = [index for index, node in enumerate(document.get("nodes", [])) if node.get("name") == name]
        error = float(np.max(np.abs(worlds[hits[0]] - np.asarray(expected)))) if len(hits) == 1 else None
        marker_rows.append({"name": name, "nodes": len(hits), "matrix_max_error": error,
                            "passed": len(hits) == 1 and error < 1e-5 and "mesh" not in document["nodes"][hits[0]]})
    lights = "KHR_lights_punctual" in document.get("extensions", {}) or any("KHR_lights_punctual" in node.get("extensions", {}) for node in document.get("nodes", []))
    result = {"asset": summary, "primitives": primitives, "invalid_geometry_uv": invalid,
              "degenerate_triangles": degenerate, "marker_nodes": marker_rows,
              "assembly_owns_geometry_and_emitter": assembly_hierarchy,
              "geometry_outside_assembly": unparented_geometry,
              "has_lights": lights, "has_cameras": bool(document.get("cameras"))}
    result["passed"] = bool(summary["triangles"]) and not summary["animations"] and not invalid and not degenerate and not lights and not result["has_cameras"] and assembly_hierarchy and all(row["passed"] for row in marker_rows)
    return result


def audit_lighthouse26(expected_pid, expected_port, expected_source, log_path):
    import bpy
    root, source, log = validate_session(expected_pid, expected_port, expected_source, log_path)
    common = common_helpers(root)
    last = json.loads((log / "lighthouse_export_last_completed.json").read_text(encoding="utf8"))
    report = {"read_only": True, "dirty_observed": bool(bpy.data.is_dirty), "visual_accepted": False,
              "protection": protection_checks(root, log, common), "source_sha256": common.sha256(source)}
    collection = bpy.data.collections[COLLECTION]
    report["source_collection_matches_export"] = collection_state(collection, common) == last["source_collection_state"]
    report["source_materials_match_export"] = all(bpy.data.materials.get(name) and export_material_state(bpy.data.materials[name], common) == state
                                                    for name, state in last["source_material_states"].items())
    target = root / "assets/reference" / ASSET
    report["glb"] = glb_checks(target, common, last["expected_markers_gltf"])
    report["runtime_sha_matches_export"] = common.sha256(target) == last["glb"]["asset"]["sha256"]
    report["disk_source_matches_completed_export"] = last.get("status") == "completed" and last.get("source_saved") is True and report["source_sha256"] == last.get("source_sha256")
    report["export_restore_confirmed"] = all(last.get(key) is True for key in (
        "source_objects_restored", "source_materials_restored", "selection_restored", "active_restored", "visibility_restored"))
    report["temporary_collection_absent"] = bpy.data.collections.get(TEMP) is None
    report["save_evidence_note"] = "dirty=false alone is not a save certificate; disk SHA, current raw collection signatures and material state are compared to the completed export."
    report["passed"] = report["protection"]["passed"] and report["glb"]["passed"] and all(report[key] for key in (
        "source_collection_matches_export", "source_materials_match_export", "runtime_sha_matches_export",
        "disk_source_matches_completed_export", "temporary_collection_absent", "export_restore_confirmed"))
    (log / "lighthouse_final_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    print(json.dumps({"passed": report["passed"], "source_sha256": report["source_sha256"],
                      "asset_sha256": report["glb"]["asset"]["sha256"], "old_objects": report["protection"]["old_source_objects"]}))
    return report
