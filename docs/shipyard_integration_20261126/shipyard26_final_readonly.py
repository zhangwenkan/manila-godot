"""Definition-only, read-only final source check for the November 26 shipyard.

The explicit audit call writes only final_source_audit.json. It never loads,
changes, saves or closes a Blender source, and never runs the export function.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path

import numpy as np


def audit_shipyard26(expected_pid, expected_port, expected_source, log_path):
    import bpy

    source = Path(expected_source).resolve()
    root = source.parent.parent
    log = Path(log_path).resolve()
    if bpy.app.background or os.getpid() != expected_pid or Path(bpy.data.filepath).resolve() != source:
        raise RuntimeError("Wrong owned GUI Blender/source")
    if bpy.types.blendermcp_server.port != expected_port or bpy.context.mode != "OBJECT":
        raise RuntimeError("Wrong owned MCP port/object mode")
    session = json.loads((log / "session_start.json").read_text(encoding="utf8"))
    if session["pid"] != expected_pid or session["port"] != expected_port or Path(session["source"]).resolve() != source:
        raise RuntimeError("Current round session does not match")
    path = root.parent.parent / "docs/pirate_island_20261125/pirate25_export.py"
    spec = importlib.util.spec_from_file_location("shipyard26_readonly_common", path)
    common = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(common)
    before = json.loads((log / "objects_before.json").read_text(encoding="utf8"))
    known = {row["name"]: row for row in before}
    mutation = json.loads((log / "mutation.json").read_text(encoding="utf8"))
    allowed = set(mutation["allowed_changed_names"])
    last = json.loads((log / "shipyard_export_last_completed.json").read_text(encoding="utf8"))
    report = {"pid": os.getpid(), "port": expected_port, "source": str(source),
              "read_only": True, "source_save_called": False,
              "dirty_observed": bool(bpy.data.is_dirty), "visual_accepted": False,
              "checks": {}, "limitations": [
                  "dirty=false is observational and is not proof that direct data edits were saved.",
                  "Historical floor world-coordinate arrays were not captured; exact raw coordinates and matrix_world are covered by the baseline object digest.",
                  "Object digests cover raw coordinates, loop indices, UVs, matrix_world and material-slot names, not every possible Blender datablock property."]}
    checks = report["checks"]
    missing, digest_changed, membership_changed = [], [], []
    current_digests = {}
    for row in before:
        obj = bpy.data.objects.get(row["name"])
        if obj is None:
            missing.append(row["name"])
            continue
        current_digests[obj.name] = common.object_digest(obj)
        if current_digests[obj.name] != row["digest"]:
            digest_changed.append(obj.name)
        membership = set(row.get("collections", [row.get("collection")])) - {None}
        if not membership <= {collection.name for collection in obj.users_collection}:
            membership_changed.append(obj.name)
    changed = set(missing) | set(digest_changed) | set(membership_changed)
    report["old_mesh_changes"] = {
        "baseline_objects": len(before), "actual_changed_count": len(changed),
        "actual_changed_names": sorted(changed), "digest_changed_count": len(digest_changed),
        "digest_changed_names": sorted(digest_changed), "membership_changed_count": len(membership_changed),
        "membership_changed_names": sorted(membership_changed), "missing_names": sorted(missing),
        "allowed_count": len(allowed), "undeclared_changes": sorted(changed - allowed),
        "allowed_but_unchanged": sorted(allowed - changed), "unchanged_count": len(before) - len(changed)}
    checks["old_changes_declared"] = not (changed - allowed) and allowed <= set(known)
    checks["old_meshes_not_deleted"] = not missing

    pier_names = set(json.loads((log / "old_small_pier_121_names.json").read_text(encoding="utf8")))
    archive = bpy.data.collections.get("Archive_Y26_ReplacedSmallPier")
    archived_names = {obj.name for obj in archive.all_objects} if archive else set()
    report["replaced_small_pier"] = {"expected_count": len(pier_names), "archived_count": len(archived_names),
                                      "missing_names": sorted(pier_names - archived_names),
                                      "unexpected_names": sorted(archived_names - pier_names),
                                      "geometry_pose_unchanged": all(current_digests.get(name) == known[name]["digest"] for name in pier_names),
                                      "hidden_render": bool(archive and archive.hide_render),
                                      "hidden_viewport": bool(archive and archive.hide_viewport)}
    checks["complete_pier_archived"] = bool(archive) and archived_names == pier_names and report["replaced_small_pier"]["geometry_pose_unchanged"] and archive.hide_render and archive.hide_viewport

    terrain = bpy.data.objects["C25_ContourBuiltCoast"]
    mesh = terrain.data
    p = np.empty((len(mesh.vertices), 3), np.float32)
    mesh.vertices.foreach_get("co", p.ravel())
    polygon_sizes = np.empty(len(mesh.polygons), np.int32)
    mesh.polygons.foreach_get("loop_total", polygon_sizes)
    checks["terrain_explicit_triangles"] = bool(np.all(polygon_sizes == 3))
    checks["terrain_finite_identity"] = bool(np.isfinite(p).all() and np.array_equal(np.asarray(terrain.matrix_world), np.eye(4)))
    if checks["terrain_explicit_triangles"]:
        loops = np.empty(len(mesh.loops), np.int32)
        mesh.loops.foreach_get("vertex_index", loops)
        tri = loops.reshape(-1, 3)
        with np.load(log / "terrain_before.npz") as baseline:
            bp = baseline["positions"].astype(np.float32)
            bt = baseline["triangles"].astype(np.int32)
        same_shape = p.shape == bp.shape
        same_topology = np.array_equal(tri, bt)

        def edges(triangles):
            all_edges = np.sort(np.concatenate((triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]])), axis=1)
            unique, counts = np.unique(all_edges, axis=0, return_counts=True)
            return {tuple(map(int, edge)) for edge in unique[counts == 1]}, int(np.count_nonzero(counts > 2))

        old_boundary, old_nonmanifold = edges(bt)
        new_boundary, new_nonmanifold = edges(tri)
        shared = min(len(bp), len(p))
        delta = p[:shared].astype(np.float64) - bp[:shared].astype(np.float64)
        changed_exact = np.flatnonzero(np.any(delta != 0, axis=1))
        changed_threshold = np.flatnonzero(np.max(np.abs(delta), axis=1) > 1e-6)
        boundary_vertices = sorted({index for edge in old_boundary for index in edge})
        boundary_changed = [index for index in boundary_vertices if index >= len(p) or np.any(p[index] != bp[index])]
        cross = np.cross(p[tri[:, 1]].astype(float) - p[tri[:, 0]], p[tri[:, 2]].astype(float) - p[tri[:, 0]])
        old_cross = np.cross(bp[bt[:, 1]].astype(float) - bp[bt[:, 0]], bp[bt[:, 2]].astype(float) - bp[bt[:, 0]])
        bad = np.linalg.norm(cross, axis=1) < 1e-10
        old_bad = np.linalg.norm(old_cross, axis=1) < 1e-10
        downward = cross[:, 2] < -1e-10
        old_downward = old_cross[:, 2] < -1e-10
        report["terrain"] = {
            "before_vertices": len(bp), "vertices": len(p), "before_triangles": len(bt), "triangles": len(tri),
            "same_topology": same_topology, "same_xy": bool(same_shape and np.array_equal(p[:, :2], bp[:, :2])),
            "changed_original_vertices_exact": len(changed_exact), "changed_original_vertices_over_1e_6": len(changed_threshold),
            "height_delta_min": float(delta[:, 2].min()), "height_delta_max": float(delta[:, 2].max()),
            "before_boundary_edges": len(old_boundary), "boundary_edges": len(new_boundary),
            "added_boundary_edges": sorted(new_boundary - old_boundary), "removed_boundary_edges": sorted(old_boundary - new_boundary),
            "changed_boundary_vertex_indices": boundary_changed,
            "before_nonmanifold_edges": old_nonmanifold, "nonmanifold_edges": new_nonmanifold,
            "degenerate_triangles": int(bad.sum()), "before_degenerate_triangles": int(old_bad.sum()),
            "new_degenerate_triangles": int(np.count_nonzero(bad & ~old_bad)) if same_topology else None,
            "downward_triangles": int(downward.sum()),
            "new_downward_triangles": int(np.count_nonzero(downward & ~old_downward)) if same_topology else None,
            "raw_geometry_sha256": hashlib.sha256(p.tobytes() + tri.tobytes()).hexdigest()}
        checks["terrain_topology_xy_preserved"] = same_shape and same_topology and report["terrain"]["same_xy"]
        checks["terrain_boundary_preserved"] = old_boundary == new_boundary and not boundary_changed
        checks["terrain_no_new_bad_faces"] = same_topology and not report["terrain"]["new_degenerate_triangles"] and not report["terrain"]["new_downward_triangles"] and new_nonmanifold <= old_nonmanifold

    floor_names = sorted(name for name, row in known.items() if row.get("collection") == "Reference_Town" and name.startswith("Town_Floor"))
    floor_names.append("Hut_Floor.013")
    floors = []
    for name in floor_names:
        obj = bpy.data.objects.get(name)
        unchanged = name in known and current_digests.get(name) == known[name]["digest"]
        row = {"name": name, "baseline_raw_vertices_and_matrix_digest_match": unchanged,
               "raw_world_coordinates_unchanged_by_digest": unchanged}
        if obj is not None:
            points = np.asarray([list(obj.matrix_world @ vertex.co) for vertex in obj.data.vertices], np.float32)
            row.update(current_world_vertices=len(points), current_world_finite=bool(np.isfinite(points).all()),
                       current_world_coords_sha256=hashlib.sha256(points.tobytes()).hexdigest())
        floors.append(row)
    report["fixed_floors"] = floors
    checks["nine_town_and_hut013_raw_world_geometry_preserved"] = len(floor_names) == 10 and all(row["raw_world_coordinates_unchanged_by_digest"] and row.get("current_world_finite") for row in floors)

    active_objects = {obj.name: obj for collection in bpy.data.collections
                      if collection.name.startswith("Reference_") and not collection.hide_render
                      for obj in collection.all_objects if obj.type in {"MESH", "CURVE", "FONT"}}
    materials = {mat.name: mat for obj in active_objects.values() for mat in obj.data.materials if mat}
    images = {}

    def tree_images(tree, seen):
        if tree is None or tree.as_pointer() in seen:
            return
        seen.add(tree.as_pointer())
        for node in tree.nodes:
            if node.type == "TEX_IMAGE" and node.image is not None:
                images[node.image.name] = node.image
            if node.type == "GROUP":
                tree_images(node.node_tree, seen)

    for mat in materials.values():
        if mat.use_nodes:
            tree_images(mat.node_tree, set())
    image_rows = []
    for name, image in sorted(images.items()):
        packed = bytes(image.packed_file.data) if image.packed_file else None
        image_path = Path(bpy.path.abspath(image.filepath)) if image.filepath else None
        image_rows.append({"name": name, "size": list(image.size), "packed_bytes": len(packed) if packed else 0,
                           "packed_sha256": hashlib.sha256(packed).hexdigest() if packed else None,
                           "external_exists": bool(image_path and image_path.is_file()),
                           "available": bool((packed or (image_path and image_path.is_file())) and min(image.size) > 0)})
    report["used_images"] = image_rows
    checks["all_used_images_available"] = all(row["available"] for row in image_rows)
    report["used_image_count"] = len(image_rows)
    report["used_packed_image_count"] = sum(row["packed_bytes"] > 0 for row in image_rows)

    yard = bpy.data.collections["Reference_Shipyard"]
    members = list(yard.all_objects)
    yard_meshes = [obj for obj in members if obj.type == "MESH"]
    by_material = {}
    bad_geometry, bad_uv, missing_uv = [], [], []
    for obj in yard_meshes:
        coords = np.empty((len(obj.data.vertices), 3), np.float32)
        obj.data.vertices.foreach_get("co", coords.ravel())
        if not np.isfinite(coords).all() or not np.isfinite(np.asarray(obj.matrix_world)).all() or not np.isfinite(np.asarray(obj.dimensions)).all():
            bad_geometry.append(obj.name)
        uv_names = []
        for uv in obj.data.uv_layers:
            values = np.empty(len(uv.data) * 2, np.float32)
            uv.data.foreach_get("uv", values)
            uv_names.append(uv.name)
            if not np.isfinite(values).all():
                bad_uv.append(obj.name + ":" + uv.name)
        for mat in obj.data.materials:
            if mat is None:
                continue
            row = by_material.setdefault(mat.name, {"objects": 0, "uv_layers": set(), "objects_without_uv": []})
            row["objects"] += 1
            row["uv_layers"].update(uv_names)
            if not uv_names:
                row["objects_without_uv"].append(obj.name)
                if mat.use_nodes and any(node.type == "TEX_IMAGE" and node.image is not None for node in mat.node_tree.nodes):
                    missing_uv.append(obj.name + ":" + mat.name)
    for row in by_material.values():
        row["uv_layers"] = sorted(row["uv_layers"])
    report["shipyard"] = {"active_components": len(members), "active_meshes": len(yard_meshes),
                           "new_active_components_vs_baseline": len([obj for obj in members if obj.name not in known]),
                           "new_active_meshes_vs_baseline": len([obj for obj in yard_meshes if obj.name not in known]),
                           "nonmesh_components": [obj.name for obj in members if obj.type != "MESH"],
                           "materials": by_material, "nonfinite_geometry_or_dimensions": bad_geometry,
                           "nonfinite_uv_layers": bad_uv, "textured_objects_without_uv": missing_uv,
                           "obsolete_bank_present": any(obj.name.startswith("M14 continuous sculpted shore bank") for obj in members)}
    checks["shipyard_raw_geometry_uv_finite"] = not bad_geometry and not bad_uv
    checks["shipyard_textured_meshes_have_uv"] = not missing_uv
    checks["shipyard_old_bank_excluded"] = not report["shipyard"]["obsolete_bank_present"]

    collection_mismatches = []
    for cname, expected_digest in last.get("collection_source_hashes", {}).items():
        collection = bpy.data.collections.get(cname)
        digest = hashlib.sha256()
        if collection:
            for obj in sorted(collection.all_objects, key=lambda item: item.name):
                digest.update(obj.name.encode())
                digest.update(common.object_digest(obj).encode())
        if collection is None or digest.hexdigest() != expected_digest:
            collection_mismatches.append(cname)
    expected_images = {image["name"]: image["packed_sha256"] for mat in last.get("source_material_table", []) for image in mat["images"]}
    current_images = {row["name"]: row["packed_sha256"] for row in image_rows}
    changed_export_images = [name for name, digest in expected_images.items() if current_images.get(name) != digest]
    disk_sha = common.sha256(source)
    report["saved_export_consistency"] = {
        "last_export_status": last.get("status"), "last_export_source_sha256": last.get("source_sha256"),
        "disk_source_sha256": disk_sha, "disk_source_sha_matches_export": disk_sha == last.get("source_sha256"),
        "collection_source_digest_mismatches": collection_mismatches,
        "recorded_packed_image_mismatches": changed_export_images,
        "evidence": "Disk SHA is compared with the latest completed export; current collection digests and recorded packed images are compared separately. dirty is not used as a save certificate."}
    checks["latest_completed_export_source_consistent"] = last.get("status") == "completed" and last.get("source_saved") is True and Path(last["source"]).resolve() == source and disk_sha == last.get("source_sha256") and not collection_mismatches and not changed_export_images
    report["passed"] = all(checks.values())
    report["failed_checks"] = [name for name, passed in checks.items() if not passed]
    (log / "final_source_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    print(json.dumps({"passed": report["passed"], "checks": len(checks), "failed_checks": report["failed_checks"],
                      "old_changed": len(changed), "old_digest_changed": len(digest_changed),
                      "archived_pier": len(archived_names), "shipyard_components": len(members),
                      "shipyard_meshes": len(yard_meshes), "disk_source_sha256": disk_sha}, ensure_ascii=False))
    return report
