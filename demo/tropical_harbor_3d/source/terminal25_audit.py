"""Independent, read-only live audit for the new 2026-11-25 terminal.

Run only through the task-owned Blender MCP after site/model adjustments.
This script reads the current scene and the immutable current-round snapshots;
it does not load any old terminal asset, execute construction code, alter scene
data, save the blend, or export assets. Only a timestamped audit JSON is written.
The caller must check PID, source path, and MCP port before invoking this file.
Technical checks do not constitute visual acceptance.
"""

import hashlib
import json
import math
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(bpy.data.filepath).parent.parent
LOG = ROOT / "captures/terminal_rebuild_20261125"
PLAN_PATH = ROOT.parent.parent / "docs/terminal_rebuild_20261125/current_terminal_plan.json"
TERRAIN = "C25_ContourBuiltCoast"
COLLECTION = "Reference_Terminal"
ARCHIVE = "Archive_TerminalSimpleHouses_20261125"
GRASS_RECTS = [(-7.45, 3.35, 22.72, 27.18), (-9.20, -7.2, 23.65, 25.4)]


def digest(ob, matrix=None):
    """Byte-for-byte same scope and ordering as terminal25_01_snapshot.py."""
    h = hashlib.sha256()
    h.update(np.asarray(ob.matrix_world if matrix is None else matrix, dtype=np.float64).tobytes())
    if ob.type == "MESH":
        a = np.empty(len(ob.data.vertices) * 3, np.float32)
        ob.data.vertices.foreach_get("co", a)
        h.update(a.tobytes())
        a = np.empty(len(ob.data.loops), np.int32)
        ob.data.loops.foreach_get("vertex_index", a)
        h.update(a.tobytes())
        for uv in ob.data.uv_layers:
            a = np.empty(len(uv.data) * 2, np.float32)
            uv.data.foreach_get("uv", a)
            h.update(a.tobytes())
        h.update("|".join(m.name if m else "" for m in ob.data.materials).encode())
    return h.hexdigest()


def bounds(ob):
    ps = [ob.matrix_world @ Vector(p) for p in ob.bound_box]
    return np.array([[min(p[k] for p in ps) for k in range(3)],
                     [max(p[k] for p in ps) for k in range(3)]])


def mesh_arrays(ob):
    p = np.empty((len(ob.data.vertices), 3), np.float32)
    ob.data.vertices.foreach_get("co", p.ravel())
    ix = np.empty(len(ob.data.loops), np.int32)
    ob.data.loops.foreach_get("vertex_index", ix)
    return p, ix


report = {
    "created_local": datetime.now().astimezone().isoformat(),
    "pid": os.getpid(), "source": bpy.data.filepath,
    "source_dirty": bool(bpy.data.is_dirty), "blender": bpy.app.version_string,
    "coordinates": "Blender x,y,z; Godot x,z,-y",
    "read_only_scene_audit": True, "checks": [], "warnings": [],
    "limitations": [
        "Object digest covers transform, mesh vertices/loops, UV data and material slot names; it does not cover material node contents, modifiers or custom properties.",
        "The baseline stores grass digests/counts, not full leaf geometry. Changed grass is limited to reported objects and its remaining roots are checked; unchanged geometry outside deleted leaves cannot be proved from this snapshot alone.",
        "Walkway checks sample visible support and head clearance; this is not a Godot character-navigation or collision test. The main door is intentionally a closed decorative door, and the right tower has no authored entrance.",
        "AABB screening precedes geometric ray tests. Contact is sampled; neither these checks nor a pass is visual acceptance.",
    ],
}


def check(label, passed, **details):
    if "name" in details:
        details["subject"] = details.pop("name")
    report["checks"].append({"name": label, "pass": bool(passed), **details})
    return bool(passed)


def warn(message, **details):
    report["warnings"].append({"message": message, **details})


required = [LOG / "objects_before.json", LOG / "terrain_before.npz", PLAN_PATH, LOG / "site.json"]
assert all(p.exists() for p in required), "Missing current-round immutable snapshot, plan or completed site report"
assert bpy.data.collections.get(COLLECTION), "New terminal collection is absent"
assert bpy.data.objects.get(TERRAIN), "Current terrain is absent"
before_rows = json.loads((LOG / "objects_before.json").read_text(encoding="utf8"))
before = {r["name"]: r for r in before_rows}
plan = json.loads(PLAN_PATH.read_text(encoding="utf8"))
site = json.loads((LOG / "site.json").read_text(encoding="utf8"))
connections_path = LOG / "connections.json"
connections = json.loads(connections_path.read_text(encoding="utf8")) if connections_path.exists() else {}
baseline = np.load(LOG / "terrain_before.npz")
collection = bpy.data.collections[COLLECTION]
terminal_objects = [o for o in collection.objects if o.type == "MESH"]
terminal_names = {o.name for o in terminal_objects}
old_names = plan["archive_structure_names"] + plan["associated_prop_names"]
keep_names = plan["preserve_arrival_geometry"]["names"] + plan["preserve_arrival_deck_pegs"]["names"]
check("baseline_unique_objects", len(before) == len(before_rows), count=len(before_rows))
check("archive_manifest_918", len(old_names) == len(set(old_names)) == 918)
check("protected_platform_bridge_pegs_203", len(keep_names) == len(set(keep_names)) == 203)
check("site_archive_matches_semantic_manifest", set(site.get("archived_names", [])) == set(old_names))
check("new_terminal_is_visible", not collection.hide_render and not collection.hide_viewport)

