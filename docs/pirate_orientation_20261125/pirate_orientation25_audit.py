"""Definition-only source audit for the already-built, rigidly moved P25 island.

Run only inside the owned GUI Blender MCP. The build.json contract contains
terrain_objects, skirt_indices, skirt_bottom and supports. Each support's
bottom_local is in P25_Assembly space (not the prop's object space).
Requires this round's actual island_local_before.json. Root pose is checked
against an explicit expected matrix; all island-local data must remain equal.
This audit does not claim boat sweeps: the independent runtime owns those checks.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from datetime import datetime
from pathlib import Path

import numpy as np


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _digest(obj):
    h = hashlib.sha256(np.asarray(obj.matrix_world, np.float64).tobytes())
    if obj.type == "MESH":
        a = np.empty(len(obj.data.vertices) * 3, np.float32)
        obj.data.vertices.foreach_get("co", a)
        h.update(a.tobytes())
        a = np.empty(len(obj.data.loops), np.int32)
        obj.data.loops.foreach_get("vertex_index", a)
        h.update(a.tobytes())
        for uv in obj.data.uv_layers:
            a = np.empty(len(uv.data) * 2, np.float32)
            uv.data.foreach_get("uv", a)
            h.update(a.tobytes())
        h.update("|".join(m.name if m else "" for m in obj.data.materials).encode())
    return h.hexdigest()


def _invariants_module():
    path = Path(__file__).resolve().with_name("pirate_orientation25_invariants.py")
    spec = importlib.util.spec_from_file_location("pirate_orientation25_invariants", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit_pirate_orientation25(expected_pid, expected_port, expected_source, log_path,
                               expected_assembly_world, contract_path, maximum_world_x=-10.5):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    source = Path(expected_source).resolve()
    root = source.parent.parent
    log = Path(log_path).resolve()
    contract_path = Path(contract_path).resolve() if contract_path else log / "build.json"
    if bpy.app.background or os.getpid() != expected_pid or Path(bpy.data.filepath).resolve() != source:
        raise RuntimeError("Wrong independently owned GUI Blender/source")
    if bpy.types.blendermcp_server.port != expected_port:
        raise RuntimeError("Wrong owned MCP port")
    session = json.loads((log / "session_start.json").read_text(encoding="utf8"))
    if session["pid"] != expected_pid or session["port"] != expected_port or Path(session["source"]).resolve() != source:
        raise RuntimeError("This round's source/session snapshot does not match")
    contract = json.loads(contract_path.read_text(encoding="utf8"))
    before = json.loads((log / "objects_before.json").read_text(encoding="utf8"))
    invariants = _invariants_module()
    island_names = invariants.island_snapshot_names(log)
    expected_pose = np.asarray(expected_assembly_world, np.float64)
    if expected_pose.shape != (4, 4) or not np.isfinite(expected_pose).all():
        raise RuntimeError("A concrete finite expected assembly matrix is required")
    manifest = json.loads((log / "before_manifest.json").read_text(encoding="utf8"))
    collection = bpy.data.collections["Reference_PirateIsland"]
    assembly = bpy.data.objects["P25_Assembly"]
    objects = [o for o in collection.all_objects if o.type == "MESH"]
    names = {o.name for o in objects}
    dirty_before = bool(bpy.data.is_dirty)
    source_hash = _sha(source)
    report = {"created_local": datetime.now().astimezone().isoformat(), "read_only": True,
              "source": str(source), "source_sha256": source_hash, "source_dirty_before": dirty_before,
              "pid": os.getpid(), "port": expected_port, "checks": [], "visual_accepted": False,
              "contract": str(contract_path), "contract_sha256": _sha(contract_path),
              "limitations": ["Support checks cover the authored root-space foot anchors in build.json, not every surface or every prop.",
                              "Maximum world X is an island envelope check; the independent runtime audit owns swept route checks.",
                              "Historical object digests cover raw mesh, pose, UV and material slots. Historical material checks cover only the recorded names, image references and base color."]}

    def check(label, okay, **details):
        report["checks"].append({"name": label, "pass": bool(okay), **details})

    check("existing_island_collection_visible_and_prefixed", bool(objects) and not collection.hide_render
          and not collection.hide_viewport and all(name.startswith("P25_") for name in names), mesh_objects=len(objects))
    check("all_island_meshes_parented_to_assembly", all(obj.parent == assembly for obj in objects))
    local = invariants.check_island_local(log)
    check("existing_island_local_geometry_uv_materials_and_components_preserved", local["passed"], **{k: v for k, v in local.items() if k != "passed"})
    pose_error = float(np.max(np.abs(np.asarray(assembly.matrix_world, np.float64) - expected_pose)))
    check("island_assembly_matches_expected_rigid_pose", pose_error <= 1e-5,
          expected_assembly_world=expected_pose.tolist(), maximum_matrix_error=pose_error)
    old_failures = []
    protected_rows = [row for row in before if row["name"] not in island_names]
    for row in protected_rows:
        obj = bpy.data.objects.get(row["name"])
        memberships = set(row.get("collections", [row.get("collection")])) - {None}
        if obj is None or _digest(obj) != row["digest"] or not memberships <= {c.name for c in obj.users_collection}:
            old_failures.append(row["name"])
    check("all_non_island_source_objects_preserved", not old_failures, checked=len(protected_rows), failures=old_failures)
    old_names = {row["name"] for row in before}
    expected_mesh_names = island_names - {"P25_Assembly"}
    check("island_retains_existing_component_set", names == expected_mesh_names,
          missing=sorted(expected_mesh_names - names), unexpected=sorted(names - expected_mesh_names))
    old_glbs = [row for row in manifest if Path(row["relative"]).suffix.lower() == ".glb"
                and Path(row["relative"]).name != "pirate_island.glb"]
    file_failures = [row["relative"] for row in old_glbs
                     if not (root / row["relative"]).is_file() or _sha(root / row["relative"]) != row["sha256"]]
    current_glbs = {p.relative_to(root).as_posix() for p in (root / "assets/reference").glob("*.glb")
                    if p.name != "pirate_island.glb"}
    expected_glbs = {row["relative"] for row in old_glbs}
    check("all_original_runtime_glbs_preserved", bool(old_glbs) and not file_failures and current_glbs == expected_glbs,
          checked=len(old_glbs), failures=file_failures, unexpected_files=sorted(current_glbs - expected_glbs))
    fresh_external = [obj.name for col in bpy.data.collections if col.name.startswith("Reference_")
                      and col != collection and not col.hide_render for obj in col.objects
                      if obj.type == "MESH" and obj.name not in old_names and obj.name not in names]
    check("all_new_runtime_geometry_belongs_to_island", not fresh_external, outside_island=fresh_external)
    material_failures = []
    materials_before = json.loads((log / "materials_before.json").read_text(encoding="utf8"))
    for row in materials_before:
        material = bpy.data.materials.get(row["name"])
        if material is None:
            material_failures.append(row["name"])
            continue
        p = next((n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if material.use_nodes else None
        actual = {"name": material.name,
                  "images": [n.image.name for n in material.node_tree.nodes if n.type == "TEX_IMAGE" and n.image] if material.use_nodes else [],
                  "color": list(p.inputs["Base Color"].default_value) if p else None}
        if actual != row:
            material_failures.append(row["name"])
    check("recorded_original_material_fields_preserved", not material_failures,
          checked=len(materials_before), failures=material_failures)

    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated_cache = {}
    bvh_cache = {}

    def evaluated_geometry(name):
        if name not in evaluated_cache:
            obj = bpy.data.objects[name]
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            try:
                mesh.calc_loop_triangles()
                world = np.asarray([tuple(evaluated.matrix_world @ vertex.co) for vertex in mesh.vertices], np.float64).reshape(-1, 3)
                triangles = np.asarray([tuple(face.vertices) for face in mesh.loop_triangles], np.int32).reshape(-1, 3)
            finally:
                evaluated.to_mesh_clear()
            evaluated_cache[name] = world, triangles
        return evaluated_cache[name]

    def support_bvh(name):
        if name not in bvh_cache:
            world, triangles = evaluated_geometry(name)
            bvh_cache[name] = BVHTree.FromPolygons(world.tolist(), triangles.tolist(), all_triangles=True)
        return bvh_cache[name]

    all_bounds = []
    invalid_geometry = []
    total_vertices, total_triangles = 0, 0
    for obj in objects:
        world, triangles = evaluated_geometry(obj.name)
        valid = (len(world) > 0 and len(triangles) > 0 and np.all(np.isfinite(world))
                 and triangles.min() >= 0 and triangles.max() < len(world))
        if not valid:
            invalid_geometry.append(obj.name)
            continue
        total_vertices += len(world)
        total_triangles += len(triangles)
        all_bounds.append([world.min(0), world.max(0)])
    check("island_has_finite_nonempty_topology", bool(objects) and not invalid_geometry,
          vertices=total_vertices, triangles=total_triangles, failures=invalid_geometry)
    actual_bounds = [np.min(np.asarray(all_bounds)[:, 0], axis=0), np.max(np.asarray(all_bounds)[:, 1], axis=0)] if all_bounds else None
    check("island_world_x_stays_outside_navigation_corridor", actual_bounds is not None and actual_bounds[1][0] <= maximum_world_x + 1e-5,
          actual_bounds=actual_bounds, maximum_allowed_world_x=maximum_world_x,
          envelope_margin=float(maximum_world_x - actual_bounds[1][0]) if actual_bounds is not None else None)

    terrain_names = contract.get("terrain_objects", [])
    check("terrain_body_contract_is_explicit", bool(terrain_names) and "P25_IslandSandBody" in terrain_names)
    for name in terrain_names:
        if name not in names:
            check("terrain_exists_" + name, False)
            continue
        world, triangles = evaluated_geometry(name)
        edges = np.sort(np.concatenate((triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]])), axis=1)
        _, counts = np.unique(edges, axis=0, return_counts=True)
        boundary = int(np.count_nonzero(counts == 1))
        nonmanifold = int(np.count_nonzero(counts > 2))
        cross = np.cross(world[triangles[:, 1]] - world[triangles[:, 0]], world[triangles[:, 2]] - world[triangles[:, 0]])
        degenerate = int(np.count_nonzero(np.linalg.norm(cross, axis=1) < 1e-10))
        check("terrain_closed_and_non_degenerate_" + name, not boundary and not nonmanifold and not degenerate,
              boundary_edges=boundary, nonmanifold_edges=nonmanifold, degenerate_triangles=degenerate)

    body = bpy.data.objects.get("P25_IslandSandBody")
    skirt_indices = contract.get("skirt_indices", [])
    bottom = float(contract.get("skirt_bottom", 0))
    valid_skirt = body is not None and bool(skirt_indices) and min(skirt_indices) >= 0 and max(skirt_indices) < len(body.data.vertices)
    skirt_z = [(body.matrix_world @ body.data.vertices[i].co).z for i in skirt_indices] if valid_skirt else []
    expected_z = (assembly.matrix_world @ Vector((0, 0, bottom))).z
    check("main_sand_body_has_underwater_bottom", valid_skirt and bottom < -.5
          and max(skirt_z) <= -.5 and max(abs(z - expected_z) for z in skirt_z) < 1e-5,
          samples=len(skirt_z), lowest_world_z=min(skirt_z) if skirt_z else None,
          highest_world_z=max(skirt_z) if skirt_z else None, authored_bottom=bottom)

    terrain_group = [obj.name for obj in objects if obj.name in ("P25_IslandSandBody", "P25_ForestEarthBank")
                     or obj.name.startswith("P25_RidgeMass")]
    supports = contract.get("supports", [])
    check("support_contract_is_explicit", bool(supports), anchors=len(supports), terrain_group=terrain_group)
    support_rows = []
    for spec in supports:
        name = spec["object"]
        point = spec.get("bottom_local", [])
        support_names = terrain_group if spec.get("support") == "terrain_group" else [spec.get("support")]
        valid = name in names and len(point) == 3 and bool(support_names) and all(n in names for n in support_names)
        world = assembly.matrix_world @ Vector(point) if valid else None
        candidates = []
        if valid:
            for support_name in support_names:
                vertices, _ = evaluated_geometry(support_name)
                cast_z = max(float(vertices[:, 2].max()) + 2, float(world.z) + 2)
                hit = support_bvh(support_name).ray_cast(Vector((world.x, world.y, cast_z)), Vector((0, 0, -1)), 200)[0]
                if hit is not None:
                    candidates.append((float(hit.z), support_name))
        surface, support_name = max(candidates) if candidates else (None, None)
        gap = float(world.z - surface) if surface is not None else None
        low, high = float(spec.get("minimum_gap", -.22)), float(spec.get("maximum_gap", .04))
        row = {"object": name, "anchor_assembly_local": point, "anchor_world": list(world) if world is not None else None,
               "hit_support": support_name, "gap": gap, "allowed_gap": [low, high]}
        support_rows.append(row)
        check("authored_support_anchor_" + name, valid and gap is not None and low <= gap <= high, **row)
    report["support_results"] = support_rows
    report["runtime_route_checks"] = {"owned_by": "independent Godot runtime audit",
                                      "executed_by_this_script": False}
    check("read_only_audit_did_not_change_source", bool(bpy.data.is_dirty) == dirty_before and _sha(source) == source_hash)
    report["passed"] = all(row["pass"] for row in report["checks"])
    report["failed_checks"] = [row["name"] for row in report["checks"] if not row["pass"]]
    report["source_dirty_after"] = bool(bpy.data.is_dirty)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = log / ("pirate_audit_" + stamp + ".json")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                              default=lambda value: value.item() if isinstance(value, np.generic) else value.tolist() if isinstance(value, np.ndarray) else str(value)), encoding="utf8")
    print(json.dumps({"report": str(path), "passed": report["passed"], "checks": len(report["checks"]),
                      "failed_checks": report["failed_checks"]}, ensure_ascii=False))
    return report
