"""Definition-only invariants for an already-built island rigid transform.

Call capture_island_local() in the owned Blender BEFORE moving the assembly,
then write its return value once to this round's island_local_before.json.
This module neither creates snapshots nor changes Blender on import.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

COLLECTION = "Reference_PirateIsland"
ASSEMBLY = "P25_Assembly"


def _export_definitions():
    path = Path(__file__).resolve().parents[1] / "pirate_island_20261125/pirate25_export.py"
    spec = importlib.util.spec_from_file_location("pirate25_export_readonly_definitions", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mesh_signature(mesh):
    h = hashlib.sha256()
    counts = {"vertices": len(mesh.vertices), "edges": len(mesh.edges),
              "polygons": len(mesh.polygons), "loops": len(mesh.loops)}
    h.update(json.dumps(counts, sort_keys=True).encode())
    for values, name, width, dtype in (
        (mesh.vertices, "co", 3, np.float32),
        (mesh.edges, "vertices", 2, np.int32),
        (mesh.loops, "vertex_index", 1, np.int32),
        (mesh.polygons, "loop_start", 1, np.int32),
        (mesh.polygons, "loop_total", 1, np.int32),
        (mesh.polygons, "material_index", 1, np.int32),
        (mesh.polygons, "use_smooth", 1, np.bool_),
    ):
        a = np.empty(len(values) * width, dtype)
        values.foreach_get(name, a)
        h.update(name.encode() + a.tobytes())
    uv_names = []
    for uv in mesh.uv_layers:
        uv_names.append(uv.name)
        a = np.empty(len(uv.data) * 2, np.float32)
        uv.data.foreach_get("uv", a)
        h.update(uv.name.encode() + a.tobytes())
    slots = [material.name if material else None for material in mesh.materials]
    h.update(json.dumps(slots).encode())
    return {"sha256": h.hexdigest(), **counts, "uv_layers": uv_names, "material_slots": slots}


def _modifier_signature(obj):
    rows = []
    for modifier in obj.modifiers:
        row = {"name": modifier.name, "type": modifier.type, "properties": {}}
        for prop in modifier.bl_rna.properties:
            key = prop.identifier
            if key in ("rna_type", "name", "type") or prop.is_readonly:
                continue
            value = getattr(modifier, key)
            if prop.type in ("BOOLEAN", "INT", "FLOAT", "STRING", "ENUM"):
                row["properties"][key] = list(value) if getattr(prop, "is_array", False) else sorted(value) if isinstance(value, set) else value
            elif prop.type == "POINTER":
                row["properties"][key] = value.name if value and hasattr(value, "name") else None
        rows.append(row)
    return rows


def capture_island_local():
    """Read current island-local geometry/pose/graph fields; root world pose is separate."""
    import bpy

    definitions = _export_definitions()
    collection = bpy.data.collections[COLLECTION]
    assembly = bpy.data.objects[ASSEMBLY]
    objects = sorted(collection.all_objects, key=lambda obj: obj.name)
    if assembly not in objects:
        raise RuntimeError("Island assembly is not in the island collection")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    rows = []
    for obj in objects:
        row = {"name": obj.name, "type": obj.type,
               "parent": obj.parent.name if obj.parent else None,
               "collections": sorted(c.name for c in obj.users_collection),
               "hide_render": bool(obj.hide_render), "hide_viewport": bool(obj.hide_viewport),
               "hidden": bool(obj.hide_get()), "modifiers": _modifier_signature(obj)}
        if obj != assembly:
            row["matrix_basis"] = [list(v) for v in obj.matrix_basis]
            row["matrix_parent_inverse"] = [list(v) for v in obj.matrix_parent_inverse]
        if obj.type == "MESH":
            row["data_name"] = obj.data.name
            row["raw_mesh"] = _mesh_signature(obj.data)
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
            try:
                row["evaluated_local_mesh"] = _mesh_signature(mesh)
            finally:
                evaluated.to_mesh_clear()
        rows.append(row)
    materials = {material.name: material for obj in objects if obj.type == "MESH"
                 for material in obj.data.materials if material}
    invariant = {"schema": 1, "collection": COLLECTION, "assembly": ASSEMBLY,
                 "components": len([o for o in objects if o.type == "MESH"]),
                 "objects": rows,
                 "materials": {name: definitions.material_state(mat) for name, mat in sorted(materials.items())},
                 "collection_flags": {c.name: {"hide_render": bool(c.hide_render), "hide_viewport": bool(c.hide_viewport)}
                                      for c in [collection, *collection.children_recursive]}}
    snapshot = {"invariant": invariant, "assembly_world": [list(v) for v in assembly.matrix_world],
                "limitations": ["World transform of P25_Assembly is intentionally excluded from invariant equality.",
                                "Material signature covers node sockets, image references/packed bytes, and links; it is not every RNA node property."]}
    # Match the immutable JSON snapshot's types, including material link tuples.
    return json.loads(json.dumps(snapshot, ensure_ascii=False))


def check_island_local(log_path):
    before_path = Path(log_path) / "island_local_before.json"
    before = json.loads(before_path.read_text(encoding="utf8"))
    after = capture_island_local()
    old = before["invariant"]
    new = after["invariant"]
    evaluated_hash_changes = []
    old_eval = {row["name"]: row.get("evaluated_local_mesh", {}).get("sha256") for row in old["objects"]}
    for row in new["objects"]:
        if row.get("evaluated_local_mesh", {}).get("sha256") != old_eval.get(row["name"]):
            evaluated_hash_changes.append(row["name"])
    # Blender's evaluated bevel output may differ at the byte level even in
    # consecutive reads without edits. Preserve exact raw mesh + modifiers,
    # UV/material/topology counts and layer names; report evaluated hashes as
    # observations, not as evidence that this round changed the authored mesh.
    for invariant in (old, new):
        for row in invariant["objects"]:
            if "evaluated_local_mesh" in row:
                row["evaluated_local_mesh"].pop("sha256", None)
    old_rows = {row["name"]: row for row in old["objects"]}
    new_rows = {row["name"]: row for row in new["objects"]}
    changed = [name for name in sorted(set(old_rows) | set(new_rows)) if old_rows.get(name) != new_rows.get(name)]
    old_mats, new_mats = old["materials"], new["materials"]
    changed_mats = [name for name in sorted(set(old_mats) | set(new_mats)) if old_mats.get(name) != new_mats.get(name)]
    transform = np.asarray(after["assembly_world"], np.float64) @ np.linalg.inv(np.asarray(before["assembly_world"], np.float64))
    rotation = transform[:3, :3]
    rigid_error = float(np.max(np.abs(rotation.T @ rotation - np.eye(3))))
    yaw_error = float(np.max(np.abs(rotation @ np.asarray([0., 0., 1.]) - [0., 0., 1.])))
    rigid = (rigid_error <= 1e-5 and abs(float(np.linalg.det(rotation)) - 1.) <= 1e-5
             and yaw_error <= 1e-5 and abs(float(transform[2, 3])) <= 1e-5
             and float(np.max(np.abs(transform[3] - [0., 0., 0., 1.]))) <= 1e-5)
    repeats = [_evaluated_repeat_metrics(name) for name in evaluated_hash_changes if name in new_rows]
    repeat_okay = all(row["pass"] for row in repeats)
    return {"passed": old == new and rigid and repeat_okay, "components": new["components"], "objects": len(new_rows),
            "changed_local_objects": changed, "changed_material_signatures": changed_mats,
            "collection_flags_preserved": old["collection_flags"] == new["collection_flags"],
            "root_transform_is_horizontal_rigid_motion": rigid,
            "root_rotation_orthogonality_error": rigid_error, "root_vertical_axis_error": yaw_error,
            "root_delta_blender_matrix": transform.tolist(),
            "evaluated_hash_changes_observed": evaluated_hash_changes,
            "evaluated_hash_is_historical_shape_proof": False,
            "evaluated_repeat_position_checks": repeats,
            "before_assembly_world": before["assembly_world"], "after_assembly_world": after["assembly_world"],
            "limitations": after["limitations"]}


def _evaluated_repeat_metrics(name):
    """Compare two current evaluations numerically; never rewrite the baseline."""
    import bpy

    obj = bpy.data.objects[name]
    graph = bpy.context.evaluated_depsgraph_get()
    arrays = []
    counts = []
    for _ in range(2):
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=graph)
        try:
            positions = np.empty(len(mesh.vertices) * 3, np.float32)
            mesh.vertices.foreach_get("co", positions)
            arrays.append(positions.reshape(-1, 3))
            counts.append([len(mesh.vertices), len(mesh.edges), len(mesh.loops), len(mesh.polygons)])
        finally:
            evaluated.to_mesh_clear()
    same_counts = counts[0] == counts[1]
    finite = all(np.isfinite(a).all() for a in arrays)
    delta = float(np.max(np.abs(arrays[0] - arrays[1]))) if same_counts and len(arrays[0]) else None
    bounds = [[a.min(axis=0).tolist(), a.max(axis=0).tolist()] if len(a) else None for a in arrays]
    return {"object": name, "pass": same_counts and finite and delta is not None and delta <= 2e-5,
            "counts_equal": same_counts, "finite": bool(finite), "maximum_local_position_delta": delta,
            "position_tolerance": 2e-5, "current_evaluated_bounds": bounds,
            "scope": "two consecutive current reads, not a historical evaluated-position comparison"}


def island_snapshot_names(log_path):
    data = json.loads((Path(log_path) / "island_local_before.json").read_text(encoding="utf8"))
    return {row["name"] for row in data["invariant"]["objects"]}
