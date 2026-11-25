"""Owned GUI Blender export for the November 25 terminal rebuild.

Loading this file only defines export_terminal25. The first explicit call must
use the default full export. Later visual iterations may use terminal_only=True
or changed_only=True. The latter always exports terminal, exports changed
ancillary collections, and exports terrain/height only when geometry changed.
No historical terminal asset or production script is loaded by this module.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import time
from pathlib import Path

import numpy as np


def _tn25_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tn25_digest(obj):
    """Exactly the digest used by this round's immutable object snapshot."""
    digest = hashlib.sha256()
    digest.update(np.asarray(obj.matrix_world, dtype=np.float64).tobytes())
    if obj.type == "MESH":
        coords = np.empty(len(obj.data.vertices) * 3, np.float32)
        obj.data.vertices.foreach_get("co", coords)
        digest.update(coords.tobytes())
        loops = np.empty(len(obj.data.loops), np.int32)
        obj.data.loops.foreach_get("vertex_index", loops)
        digest.update(loops.tobytes())
        for layer in obj.data.uv_layers:
            values = np.empty(len(layer.data) * 2, np.float32)
            layer.data.foreach_get("uv", values)
            digest.update(values.tobytes())
        digest.update("|".join(m.name if m else "" for m in obj.data.materials).encode())
    return digest.hexdigest()


def _tn25_verify_terrain(positions, loops, log):
    """Accept topology changes only against this round's applied ground fix."""
    positions = np.asarray(positions, dtype=np.float32)
    triangles = np.asarray(loops, dtype=np.int32).reshape(-1, 3)
    terrain_digest = hashlib.sha256(positions.tobytes() + triangles.ravel().tobytes()).hexdigest()
    with np.load(log / "terrain_before.npz") as baseline:
        before_positions = np.asarray(baseline["positions"], dtype=np.float32)
        before_triangles = np.asarray(baseline["triangles"], dtype=np.int32)
    if len(before_positions) != 66230 or len(before_triangles) != 114226:
        raise RuntimeError("Unexpected current-round terrain baseline dimensions")
    if len(positions) < len(before_positions):
        raise RuntimeError("Original terrain vertices were removed")
    if not np.array_equal(positions[:len(before_positions), :2], before_positions[:, :2]):
        raise RuntimeError("Original terrain XY coordinates changed")
    if not np.all(np.isfinite(positions)) or triangles.min() < 0 or triangles.max() >= len(positions):
        raise RuntimeError("Terrain contains invalid coordinates or triangle indices")
    changed_original = np.flatnonzero(np.any(positions[:len(before_positions)] != before_positions, axis=1))
    topology_changed = positions.shape != before_positions.shape or not np.array_equal(triangles, before_triangles)
    result = {
        "terrain_geometry_sha256": terrain_digest,
        "terrain_topology_changed": topology_changed,
        "terrain_changed_original_vertices": len(changed_original),
        "terrain_added_vertices": len(positions) - len(before_positions),
        "terrain_added_triangles": len(triangles) - len(before_triangles),
        "terrain_changed_vertices": len(changed_original) + len(positions) - len(before_positions),
        "terrain_original_xy_unchanged": True,
        "terrain_topology_certificate": None,
    }
    if not topology_changed:
        return result
    certificate_path = log / "ground_fix.json"
    after_path = log / "terrain_after.npz"
    if not certificate_path.is_file() or not after_path.is_file():
        raise RuntimeError("Terrain topology changed without the applied ground-fix certificate and snapshot")
    certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
    if certificate.get("status") != "applied":
        raise RuntimeError("Ground-fix certificate has not been applied")
    with np.load(after_path) as after:
        after_positions = np.asarray(after["positions"], dtype=np.float32)
        after_triangles = np.asarray(after["triangles"], dtype=np.int32)
    after_digest = hashlib.sha256(after_positions.tobytes() + after_triangles.ravel().tobytes()).hexdigest()
    if certificate.get("terrain_after_sha256") != after_digest or terrain_digest != after_digest:
        raise RuntimeError("Current terrain does not match the certified ground-fix geometry hash")
    if not np.array_equal(positions, after_positions) or not np.array_equal(triangles, after_triangles):
        raise RuntimeError("Current terrain differs from the certified after snapshot")
    expected_counts = {
        "before_vertices": len(before_positions), "before_triangles": len(before_triangles),
        "after_vertices": len(positions), "after_triangles": len(triangles),
        "added_vertices": len(positions) - len(before_positions),
        "added_triangles": len(triangles) - len(before_triangles),
        "boundary_edges_before": 1020, "boundary_edges_after": 1020,
        "nonmanifold_edges": 0, "degenerate_triangles": 0, "downward_triangles": 0,
    }
    for key, value in expected_counts.items():
        if certificate.get(key) != value:
            raise RuntimeError("Ground-fix certificate count mismatch: " + key)
    if certificate.get("original_xy_unchanged") is not True or certificate.get("boundary_indices_unchanged") is not True:
        raise RuntimeError("Ground-fix certificate does not preserve original XY and boundaries")

    def mesh_edges(tris):
        edges = np.sort(np.concatenate((tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]])), axis=1)
        unique, counts = np.unique(edges, axis=0, return_counts=True)
        return unique[counts == 1], int(np.count_nonzero(counts > 2))

    before_boundary, _ = mesh_edges(before_triangles)
    after_boundary, nonmanifold = mesh_edges(triangles)
    if len(before_boundary) != 1020 or not np.array_equal(before_boundary, after_boundary):
        raise RuntimeError("Certified terrain does not independently preserve original boundary indices")
    vertices64 = positions.astype(np.float64)
    cross = np.cross(vertices64[triangles[:, 1]] - vertices64[triangles[:, 0]],
                     vertices64[triangles[:, 2]] - vertices64[triangles[:, 0]])
    degenerate = int(np.count_nonzero(np.linalg.norm(cross, axis=1) < 1e-10))
    downward = int(np.count_nonzero(cross[:, 2] <= 1e-10))
    if nonmanifold or degenerate or downward:
        raise RuntimeError("Certified terrain failed independent manifold/area/orientation checks")
    result["terrain_topology_certificate"] = {
        "file": str(certificate_path), "sha256": _tn25_sha(certificate_path),
        "after_snapshot": str(after_path), "after_snapshot_file_sha256": _tn25_sha(after_path),
        "geometry_sha256": after_digest, "status": "applied", **expected_counts,
        "independent_topology_checks_passed": True,
    }
    return result