# Exact old-object invariance, including archived structures and all 203 pier parts.
archive = bpy.data.collections.get(ARCHIVE)
missing = [n for n in before if bpy.data.objects.get(n) is None]
check("no_old_object_disappeared", not missing, missing=missing)
archive_bad = []
for name in old_names:
    ob = bpy.data.objects.get(name)
    if ob is None or archive is None or ob.name not in archive.objects or any(c != archive for c in ob.users_collection):
        archive_bad.append(name)
check("918_old_parts_archived_and_hidden", archive is not None and archive.hide_render and archive.hide_viewport and not archive_bad,
      invalid_members=archive_bad)
archive_changed = [n for n in old_names if bpy.data.objects.get(n) and digest(bpy.data.objects[n]) != before[n]["digest"]]
check("archived_geometry_and_transforms_preserved", not archive_changed, changed=archive_changed)
keep_bad = []
for name in keep_names:
    ob = bpy.data.objects.get(name)
    if ob is None or digest(ob) != before[name]["digest"] or before[name]["collection"] not in [c.name for c in ob.users_collection]:
        keep_bad.append(name)
check("203_platform_bridge_pegs_unchanged", not keep_bad, changed_or_missing=keep_bad)

plant_results = {}
plant_changed_names = set()
for key, required_move in [("palm_17", True), ("tree_3", bool(connections.get("tree_group")))]:
    names = plan["foliage_groups"][key]["names"]
    deltas, bad = [], []
    for name in names:
        ob = bpy.data.objects.get(name)
        if ob is None:
            bad.append({"name": name, "reason": "missing"})
            continue
        old_matrix = np.asarray(before[name]["matrix"], np.float64)
        now = np.asarray(ob.matrix_world, np.float64)
        delta = now[:3, 3] - old_matrix[:3, 3]
        deltas.append(delta)
        if digest(ob, old_matrix) != before[name]["digest"] or not np.allclose(now[:3, :3], old_matrix[:3, :3], atol=2e-6, rtol=0):
            bad.append({"name": name, "reason": "geometry/rotation/scale changed"})
        if digest(ob) != before[name]["digest"]:
            plant_changed_names.add(name)
    rigid = len(deltas) == len(names) and np.max(np.abs(np.asarray(deltas) - deltas[0])) < 3e-5
    moved = bool(deltas) and np.linalg.norm(deltas[0]) > 1e-5
    plant_results[key] = {"members": len(names), "delta": deltas[0].tolist() if deltas else None, "moved": moved, "bad": bad}
    check(key + "_complete_rigid_group", rigid and not bad and (moved or not required_move), **plant_results[key])
report["plants"] = plant_results
expected_palm_delta = np.asarray(site.get("palm_delta", []), float)
palm_extra = np.asarray(connections.get("palm_additional_delta", [0, 0, 0]), float)
palm_delta = plant_results["palm_17"]["delta"]
check("palm_move_reports_match_full_group", set(site.get("palm_group", [])) == set(plan["foliage_groups"]["palm_17"]["names"]))
check("palm_move_reports_match_observed_total_delta",
      expected_palm_delta.shape == palm_extra.shape == (3,) and palm_delta is not None
      and np.allclose(palm_delta, expected_palm_delta + palm_extra, atol=3e-5, rtol=0),
      observed_delta=palm_delta, site_delta=expected_palm_delta, additional_delta=palm_extra)
if connections.get("tree_group"):
    check("tree_move_report_matches_full_group", set(connections["tree_group"]) == set(plan["foliage_groups"]["tree_3"]["names"]))
    delta = plant_results["tree_3"]["delta"]
    check("tree_move_report_matches_observed_delta", delta is not None and np.allclose(delta, connections["tree_delta"], atol=3e-5, rtol=0))

grass_rows = site.get("grass", [])
grass_names = {r["object"] for r in grass_rows}
valid_grass_names = {n for n, r in before.items() if r["collection"] in {"Reference_Foliage", "Reference_GroundCover"} and any(k in n for k in ["Grass", "Tuft"])}
check("grass_edits_only_known_grass_meshes", grass_names <= valid_grass_names, reported=sorted(grass_names), valid=sorted(valid_grass_names))
allowed_changes = {TERRAIN} | plant_changed_names | grass_names
external_changed, collection_changed = [], []
for name, row in before.items():
    ob = bpy.data.objects.get(name)
    if ob is None:
        continue
    if name not in allowed_changes and digest(ob) != row["digest"]:
        external_changed.append(name)
    if name not in old_names and row["collection"] not in [c.name for c in ob.users_collection]:
        collection_changed.append(name)
check("all_other_old_object_digests_unchanged", not external_changed, changed=external_changed,
      tested=len(before) - len(allowed_changes), authorized_digest_exceptions=sorted(allowed_changes))
check("other_old_collections_preserved", not collection_changed, changed=collection_changed)
new_external = []
for c in bpy.data.collections:
    if c.name.startswith("Reference_") and c.name != COLLECTION and not c.hide_render:
        new_external += [o.name for o in c.objects if o.type == "MESH" and o.name not in before]
check("new_geometry_confined_to_terminal_collection", not new_external, new_elsewhere=sorted(set(new_external)), new_terminal_meshes=len(terminal_objects))
check("terminal_contains_no_reused_old_objects", not (terminal_names & set(before)), reused=sorted(terminal_names & set(before)))

# Connected leaf counting uses the same lowest-world-vertex root definition as site.
grass_results = []
for row in grass_rows:
    name = row["object"]
    ob = bpy.data.objects.get(name)
    if ob is None or name not in before:
        check("grass_exists_" + name, False)
        continue
    p, _ = mesh_arrays(ob)
    edges = np.empty(len(ob.data.edges) * 2, np.int32)
    ob.data.edges.foreach_get("vertices", edges)
    neighbors = [[] for _ in range(len(p))]
    for a, b in edges.reshape(-1, 2):
        neighbors[a].append(b)
        neighbors[b].append(a)
    seen = np.zeros(len(p), bool)
    remaining_inside = 0
    for start in range(len(p)):
        if seen[start]:
            continue
        stack, indices = [start], []
        seen[start] = True
        while stack:
            q = stack.pop()
            indices.append(q)
            for nxt in neighbors[q]:
                if not seen[nxt]:
                    seen[nxt] = True
                    stack.append(nxt)
        world = [ob.matrix_world @ Vector(p[k]) for k in indices]
        rt = min(world, key=lambda v: v.z)
        remaining_inside += any(a <= rt.x <= b and c <= rt.y <= d for a, b, c, d in GRASS_RECTS)
    removed = before[name]["vertices"] - len(p)
    okay = removed == row["vertices_removed"] and removed > 0 and remaining_inside == 0
    grass_results.append({"name": name, "vertices_removed": removed, "remaining_roots_inside": remaining_inside})
    check("grass_footprint_clear_" + name, okay, **grass_results[-1])
report["grass"] = grass_results