def export_terminal25(expected_pid, terminal_only=False, log_path=None, changed_only=False):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    if bpy.app.background or os.getpid() != expected_pid:
        raise RuntimeError("Export requires the independently owned GUI Blender PID")
    root = Path(bpy.data.filepath).parent.parent
    source_path = Path(bpy.data.filepath)
    if source_path.name != "harbor_shore_control_mcp.blend":
        raise RuntimeError("Wrong C25 source file")
    log = Path(log_path) if log_path else root / "captures/terminal_rebuild_20261125"
    if not log.is_absolute():
        log = root / log
    session = json.loads((log / "session_start.json").read_text(encoding="utf-8"))
    if session["pid"] != expected_pid or Path(session["source"]) != source_path:
        raise RuntimeError("Snapshot session and current source do not match")
    if bpy.types.blendermcp_server.port != session["port"]:
        raise RuntimeError("Owned MCP port changed")
    if bpy.context.mode != "OBJECT":
        raise RuntimeError("Export requires Object mode")
    if terminal_only and changed_only:
        raise ValueError("terminal_only and changed_only are mutually exclusive")
    if not callable(getattr(bpy.data, "batch_remove", None)):
        raise RuntimeError("This Blender lacks the required safe batch ID removal")

    mapping = {
        "Reference_Terminal": "terminal.glb",
        "Reference_Coast": "coast.glb",
        "Reference_Foliage": "foliage.glb",
        "Reference_GroundCover": "ground_cover.glb",
    }
    scope = ["Reference_Terminal"] if terminal_only else list(mapping)
    out = root / "assets/reference"
    before = json.loads((log / "objects_before.json").read_text(encoding="utf-8"))
    manifest = json.loads((log / "before_manifest.json").read_text(encoding="utf-8"))
    expected = {
        Path(row["relative"]).name: row["sha256"]
        for row in manifest
        if Path(row["relative"]).parent.as_posix() == "assets/reference"
    }
    last_path = log / "export_last_completed.json"
    previous = json.loads(last_path.read_text(encoding="utf-8")) if last_path.exists() else None
    if previous:
        if previous.get("status") != "completed" or not previous.get("source_saved"):
            raise RuntimeError("Previous completed-export record is inconsistent")
        if Path(previous["source"]) != source_path:
            raise RuntimeError("Previous export belongs to another source")
        expected.update(previous["runtime_asset_hashes"])
    elif terminal_only or changed_only:
        raise RuntimeError("Scoped export requires a completed full first export")
    for filename, digest in expected.items():
        if _tn25_sha(out / filename) != digest:
            raise RuntimeError("Runtime asset changed outside the recorded export: " + filename)
    if not previous and (out / "terminal.glb").exists():
        raise RuntimeError("Unrecorded terminal.glb exists; refusing to overwrite it")

    protected_files = {
        row["relative"]: row["sha256"] for row in manifest
        if Path(row["relative"]).suffix == ".glb"
        and Path(row["relative"]).name not in {*mapping.values(), "terrain.glb"}
    }
    required_fixed = {
        "town.glb", "cargo_port.glb", "boat.glb", "cargo_ginseng.glb",
        "cargo_jade.glb", "cargo_nutmeg.glb", "cargo_silk.glb", "ocean.glb",
        "ground_rock.glb", "rocks.glb",
    }
    if {Path(p).name for p in protected_files} != required_fixed:
        raise RuntimeError("The ten protected runtime GLBs are not fully represented")

    def check_protected_files():
        for relative, digest in protected_files.items():
            if _tn25_sha(root / relative) != digest:
                raise RuntimeError("Protected runtime asset changed: " + relative)

    protected_rows = [row for row in before
                      if row["collection"] not in mapping
                      and row["name"] != "C25_ContourBuiltCoast"]
    original_town = {row["name"] for row in before if row["collection"] == "Reference_Town"}

    def check_protected_objects():
        results = {"objects": 0, "town_objects": len(original_town), "town_floors": []}
        current_town = {obj.name for obj in bpy.data.collections["Reference_Town"].objects
                        if obj.type == "MESH"}
        if current_town != original_town:
            raise RuntimeError("Current-town source object set changed")
        for row in protected_rows:
            obj = bpy.data.objects.get(row["name"])
            if obj is None or row["collection"] not in {c.name for c in obj.users_collection}:
                raise RuntimeError("Protected source object missing or moved: " + row["name"])
            if _tn25_digest(obj) != row["digest"]:
                raise RuntimeError("Protected source geometry/UV/material/pose changed: " + row["name"])
            results["objects"] += 1
            if row["collection"] == "Reference_Town" and row["name"].startswith("Town_Floor"):
                results["town_floors"].append(row["name"])
        if len(results["town_floors"]) != 9:
            raise RuntimeError("Expected nine unchanged current-town floor meshes")
        return results

    check_protected_files()
    protected_before = check_protected_objects()
    for cname in scope:
        if bpy.data.collections.get(cname) is None:
            raise RuntimeError("Missing export collection: " + cname)
    if not (log / "site.json").exists():
        raise RuntimeError("Current terminal site pass has not completed")
    terrain = bpy.data.objects["C25_ContourBuiltCoast"]
    if terrain.mode != "OBJECT" or any(m.show_viewport for m in terrain.modifiers):
        raise RuntimeError("Terrain must be the raw unmodified object mesh")
    if not np.array_equal(np.asarray(terrain.matrix_world), np.eye(4)):
        raise RuntimeError("Terrain transform is no longer identity")
    mesh = terrain.data
    positions = np.empty((len(mesh.vertices), 3), np.float32)
    mesh.vertices.foreach_get("co", positions.ravel())
    loops = np.empty(len(mesh.loops), np.int32)
    mesh.loops.foreach_get("vertex_index", loops)
    sizes = np.empty(len(mesh.polygons), np.int32)
    mesh.polygons.foreach_get("loop_total", sizes)
    if not np.all(sizes == 3):
        raise RuntimeError("Terrain must contain explicit triangles only")
    terrain_verification = _tn25_verify_terrain(positions, loops, log)
    terrain_digest = terrain_verification["terrain_geometry_sha256"]
    if terminal_only and terrain_digest != previous["terrain_geometry_sha256"]:
        raise RuntimeError("Terrain changed after the full export; terminal-only mode is insufficient")

    def collection_source_digest(cname):
        digest = hashlib.sha256()
        for obj in sorted(bpy.data.collections[cname].objects, key=lambda item: item.name):
            if obj.type == "MESH":
                digest.update(obj.name.encode())
                digest.update(_tn25_digest(obj).encode())
        return digest.hexdigest()

    ancillary_source_hashes = {cname: collection_source_digest(cname)
                               for cname in mapping if cname != "Reference_Terminal"}
    if terminal_only and ancillary_source_hashes != previous.get("ancillary_source_hashes"):
        raise RuntimeError("A skipped source collection changed; use a full export")
    export_terrain = not terminal_only
    if changed_only:
        previous_ancillary = previous.get("ancillary_source_hashes", {})
        if set(previous_ancillary) != set(ancillary_source_hashes):
            raise RuntimeError("Previous export lacks the ancillary source hash baseline")
        scope = ["Reference_Terminal"] + [cname for cname in mapping
                 if cname != "Reference_Terminal"
                 and ancillary_source_hashes[cname] != previous_ancillary[cname]]
        export_terrain = terrain_digest != previous["terrain_geometry_sha256"]

    started = time.perf_counter()
    run_dir = log / ("export_stage_" + time.strftime("%Y%m%d_%H%M%S") + "_" + str(time.time_ns() % 1000000))
    run_dir.mkdir()
    report = {
        "status": "running", "pid": os.getpid(), "port": session["port"],
        "source": str(source_path), "terminal_only": bool(terminal_only),
        "changed_only": bool(changed_only), "requested_collections": list(scope),
        "terrain_export_requested": export_terrain,
        "source_saved": False, "visual_accepted": False, "exported": [],
        "collections": {}, "stages": [], "stage_directory": str(run_dir),
        **terrain_verification,
        "ancillary_source_hashes": ancillary_source_hashes,
        "protected_objects_before": protected_before,
    }

    def write_json(path, data):
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(path)

    def progress(phase, collection=None, **detail):
        event = {"phase": phase, "collection": collection,
                 "elapsed_seconds": time.perf_counter() - started, "time_unix": time.time(), **detail}
        report["current_stage"] = event
        if not detail.get("heartbeat"):
            report["stages"].append(event)
        write_json(log / "export_progress.json", {
            "status": report["status"], "pid": os.getpid(), "source": str(source_path),
            "terminal_only": bool(terminal_only), "changed_only": bool(changed_only),
            "requested_collections": list(scope), "terrain_export_requested": export_terrain,
            "current_stage": event,
            "stages": report["stages"], "exported": report["exported"],
            "source_saved": report["source_saved"],
        })

    selected_names = [obj.name for obj in bpy.context.selected_objects]
    active_name = bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None
    affected = {obj.name: obj for cname in scope for obj in bpy.data.collections[cname].objects}
    affected[terrain.name] = terrain
    hide_flags = {name: (obj.hide_get(), obj.hide_viewport) for name, obj in affected.items()}
    collection_flags = {cname: bpy.data.collections[cname].hide_viewport for cname in scope}
    temporary_name = "TN25_EXPORT_TEMP"
    if bpy.data.collections.get(temporary_name):
        raise RuntimeError("An earlier temporary export collection still exists")
    preview_socket = None
    principled = None
    land_material = None
    staged = []
    committed = []
    rollback_rows = []
    source_complete = False

    def export_selected(path):
        opts = dict(filepath=str(path), export_format="GLB", use_selection=True,
                    export_apply=True, export_yup=True, export_texcoords=True,
                    export_normals=True, export_materials="EXPORT")
        rna = bpy.ops.export_scene.gltf.get_rna_type().properties
        if "export_all_uvs" in rna:
            opts["export_all_uvs"] = True
        if "export_vertex_color" in rna:
            opts["export_vertex_color"] = "ACTIVE"
        result = bpy.ops.export_scene.gltf(**opts)
        if "FINISHED" not in result or not path.is_file() or path.stat().st_size < 100:
            raise RuntimeError("GLB exporter did not finish: " + str(path))
        with path.open("rb") as stream:
            if stream.read(4) != b"glTF":
                raise RuntimeError("Exported file lacks the GLB header")

    def export_collection(cname, path):
        source = bpy.data.collections[cname]
        source.hide_viewport = False
        source_objects = [obj for obj in source.objects if obj.type == "MESH"]
        for obj in source_objects:
            obj.hide_viewport = False
            obj.hide_set(False)
        progress("evaluate_source", cname, source_objects=len(source_objects))
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = [(obj, obj.evaluated_get(depsgraph), obj.matrix_world.copy()) for obj in source_objects]
        created_mesh_ids = {}
        snapshots = []
        groups = {}
        temp_collection = None
        result_objects = []
        timings = {}
        tick = time.perf_counter()
        try:
            progress("snapshot_evaluated_meshes", cname, total=len(evaluated))
            # Snapshot EVERY evaluated mesh before linking any new scene object.
            for index, (obj, evaluated_obj, matrix) in enumerate(evaluated):
                data = bpy.data.meshes.new_from_object(evaluated_obj,
                            preserve_all_data_layers=True, depsgraph=depsgraph)
                created_mesh_ids[data.name] = data.as_pointer()
                category = "Terminal" if cname == "Reference_Terminal" else (
                    "Leaf" if any(word in obj.name for word in ("Crown", "Frond", "Tuft", "Coconut")) else "Solid")
                key = (category, tuple(mat.name if mat else "None" for mat in data.materials))
                snapshots.append((obj.name, data, matrix, key))
                if (index + 1) % 100 == 0:
                    progress("snapshot_evaluated_meshes", cname, completed=index + 1,
                             total=len(evaluated), heartbeat=True)
            timings["snapshot_seconds"] = time.perf_counter() - tick
            evaluated.clear()
            depsgraph = None
            progress("link_export_copies", cname, total=len(snapshots))
            tick = time.perf_counter()
            temp_collection = bpy.data.collections.new(temporary_name)
            bpy.context.scene.collection.children.link(temp_collection)
            for name, data, matrix, key in snapshots:
                copy = bpy.data.objects.new(name + "_tn25_export", data)
                temp_collection.objects.link(copy)
                copy.matrix_world = matrix
                groups.setdefault(key, []).append(copy)
            if not groups:
                raise RuntimeError("No meshes in export collection: " + cname)
            bpy.context.view_layer.update()
            timings["link_seconds"] = time.perf_counter() - tick
            progress("join_material_groups", cname, total=len(groups))
            tick = time.perf_counter()
            for index, ((category, materials), objects) in enumerate(groups.items()):
                bpy.ops.object.select_all(action="DESELECT")
                for obj in objects:
                    obj.select_set(True)
                bpy.context.view_layer.objects.active = objects[0]
                if len(objects) > 1:
                    bpy.ops.object.join()
                joined = objects[0]
                joined.name = category + "_" + (materials[0] if materials else "Untextured")
                result_objects.append(joined)
                progress("join_material_groups", cname, completed=index + 1,
                         total=len(groups), heartbeat=True)
            timings["join_seconds"] = time.perf_counter() - tick
            bpy.ops.object.select_all(action="DESELECT")
            for obj in result_objects:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = result_objects[0]
            triangles = sum(sum(len(face.vertices) - 2 for face in obj.data.polygons) for obj in result_objects)
            progress("write_glb", cname, triangles=triangles, material_groups=len(result_objects))
            tick = time.perf_counter()
            export_selected(path)
            timings["glb_seconds"] = time.perf_counter() - tick
            return {"source_mesh_objects": len(source_objects), "export_mesh_groups": len(result_objects),
                    "evaluated_triangles": triangles, "timings": timings}
        finally:
            progress("cleanup_export_copies", cname, allocated_meshes=len(created_mesh_ids))
            tick = time.perf_counter()
            temporary_objects = list(temp_collection.objects) if temp_collection is not None else []
            users = {}
            for obj in temporary_objects:
                if obj.type != "MESH" or created_mesh_ids.get(obj.data.name) != obj.data.as_pointer():
                    raise RuntimeError("Unexpected source data in export temporary collection")
                pointer = obj.data.as_pointer()
                users[pointer] = users.get(pointer, 0) + 1
            meshes_to_remove = []
            for name, pointer in created_mesh_ids.items():
                data = bpy.data.meshes.get(name)
                if data is None:
                    continue
                if data.as_pointer() != pointer or data.users != users.get(pointer, 0):
                    raise RuntimeError("Temporary mesh identity/users changed; refusing removal: " + name)
                meshes_to_remove.append(data)
            ids = [*temporary_objects, *meshes_to_remove]
            if temp_collection is not None:
                ids.append(temp_collection)
            if ids:
                bpy.data.batch_remove(ids=ids)
            if bpy.data.collections.get(temporary_name) or any(bpy.data.meshes.get(name) for name in created_mesh_ids):
                raise RuntimeError("Temporary IDs remain after export cleanup")
            timings["cleanup_seconds"] = time.perf_counter() - tick
            timings["cleanup_meshes"] = len(meshes_to_remove)
            source.hide_viewport = collection_flags[cname]
            for obj in source_objects:
                hidden, viewport_hidden = hide_flags[obj.name]
                obj.hide_viewport = viewport_hidden
                obj.hide_set(hidden)
            progress("cleanup_complete", cname, remaining_temporary_ids=0, timings=timings)

    def restore_state():
        if preview_socket is not None:
            land_material.node_tree.links.new(preview_socket, principled.inputs["Base Color"])
        for cname, hidden in collection_flags.items():
            bpy.data.collections[cname].hide_viewport = hidden
        bpy.ops.object.select_all(action="DESELECT")
        for name in selected_names:
            obj = bpy.data.objects.get(name)
            if obj is not None:
                obj.select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects.get(active_name) if active_name else None
        for name, (hidden, viewport_hidden) in hide_flags.items():
            obj = bpy.data.objects.get(name)
            if obj is not None:
                obj.hide_viewport = viewport_hidden
                obj.hide_set(hidden)
        report["source_material_restored"] = preview_socket is None or (
            len(principled.inputs["Base Color"].links) == 1
            and principled.inputs["Base Color"].links[0].from_socket == preview_socket)
        report["temporary_collection_removed"] = bpy.data.collections.get(temporary_name) is None
        report["selection_restored"] = set(selected_names) == {obj.name for obj in bpy.context.selected_objects}
        report["visibility_restored"] = all(
            bpy.data.objects[name].hide_get() == hidden and bpy.data.objects[name].hide_viewport == viewport_hidden
            for name, (hidden, viewport_hidden) in hide_flags.items()) and all(
            bpy.data.collections[cname].hide_viewport == hidden for cname, hidden in collection_flags.items())
        if not all(report[k] for k in ("source_material_restored", "temporary_collection_removed",
                                      "selection_restored", "visibility_restored")):
            raise RuntimeError("Source state did not restore completely")

    try:
        progress("preflight_complete")
        if export_terrain:
            progress("prepare_terrain")
            vertex_positions = positions[loops]
            uv_values = {
                "UVMap": np.column_stack(((vertex_positions[:, 0] - 8) / 26,
                                          (-vertex_positions[:, 1] - 10) / 45)),
                "RockRegion": np.column_stack(((-vertex_positions[:, 1] - 10) / 45,
                                               (vertex_positions[:, 2] - .7) / 4.4)),
                "GroundRegion": np.column_stack(((vertex_positions[:, 0] + 4) / 48,
                                                 (-vertex_positions[:, 1] + 15) / 97)),
            }
            for name, values in uv_values.items():
                layer = mesh.uv_layers.get(name)
                if layer is None:
                    raise RuntimeError("Established terrain UV layer missing: " + name)
                layer.data.foreach_set("uv", values.astype(np.float32).ravel())
            land_material = mesh.materials[0]
            nodes = land_material.node_tree.nodes
            principled = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
            land = nodes.get("G23_LandUse")
            if land is None or not land.image or len(principled.inputs["Base Color"].links) != 1:
                raise RuntimeError("Unexpected current terrain source preview material")
            preview_socket = principled.inputs["Base Color"].links[0].from_socket
            land_material.node_tree.links.new(land.outputs["Color"], principled.inputs["Base Color"])
            bpy.ops.object.select_all(action="DESELECT")
            terrain.hide_viewport = False
            terrain.hide_set(False)
            terrain.select_set(True)
            bpy.context.view_layer.objects.active = terrain
            path = run_dir / "terrain.glb"
            progress("write_terrain_glb")
            export_selected(path)
            staged.append((path, out / path.name))
            land_material.node_tree.links.new(preview_socket, principled.inputs["Base Color"])
            bvh = BVHTree.FromPolygons(positions.tolist(), loops.reshape(-1, 3).tolist(), all_triangles=True)
            values = []
            top = float(positions[:, 2].max() + 50)
            reach = top - float(positions[:, 2].min()) + 50
            progress("sample_height_cache", total_rows=481)
            for row, z in enumerate(np.arange(-30, 90.001, .25)):
                q = float(np.clip((z + 18.7) / (-26 + 18.7), 0, 1))
                shore = 7.8 + 1.45 * math.sin(z * .12) + .48 * math.sin(z * .29) - 21 * q * q * (3 - 2 * q)
                for distance in np.arange(-20, 50.001, .25):
                    hit = bvh.ray_cast(Vector((float(shore + distance), float(-z), top)),
                                       Vector((0, 0, -1)), reach)[0]
                    values.append(round(float(hit.z) if hit is not None else -15., 5))
                if (row + 1) % 40 == 0:
                    progress("sample_height_cache", completed_rows=row + 1, total_rows=481, heartbeat=True)
            if len(values) != 281 * 481 or not np.all(np.isfinite(values)):
                raise RuntimeError("Invalid terrain height cache")
            path = run_dir / "shore_relief_height.json"
            path.write_text(json.dumps({"d0": -20, "z0": -30, "step": .25, "columns": 281,
                                        "rows": 481, "heights": values}), encoding="utf-8")
            staged.append((path, out / path.name))
            report["height_values"] = len(values)
        for cname in scope:
            path = run_dir / mapping[cname]
            report["collections"][cname] = export_collection(cname, path)
            staged.append((path, out / path.name))
        # Nothing reaches runtime before every requested export is staged and
        # source cleanup/protected-object checks have succeeded.
        restore_state()
        source_complete = True
        check_protected_files()
        report["protected_objects_after"] = check_protected_objects()
        for filename, digest in expected.items():
            if _tn25_sha(out / filename) != digest:
                raise RuntimeError("Runtime changed while staging: " + filename)
        report["staged_files"] = [{"file": dest.name, "sha256": _tn25_sha(path),
                                   "bytes": path.stat().st_size} for path, dest in staged]
        rollback_dir = run_dir / "runtime_before_commit"
        rollback_dir.mkdir()
        for path, destination in staged:
            backup = rollback_dir / destination.name
            existed = destination.exists()
            if existed:
                shutil.copy2(destination, backup)
            rollback_rows.append((destination, backup, existed))
        progress("all_assets_staged", files=[dest.name for _, dest in staged])
        for path, destination in staged:
            progress("commit_staged_asset", file=destination.name)
            path.replace(destination)
            committed.append(destination)
            report["exported"].append({"file": destination.name, "sha256": _tn25_sha(destination),
                                       "bytes": destination.stat().st_size})
        check_protected_files()
        written_names = {destination.name for _, destination in staged}
        for filename, digest in expected.items():
            if filename not in written_names and _tn25_sha(out / filename) != digest:
                raise RuntimeError("Skipped runtime asset changed during export: " + filename)
        report["skipped_runtime_assets_preserved"] = sorted(set(expected) - written_names)
        report["preserved_asset_count"] = len(protected_files)
        report["preserved_assets_match"] = True
        report["runtime_asset_hashes"] = {path.name: _tn25_sha(path)
                                           for path in sorted(out.glob("*.glb"))}
        report["runtime_asset_hashes"]["shore_relief_height.json"] = _tn25_sha(out / "shore_relief_height.json")
        progress("save_source")
        saved = bpy.ops.wm.save_as_mainfile(filepath=str(source_path))
        if "FINISHED" not in saved or bpy.data.is_dirty:
            raise RuntimeError("Source save did not complete cleanly")
        report.update(status="completed", source_saved=True, dirty=bool(bpy.data.is_dirty),
                      source_sha256=_tn25_sha(source_path))
        report["elapsed_seconds"] = time.perf_counter() - started
        progress("completed")
        write_json(last_path, report)
        write_json(log / "export.json", report)
        write_json(run_dir / "export.json", report)
        print(json.dumps({key: value for key, value in report.items()
                          if key not in ("stages", "collections", "runtime_asset_hashes")}, ensure_ascii=False))
        return report
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = type(exc).__name__ + ": " + str(exc)
        # A file failure during commit returns the runtime to its exact entry
        # state. A successful saved export is never automatically reversed.
        if committed and not report["source_saved"]:
            for destination, backup, existed in reversed(rollback_rows):
                if destination not in committed:
                    continue
                if existed:
                    shutil.copy2(backup, destination)
                elif destination.is_file():
                    destination.unlink()
            report["runtime_commit_rolled_back"] = True
        progress("failed", error=report["error"])
        raise
    finally:
        if not source_complete:
            try:
                restore_state()
            except Exception as exc:
                report["restore_error"] = type(exc).__name__ + ": " + str(exc)
        report["elapsed_seconds"] = time.perf_counter() - started
        write_json(log / "export.json", report)
        write_json(run_dir / "export.json", report)