# Terrain comparisons independently inspect current geometry and the exact
# applied ground-fix snapshot. The initial 05 cut remains separately auditable.
terrain = bpy.data.objects[TERRAIN]
p, loops = mesh_arrays(terrain)
p0 = np.asarray(baseline["positions"], np.float32)
tri0 = np.asarray(baseline["triangles"], np.int32)
tri = loops.reshape(-1, 3) if len(loops) % 3 == 0 and all(len(q.vertices) == 3 for q in terrain.data.polygons) else None
indices_valid = tri is not None and len(tri) > 0 and tri.min() >= 0 and tri.max() < len(p)
original_present = len(p0) == 66230 and len(tri0) == 114226 and len(p) >= len(p0)
check("terrain_explicit_valid_triangles", indices_valid and np.all(np.isfinite(p)), vertices=len(p), polygons=len(terrain.data.polygons))
check("terrain_original_66230_vertices_retained", original_present, before_vertices=len(p0), after_vertices=len(p))
check("terrain_transform_unchanged", np.array_equal(np.asarray(terrain.matrix_world), np.asarray(before[TERRAIN]["matrix"])))
ground_path = LOG / "ground_fix.json"
after_path = LOG / "terrain_after.npz"
ground_fix = json.loads(ground_path.read_text(encoding="utf8")) if ground_path.exists() else None
if indices_valid and original_present:
    edges = np.sort(np.concatenate([tri0[:, [0, 1]], tri0[:, [1, 2]], tri0[:, [2, 0]]]), axis=1)
    unique_edges, edge_counts = np.unique(edges, axis=0, return_counts=True)
    boundary_before = unique_edges[edge_counts == 1]
    edges = np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
    unique_edges, edge_counts = np.unique(edges, axis=0, return_counts=True)
    boundary_after = unique_edges[edge_counts == 1]
    boundary_indices = np.unique(boundary_before)
    check("terrain_original_xy_bitwise_unchanged", np.array_equal(p[:len(p0), :2], p0[:, :2]))
    check("terrain_1020_boundary_edge_indices_unchanged", len(boundary_before) == len(boundary_after) == 1020 and np.array_equal(boundary_after, boundary_before), before_edges=len(boundary_before), after_edges=len(boundary_after))
    check("terrain_boundary_coordinates_unchanged", np.array_equal(p[boundary_indices], p0[boundary_indices]), boundary_edges=len(boundary_after), boundary_vertices=len(boundary_indices))
    check("terrain_no_nonmanifold_edges", not np.any(edge_counts > 2), nonmanifold_edges=int(np.count_nonzero(edge_counts > 2)))
    crosses = np.cross(p[tri[:, 1]].astype(float) - p[tri[:, 0]], p[tri[:, 2]].astype(float) - p[tri[:, 0]])
    check("terrain_no_degenerate_triangles", bool(np.all(np.linalg.norm(crosses, axis=1) >= 1e-10)), degenerate=int(np.count_nonzero(np.linalg.norm(crosses, axis=1) < 1e-10)))
    check("terrain_no_downward_triangles", bool(np.all(crosses[:, 2] > 1e-10)), downward=int(np.count_nonzero(crosses[:, 2] <= 1e-10)))
    changed = np.flatnonzero(np.abs(p[:len(p0), 2] - p0[:, 2]) > 1e-7)
    geometry_sha = hashlib.sha256(p.astype(np.float32).tobytes() + tri.astype(np.int32).ravel().tobytes()).hexdigest()
    baseline_sha = hashlib.sha256(p0.tobytes() + tri0.ravel().tobytes()).hexdigest()
    if ground_fix is not None:
        check("terrain_ground_fix_status_applied", ground_fix.get("status") == "applied")
        check("terrain_ground_fix_uses_current_round_baseline", ground_fix.get("terrain_before_sha256") == baseline_sha)
        check("terrain_ground_fix_geometry_hash_matches", ground_fix.get("terrain_after_sha256") == geometry_sha, observed=geometry_sha, certified=ground_fix.get("terrain_after_sha256"))
        after_equal = False
        if after_path.exists():
            with np.load(after_path) as after:
                after_equal = np.array_equal(p, after["positions"]) and np.array_equal(tri, after["triangles"])
        check("terrain_all_original_and_added_geometry_matches_after_snapshot", after_equal, after_snapshot_exists=after_path.exists(), added_vertices=len(p)-len(p0), added_triangles=len(tri)-len(tri0))
        counts = {"before_vertices": len(p0), "before_triangles": len(tri0), "after_vertices": len(p), "after_triangles": len(tri), "added_vertices": len(p)-len(p0), "added_triangles": len(tri)-len(tri0)}
        check("terrain_ground_fix_counts_match_actual", all(ground_fix.get(key) == value for key, value in counts.items()), actual=counts)
        core = ((p0[:, 0] >= -.03 - 2e-6) & (p0[:, 0] <= 2.93 + 2e-6) & (p0[:, 1] >= 23.57 - 2e-6) & (p0[:, 1] <= 26.98 + 2e-6))
        expected = p0[:, 2].copy()
        expected[core] = np.minimum(expected[core], np.float32(1.63))
        error = float(np.max(np.abs(p[:len(p0), 2] - expected)))
        check("terrain_original_height_changes_confined_to_exact_core", np.array_equal(p[:len(p0), 2], expected), max_formula_error_m=error, changed_vertices=len(changed), core=[-.03, 2.93, 23.57, 26.98], ceiling_m=1.63)
        check("terrain_outside_core_original_vertices_bitwise_restored", np.array_equal(p[:len(p0)][~core], p0[~core]))
        check("terrain_changed_original_ids_match_ground_fix", set(changed.tolist()) == set(ground_fix.get("changed_original_vertex_ids", [])))
        added = p[len(p0):]
        added_core = ((added[:, 0] >= -.03 - 2e-6) & (added[:, 0] <= 2.93 + 2e-6) & (added[:, 1] >= 23.57 - 2e-6) & (added[:, 1] <= 26.98 + 2e-6))
        check("terrain_added_core_vertices_below_floor_ceiling", not len(added[added_core]) or bool(np.all(added[added_core, 2] <= np.float32(1.63))), added_core_vertices=int(np.count_nonzero(added_core)))
        report["terrain_ground_fix"] = {"certificate": str(ground_path), "certificate_sha256": hashlib.sha256(ground_path.read_bytes()).hexdigest(), "geometry_sha256": geometry_sha, **counts}
        # The fan repair is independently derived from all appended-centroid
        # one-rings; neither its changed list nor the replacement NPZ is treated
        # as proof of the interpolation rule. Original points/cut-edge nodes
        # and every triangle/XY coordinate must remain exactly as before repair.
        fan_path = LOG / "cut_fan_fix.json"
        refinement = ground_fix.get("fan_centroid_refinement")
        if fan_path.exists() or refinement:
            fan_before_path = LOG / "before_cut_fan_fix/terrain_after.npz"
            fan_before_cert_path = LOG / "before_cut_fan_fix/ground_fix.json"
            evidence_exists = fan_path.exists() and fan_before_path.exists() and fan_before_cert_path.exists()
            check("terrain_fan_refinement_evidence_complete", evidence_exists)
            if evidence_exists:
                fan_report = json.loads(fan_path.read_text(encoding="utf8"))
                fan_before_cert = json.loads(fan_before_cert_path.read_text(encoding="utf8"))
                with np.load(fan_before_path) as fan_snapshot:
                    pf = np.asarray(fan_snapshot["positions"], np.float32)
                    tf = np.asarray(fan_snapshot["triangles"], np.int32)
                before_fan_sha = hashlib.sha256(pf.tobytes() + tf.ravel().tobytes()).hexdigest()
                first_centroid = len(p0) + int(fan_before_cert.get("shared_intersection_vertices", -1000000))
                checkpoint_ok = (first_centroid == 66367 and p.shape == pf.shape and np.array_equal(tri, tf))
                check("terrain_fan_refinement_certificate_chain",
                      fan_report.get("status") == "applied" and fan_report.get("first_centroid") == first_centroid
                      and fan_report.get("terrain_before_sha256") == before_fan_sha == fan_before_cert.get("terrain_after_sha256")
                      and fan_report.get("terrain_after_sha256") == geometry_sha
                      and isinstance(refinement, dict) and refinement.get("report") == "cut_fan_fix.json"
                      and refinement.get("previous_certificate") == "before_cut_fan_fix/ground_fix.json",
                      before_sha256=before_fan_sha, after_sha256=geometry_sha, first_centroid=first_centroid)
                check("terrain_fan_refinement_preserves_vertex_count_and_all_triangle_indices", checkpoint_ok,
                      before_vertices=len(pf), after_vertices=len(p), before_triangles=len(tf), after_triangles=len(tri))
                if checkpoint_ok:
                    check("terrain_fan_refinement_preserves_all_xy", np.array_equal(p[:, :2], pf[:, :2]))
                    check("terrain_fan_refinement_preserves_original_66230_and_137_cut_vertices", np.array_equal(p[:first_centroid], pf[:first_centroid]), checked=first_centroid)
                    neighbors = {index: set() for index in range(first_centroid, len(p))}
                    for face in tf:
                        for index in face:
                            if index >= first_centroid:
                                neighbors[int(index)].update(int(n) for n in face if n != index)
                    adjacency_bad = {index: sorted(ns) for index, ns in neighbors.items() if not ns or any(n >= first_centroid for n in ns)}
                    check("terrain_fan_centroids_have_only_original_or_cut_boundary_neighbors", not adjacency_bad,
                          centroids=len(neighbors), invalid=adjacency_bad)
                    if not adjacency_bad:
                        recomputed = pf.copy()
                        expected_changes = {}
                        centroid_xy_errors, upward_targets = [], []
                        for index, ns in neighbors.items():
                            ns = sorted(ns)
                            xy_error = float(np.max(np.abs(pf[ns, :2].astype(float).mean(0) - pf[index, :2])))
                            centroid_xy_errors.append(xy_error)
                            target = float(pf[ns, 2].astype(float).mean())
                            if abs(target - float(pf[index, 2])) < 2e-6:
                                continue
                            if target >= float(pf[index, 2]) + 2e-6:
                                upward_targets.append(index)
                            recomputed[index, 2] = target
                            expected_changes[index] = {"neighbors": ns, "before": float(pf[index, 2]), "after": target,
                                                       "lowering": float(pf[index, 2]) - target, "xy": pf[index, :2].astype(float).tolist()}
                        check("terrain_fan_centroid_xy_is_boundary_mean", max(centroid_xy_errors, default=0) < 3e-6,
                              checked=len(centroid_xy_errors), maximum_error_m=max(centroid_xy_errors, default=0))
                        check("terrain_fan_mean_rule_does_not_raise_peaks", not upward_targets, raised=upward_targets)
                        check("terrain_all_fan_centroid_heights_match_independent_mean_rule", np.array_equal(p, recomputed),
                              checked=len(neighbors), recomputed_changed_count=len(expected_changes),
                              maximum_height_error_m=float(np.max(np.abs(p[:, 2]-recomputed[:, 2]))))
                        actual_changed = set(np.flatnonzero(np.any(p != pf, axis=1)).tolist())
                        listed_changes = fan_report.get("changes", [])
                        listed = {row["vertex"]: row for row in listed_changes}
                        row_failures = []
                        for index, target_row in expected_changes.items():
                            row = listed.get(index)
                            if (row is None or row.get("neighbors") != target_row["neighbors"]
                                    or row.get("xy") != target_row["xy"]
                                    or any(abs(float(row.get(key, float("inf"))) - target_row[key]) > 1e-12
                                           for key in ("before", "after", "lowering"))):
                                row_failures.append(index)
                        check("terrain_exact_44_fan_changes_and_report_values",
                              len(expected_changes) == 44 and actual_changed == set(expected_changes) == set(listed)
                              and len(listed_changes) == len(listed) and fan_report.get("changed_count") == 44
                              and refinement.get("changed_count") == 44 and not row_failures,
                              changed_count=len(actual_changed), changes=sorted(actual_changed), row_failures=row_failures)
                        report["terrain_fan_refinement"] = {"report": str(fan_path), "before_snapshot": str(fan_before_path),
                            "before_geometry_sha256": before_fan_sha, "after_geometry_sha256": geometry_sha,
                            "first_centroid": first_centroid, "centroids_checked": len(neighbors),
                            "changed_count": len(actual_changed), "maximum_lowering_m": max((row["lowering"] for row in expected_changes.values()), default=0)}
    else:
        unchanged_topology = p.shape == p0.shape and np.array_equal(tri, tri0)
        check("terrain_without_ground_fix_preserves_triangle_indices", unchanged_topology)
        if unchanged_topology:
            dx = np.maximum(np.maximum(-.03 - p0[:, 0], p0[:, 0] - 2.93), 0)
            dy = np.maximum(np.maximum(23.57 - p0[:, 1], p0[:, 1] - 26.98), 0)
            dist = np.sqrt(dx * dx + dy * dy)
            weight = np.clip(1 - dist / .32, 0, 1)
            weight = weight * weight * (3 - 2 * weight)
            expected = p0[:, 2] - np.maximum(p0[:, 2] - 1.68, 0) * weight
            check("terrain_exact_initial_planned_cut_only", np.max(np.abs(p[:, 2] - expected)) < 2e-6, max_formula_error_m=float(np.max(np.abs(p[:, 2] - expected))))
            check("terrain_outside_initial_cut_halo_bitwise_unchanged", np.array_equal(p[dist >= .32], p0[dist >= .32]))
            check("terrain_changed_indices_match_initial_site_report", set(changed.tolist()) == set(site.get("terrain_changed_indices", [])))
    terrain_bvh = BVHTree.FromPolygons(p.tolist(), tri.tolist(), all_triangles=True)
else:
    terrain_bvh = None


def terrain_height(x, y):
    if terrain_bvh is None:
        return None
    hit = terrain_bvh.ray_cast(Vector((x, y, 40)), Vector((0, 0, -1)), 160)[0]
    return None if hit is None else float(hit.z)


depsgraph = bpy.context.evaluated_depsgraph_get()
bvh_cache = {}


def world_bvh(ob):
    if ob.name in bvh_cache:
        return bvh_cache[ob.name]
    evaluated = ob.evaluated_get(depsgraph)
    data = evaluated.to_mesh()
    try:
        data.calc_loop_triangles()
        vs = [(evaluated.matrix_world @ v.co)[:] for v in data.vertices]
        fs = [tuple(t.vertices) for t in data.loop_triangles]
        result = BVHTree.FromPolygons(vs, fs, all_triangles=True)
    finally:
        evaluated.to_mesh_clear()
    bvh_cache[ob.name] = result
    return result


box_cache = {o.name: bounds(o) for o in terminal_objects}


def support_at(x, y, obs, max_z=4.0):
    best = None
    for ob in obs:
        bb = box_cache.get(ob.name)
        if bb is None:
            bb = bounds(ob)
            box_cache[ob.name] = bb
        if not (bb[0, 0] - 1e-4 <= x <= bb[1, 0] + 1e-4 and bb[0, 1] - 1e-4 <= y <= bb[1, 1] + 1e-4):
            continue
        hit = world_bvh(ob).ray_cast(Vector((x, y, max_z)), Vector((0, 0, -1)), 120)[0]
        if hit is not None and (best is None or hit.z > best[0]):
            best = (float(hit.z), ob.name)
    return best


# Floors must sit above ground; foundation segments must actually reach ground.
floor_results = []
for prefix in ["Main", "Small", "Gallery"]:
    ob = bpy.data.objects.get("TN25_" + prefix + "Floor")
    if ob is None:
        check(prefix + "_floor_exists", False)
        continue
    bb = bounds(ob)
    values = []
    for x in np.linspace(bb[0, 0] + .08, bb[1, 0] - .08, 11):
        for y in np.linspace(bb[0, 1] + .08, bb[1, 1] - .08, 11):
            ground = terrain_height(float(x), float(y))
            if ground is not None:
                values.append(float(bb[1, 2] - ground))
    floor_results.append({"name": ob.name, "samples": len(values), "minimum_ground_to_floor_top_m": min(values) if values else None})
    check(prefix + "_ground_does_not_bury_floor", len(values) == 121 and min(values) >= .07, **floor_results[-1])
report["floor_contacts"] = floor_results
foundation_results = []
for ob in terminal_objects:
    if not ("GroundStone" in ob.name or ob.name.startswith(("TN25_PorchFoundation", "TN25_WorkDeckPier", "TN25_RightLandingPier", "TN25_RearCutSupport"))):
        continue
    bb = bounds(ob)
    clearances = []
    for fx, fy in [(0.1, 0.1), (.9, .1), (.1, .9), (.9, .9), (.5, .5)]:
        x, y = bb[0, :2] + np.array([fx, fy]) * (bb[1, :2] - bb[0, :2])
        ground = terrain_height(float(x), float(y))
        if ground is not None:
            clearances.append(float(bb[0, 2] - ground))
    foundation_results.append({"name": ob.name, "sample_count": len(clearances), "maximum_base_gap_m": max(clearances) if clearances else None})
bad_foundations = [r for r in foundation_results if r["sample_count"] != 5 or r["maximum_base_gap_m"] > .035]
check("new_foundation_segments_contact_ground", bool(foundation_results) and not bad_foundations, checked=len(foundation_results), failures=bad_foundations)
report["foundation_contacts"] = foundation_results

# The late rear-wall correction has its own saved, inspectable scope. Old wall
# pieces remain archived; the replacement belongs only to the small-tower cut.
rear_fix_path = LOG / "rear_wall_fix.json"
if rear_fix_path.exists():
    rear_fix = json.loads(rear_fix_path.read_text(encoding="utf8"))
    rear_archive = bpy.data.collections.get("Archive_TN25_WideRearWall_20261125")
    archived_rows = rear_fix.get("archived", [])
    expected_archived = {row["name"] for row in archived_rows}
    archive_failures = []
    for row in archived_rows:
        ob = bpy.data.objects.get(row["name"])
        if ob is None:
            archive_failures.append({"object": row["name"], "reason": "missing"})
            continue
        current_corners = np.asarray([list(ob.matrix_world @ Vector(v)) for v in ob.bound_box], float)
        okay = (rear_archive is not None and list(ob.users_collection) == [rear_archive]
                and ob.name not in terminal_names
                and np.array_equal(np.asarray(ob.matrix_world), np.asarray(row["matrix"]))
                and np.array_equal(current_corners, np.asarray(row["bounds"])))
        if not okay:
            archive_failures.append({"object": ob.name, "reason": "collection, transform or bounds differ"})
    archive_set = {ob.name for ob in rear_archive.objects} if rear_archive else set()
    check("rear_wide_wall_11_parts_preserved_in_hidden_archive",
          len(expected_archived) == len(archived_rows) == 11 and archive_set == expected_archived
          and rear_archive is not None and rear_archive.hide_render and rear_archive.hide_viewport
          and not archive_failures, failures=archive_failures, archived_names=sorted(expected_archived))
    rear_supports = [ob for ob in terminal_objects if ob.name.startswith("TN25_RearCutSupport")]
    rear_caps = [ob for ob in terminal_objects if ob.name.startswith("TN25_RearCutCap")]
    new_rear_names = {ob.name for ob in rear_supports + rear_caps}
    check("rear_cut_replacement_is_exactly_four_supports_and_caps",
          len(rear_supports) == len(rear_caps) == 4 and new_rear_names == set(rear_fix.get("created", [])),
          supports=[ob.name for ob in rear_supports], caps=[ob.name for ob in rear_caps])
    dense_rear_contacts = []
    for ob in rear_supports:
        bb = bounds(ob)
        heights = []
        for x in np.linspace(bb[0, 0], bb[1, 0], 9):
            for y in np.linspace(bb[0, 1], bb[1, 1], 9):
                ground = terrain_height(float(x), float(y))
                if ground is not None:
                    heights.append(ground)
        embed = min(heights) - float(bb[0, 2]) if heights else None
        within_cut = bb[0, 0] >= .10 - 2e-6 and bb[1, 0] <= 2.90 + 2e-6 and bb[0, 1] >= 26.72 - 2e-6 and bb[1, 1] <= 26.97 + 2e-6
        row = {"object": ob.name, "bounds": bb.tolist(), "samples": len(heights), "minimum_embed_m": embed, "within_small_tower_cut": bool(within_cut)}
        dense_rear_contacts.append(row)
        check("rear_cut_support_dense_ground_contact_" + ob.name,
              len(heights) == 81 and embed is not None and embed >= .10 and within_cut, **row)
    report["rear_cut_support_contacts"] = dense_rear_contacts
    earlier_audit_path = LOG / "independent_audit_20261125_202636_329100.json"
    earlier_audit = json.loads(earlier_audit_path.read_text(encoding="utf8")) if earlier_audit_path.exists() else {}
    old_footings = {row["name"]: row for row in earlier_audit.get("foundation_contacts", [])
                   if row["name"].startswith(("TN25_MainGroundStone", "TN25_GalleryGroundStone"))}
    current_footings = {row["name"]: row for row in foundation_results
                       if row["name"].startswith(("TN25_MainGroundStone", "TN25_GalleryGroundStone"))}
    footing_failures = []
    for name, old in old_footings.items():
        current = current_footings.get(name)
        ob = bpy.data.objects.get(name)
        if (current is None or ob is None or ob.hide_render or ob.hide_get()
                or COLLECTION not in {c.name for c in ob.users_collection}
                or current["sample_count"] != old["sample_count"]
                or current["maximum_base_gap_m"] is None or old["maximum_base_gap_m"] is None
                or abs(current["maximum_base_gap_m"] - old["maximum_base_gap_m"]) > 1e-6):
            footing_failures.append(name)
    check("main_gallery_prior_grounded_footings_retained_visible",
          bool(old_footings) and set(current_footings) == set(old_footings) and not footing_failures,
          reference_audit=str(earlier_audit_path), checked=len(old_footings), failures=footing_failures,
          scope="Existing footing names, visible collection membership and ground contacts; prior full footing geometry digests were not recorded.")

# Every actual tread is sampled across its current footprint, including the
# relocated right run. No original stair-center coordinate is assumed here.
tread_objects = [ob for ob in terminal_objects if ob.name.startswith("TN25_WideEntryStep")]
check("fifteen_entrance_treads_present", len(tread_objects) == 15, count=len(tread_objects))
tread_ground_results = []
for ob in tread_objects:
    bb = bounds(ob)
    missing, intrusions, gaps = [], [], []
    for x in np.linspace(bb[0, 0] + .025, bb[1, 0] - .025, 9):
        for y in np.linspace(bb[0, 1] + .025, bb[1, 1] - .025, 5):
            hit = world_bvh(ob).ray_cast(Vector((float(x), float(y), float(bb[1, 2] + .2))), Vector((0, 0, -1)), 2)[0]
            ground = terrain_height(float(x), float(y))
            if hit is None or ground is None:
                missing.append([float(x), float(y)])
                continue
            gap = float(hit.z - ground)
            gaps.append(gap)
            if gap < .025:
                intrusions.append({"xy": [float(x), float(y)], "tread_top_above_terrain_m": gap,
                                   "required_clearance_deficit_m": .025-gap, "tread_top_z": float(hit.z), "terrain_z": ground})
    row = {"object": ob.name, "bounds": bb.tolist(), "samples": len(gaps), "missing_samples": missing,
           "minimum_tread_top_above_terrain_m": min(gaps) if gaps else None,
           "required_minimum_clearance_m": .025, "terrain_clearance_failures": intrusions}
    tread_ground_results.append(row)
    check("terrain_does_not_intrude_" + ob.name, len(gaps) == 45 and not missing and not intrusions, **row)
report["tread_ground_clearance"] = tread_ground_results

# Three existing apron-to-porch approaches: independent rays along five width lanes.
support_prefixes = ("TN25_MainFloor", "TN25_SmallFloor", "TN25_GalleryFloor", "TN25_FrontPorchPlank", "TN25_WideEntryStep", "TN25_GalleryLanding", "TN25_WorkDeckPlank", "Arrival_ApronBoard", "Arrival_LeftPierBoard")
walk_surfaces = [o for o in bpy.data.objects if o.type == "MESH" and ((o.name.startswith(support_prefixes) and "Bearer" not in o.name) or o.get("terminal25_walk_support", False))]
approaches = []
for label, cx, width in [("main", -4.9, 2.15), ("gallery", -1.0, 2.0), ("right", 1.65, 2.0)]:
    missing_samples, bad_steps, terrain_intrusions, samples, narrow_plank_seams = [], [], [], 0, 0
    run_treads = [ob for ob in tread_objects if abs(float((box_cache[ob.name][0, 0] + box_cache[ob.name][1, 0]) / 2) - cx) < .01]
    start_y = min([21.15] + [float(box_cache[ob.name][0, 1] - .15) for ob in run_treads])
    for offset in np.linspace(-min(width / 2 - .18, .66), min(width / 2 - .18, .66), 5):
        previous = None
        for y in np.linspace(start_y, 23.52, max(81, int(math.ceil((23.52 - start_y) / .03)) + 1)):
            x = cx + float(offset)
            hit = support_at(x, float(y), walk_surfaces)
            samples += 1
            # Authored planks have 8mm joints and bevels. A 24mm-wide support
            # sample can bridge those joints without concealing a missing board.
            if hit is None:
                nearby = [support_at(x + ox, float(y) + oy, walk_surfaces)
                          for ox, oy in [(-.012, 0), (.012, 0), (0, -.012), (0, .012)]]
                nearby = [value for value in nearby if value is not None]
                if nearby:
                    hit = max(nearby)
                    narrow_plank_seams += 1
            if hit is None:
                missing_samples.append([x, float(y)])
                previous = None
                continue
            if previous is not None and abs(hit[0] - previous) > .205:
                bad_steps.append({"xy": [x, float(y)], "rise_m": hit[0] - previous, "support": hit[1]})
            ground = terrain_height(x, float(y))
            if ground is not None and ground > hit[0] + .005:
                terrain_intrusions.append({"xy": [x, float(y)], "terrain_above_support_m": ground - hit[0], "support": hit[1]})
            previous = hit[0]
    approaches.append({"name": label, "sample_count": samples, "start_y": start_y, "end_y": 23.52, "narrow_plank_seams": narrow_plank_seams, "support_search_radius_m": .012, "missing_support": missing_samples, "excess_step": bad_steps, "terrain_intrusions": terrain_intrusions})
    check(label + "_apron_stair_porch_continuity", not missing_samples and not bad_steps and not terrain_intrusions, **approaches[-1])
report["approaches"] = approaches

# Door leaves/hardware are intentionally closed; structural beams must not span its opening.
door_exempt = ("TN25_DoorPlank", "TN25_DoorBrace", "TN25_DoorRing", "TN25_DoorJamb", "TN25_DoorLintel")
door_hits = []
for ob in terminal_objects:
    if ob.name.startswith(door_exempt):
        continue
    bb = box_cache[ob.name]
    if bb[1, 0] < -5.52 or bb[0, 0] > -4.28 or bb[1, 1] < 23.50 or bb[0, 1] > 23.90 or bb[1, 2] < 1.95 or bb[0, 2] > 3.95:
        continue
    collided = False
    for x in np.linspace(-5.48, -4.32, 9):
        for z in np.linspace(1.97, 3.94, 42):
            if world_bvh(ob).ray_cast(Vector((float(x), 23.48, float(z))), Vector((0, 1, 0)), .44)[0] is not None:
                collided = True
                break
        if collided:
            break
    if collided:
        door_hits.append(ob.name)
check("main_door_opening_free_of_unrelated_structure", not door_hits, blockers=door_hits,
      note="Closed door planks and door hardware are excluded; this tests the authored doorway aperture.")

# Feet of service furniture and the ground barrel need actual support, not assumed coordinates.
prop_contacts = []
props = [o for o in terminal_objects if o.name.startswith(("TN25_WorkBarrel", "TN25_ServiceShelfLeg")) and "Hoop" not in o.name]
for ob in props:
    bb = bounds(ob)
    x, y = (bb[0, :2] + bb[1, :2]) / 2
    hit = support_at(float(x), float(y), walk_surfaces, max_z=float(bb[0, 2] + .04))
    ground = terrain_height(float(x), float(y))
    height, source = hit if hit is not None else (ground, TERRAIN)
    if ground is not None and (height is None or ground > height):
        height, source = ground, TERRAIN
    gap = None if height is None else float(bb[0, 2] - height)
    prop_contacts.append({"name": ob.name, "support": source, "gap_m": gap})
bad_props = [r for r in prop_contacts if r["gap_m"] is None or not (-.07 <= r["gap_m"] <= .045)]
check("barrel_and_service_shelf_feet_supported", bool(prop_contacts) and not bad_props, failures=bad_props, checked=len(prop_contacts))
report["prop_contacts"] = prop_contacts

# Clearance warnings identify tree/roof AABB candidates; they do not falsely claim collision.
for key in ["palm_17", "palm_16", "tree_3", "tree_39", "tree_2"]:
    candidates = []
    for name in plan["foliage_groups"][key]["names"]:
        ob = bpy.data.objects.get(name)
        if ob is None:
            continue
        bb = bounds(ob)
        for terminal in terminal_objects:
            if not any(k in terminal.name for k in ["Roof", "SlateTile", "CurvedUnderlay", "UpperTower", "Front", "Back", "Side"]):
                continue
            tb = box_cache[terminal.name]
            if np.all(bb[1] > tb[0] + .01) and np.all(tb[1] > bb[0] + .01):
                candidates.append([name, terminal.name])
    if candidates:
        warn(key + " has possible canopy/building overlap; inspect final silhouette or perform triangle intersection", candidate_count=len(candidates), first_candidates=candidates[:30])

report["passed"] = all(row["pass"] for row in report["checks"])
report["failed_checks"] = [row["name"] for row in report["checks"] if not row["pass"]]
report["check_count"] = len(report["checks"])
report["scene_dirty_after"] = bool(bpy.data.is_dirty)
stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
output = LOG / ("independent_audit_" + stamp + ".json")
output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=lambda x: x.item() if isinstance(x, np.generic) else x.tolist() if isinstance(x,np.ndarray) else str(x)), encoding="utf8")
print(json.dumps({"report": str(output), "passed": report["passed"], "checks": report["check_count"],
                  "failed": report["failed_checks"], "warnings": len(report["warnings"]),
                  "read_only_scene_audit": True}, ensure_ascii=False))
