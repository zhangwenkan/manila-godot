"""Definition-only exporter for the owned November 26 shipyard integration.

Call export_shipyard26 from the verified GUI Blender MCP session. Importing this
module never opens a source, builds geometry, exports an asset, or saves Blender.
The copy/join/stage/restore flow follows terminal25_06_export.py. Small read-only
hash/material/GLB helpers come from pirate25_export.py, not its export entry point.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import shutil
import struct
import time
from pathlib import Path

import numpy as np


TARGETS = {
    "Reference_Shipyard": "shipyard.glb",
    "Reference_Terrain": "terrain.glb",
    "Reference_Coast": "coast.glb",
    "Reference_Foliage": "foliage.glb",
    "Reference_GroundCover": "ground_cover.glb",
    "Reference_Rocks": "rocks.glb",
}
TERRAIN_NAME = "C25_ContourBuiltCoast"
HEIGHT_NAME = "shore_relief_height.json"
TEMP_NAME = "Y26_EXPORT_TEMP"


def _common(root):
    path = root.parent.parent / "docs/pirate_island_20261125/pirate25_export.py"
    spec = importlib.util.spec_from_file_location("shipyard26_export_common", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf8")
    temporary.replace(path)


def _restore_staged_material_names(path, aliases):
    """Keep Godot's established material-name binding; leave BIN bytes intact."""
    if not aliases:
        return
    payload = path.read_bytes()
    magic, version, total, length, kind = struct.unpack_from("<4sIIII", payload)
    if magic != b"glTF" or version != 2 or total != len(payload) or kind != 0x4E4F534A:
        raise RuntimeError("Invalid GLB while restoring temporary material aliases")
    document = json.loads(payload[20:20 + length])
    used = set()
    for material in document.get("materials", []):
        name = material.get("name")
        if name in aliases:
            material["name"] = aliases[name]
            used.add(name)
    if used != set(aliases):
        raise RuntimeError("Temporary terrain material alias was not exported")
    encoded = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf8")
    encoded += b" " * ((-len(encoded)) % 4)
    rest = payload[20 + length:]
    path.write_bytes(struct.pack("<4sIIII", b"glTF", 2, 20 + len(encoded) + len(rest), len(encoded), kind) + encoded + rest)


def export_shipyard26(expected_pid, expected_port, expected_source, log_path,
                     targets, allowed_changed_names):
    """Export an explicit collection subset; changed names are old snapshot names.

    Supply the cumulative actual old-object changes recorded by this round's
    mutation report. Appended shipyard objects are new and need not be listed.
    Selecting Reference_Terrain also writes the established height-query cache.
    All requested files stage before any runtime replacement. Source materials,
    UVs, meshes, selection and visibility are restored before a clean source save.
    """
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    source_path = Path(expected_source).resolve()
    root = source_path.parent.parent
    log = Path(log_path).resolve()
    out = root / "assets/reference"
    if bpy.app.background or os.getpid() != expected_pid or Path(bpy.data.filepath).resolve() != source_path:
        raise RuntimeError("Wrong independently owned GUI Blender or source")
    if bpy.types.blendermcp_server.port != expected_port or bpy.context.mode != "OBJECT":
        raise RuntimeError("Wrong MCP port or object mode")
    session = json.loads((log / "session_start.json").read_text(encoding="utf8"))
    if session["pid"] != expected_pid or session["port"] != expected_port or Path(session["source"]).resolve() != source_path:
        raise RuntimeError("This round's session does not match the current GUI/source")
    if not callable(getattr(bpy.data, "batch_remove", None)) or bpy.data.collections.get(TEMP_NAME):
        raise RuntimeError("Temporary cleanup unavailable or earlier temporary collection remains")
    scope = list(dict.fromkeys(targets))
    if not scope or set(scope) - set(TARGETS):
        raise ValueError("targets must be a nonempty explicit subset of TARGETS collection names")
    common = _common(root)
    before = json.loads((log / "objects_before.json").read_text(encoding="utf8"))
    manifest = json.loads((log / "before_manifest.json").read_text(encoding="utf8"))
    known = {row["name"]: row for row in before}
    allowed = set(allowed_changed_names)
    if allowed - set(known):
        raise ValueError("Allowed changes must name old snapshotted objects: " + repr(sorted(allowed - set(known))[:12]))
    expected = {Path(row["relative"]).name: row["sha256"] for row in manifest
                if Path(row["relative"]).parent.as_posix() == "assets/reference"
                and (Path(row["relative"]).suffix.lower() == ".glb" or Path(row["relative"]).name == HEIGHT_NAME)}
    last_path = log / "shipyard_export_last_completed.json"
    previous = json.loads(last_path.read_text(encoding="utf8")) if last_path.exists() else None
    if previous:
        if previous.get("status") != "completed" or not previous.get("source_saved") or Path(previous["source"]).resolve() != source_path:
            raise RuntimeError("Previous completed-export record is inconsistent")
        expected.update(previous["runtime_asset_hashes"])
    if not previous and "Reference_Shipyard" not in scope:
        raise RuntimeError("The first export must include the newly appended shipyard")

    def check_runtime(omitted=()):
        skipped = set(omitted)
        current = {path.name for path in out.glob("*.glb")}
        recorded = {name for name in expected if name.endswith(".glb")}
        if current - skipped != recorded - skipped:
            raise RuntimeError("Runtime GLB file set differs from this round's recorded entry state")
        for name, digest in expected.items():
            if name not in skipped and common.sha256(out / name) != digest:
                raise RuntimeError("Runtime asset changed outside the recorded export: " + name)

    def memberships(row):
        return set(row.get("collections", [row.get("collection")])) - {None}

    def check_protected_objects():
        protected = [row for row in before if row["name"] not in allowed]
        failures = []
        for row in protected:
            obj = bpy.data.objects.get(row["name"])
            if obj is None or not memberships(row) <= {c.name for c in obj.users_collection} or common.object_digest(obj) != row["digest"]:
                failures.append(row["name"])
        if failures:
            raise RuntimeError("Undeclared old source object changes: " + repr(failures[:16]))
        return {"old_objects_preserved": len(protected), "declared_old_changes": len(allowed)}

    def source_objects(cname):
        collection = bpy.data.collections.get(cname)
        if collection is None:
            raise RuntimeError("Missing export collection: " + cname)
        if cname == "Reference_Terrain":
            obj = bpy.data.objects.get(TERRAIN_NAME)
            if obj is None or collection.all_objects.get(TERRAIN_NAME) != obj:
                raise RuntimeError("Current C25 terrain is missing from Reference_Terrain")
            return [obj]
        objects = [obj for obj in collection.all_objects
                   if obj.type in {"MESH", "CURVE", "FONT"} and not obj.get("sp13_skip_export", False)]
        if not objects:
            raise RuntimeError("Export collection has no active geometry: " + cname)
        if cname == "Reference_Shipyard" and any(obj.name.startswith("M14 continuous sculpted shore bank") for obj in objects):
            raise RuntimeError("Obsolete shipyard shoreline patch is still in the export collection")
        return objects

    def collection_digest(cname):
        h = hashlib.sha256()
        for obj in sorted(bpy.data.collections[cname].all_objects, key=lambda item: item.name):
            h.update(obj.name.encode())
            h.update(common.object_digest(obj).encode())
        return h.hexdigest()

    check_runtime()
    protection = check_protected_objects()
    collection_hashes = {cname: collection_digest(cname) for cname in TARGETS if bpy.data.collections.get(cname)}
    for cname in set(TARGETS) - set(scope):
        if previous:
            if collection_hashes.get(cname) != previous["collection_source_hashes"].get(cname):
                raise RuntimeError("Skipped source collection changed since its previous export: " + cname)
        else:
            old = {row["name"]: row for row in before if cname in memberships(row)}
            collection = bpy.data.collections.get(cname)
            # objects_before deliberately records direct Reference_* meshes only.
            current = {obj.name: obj for obj in collection.objects if obj.type == "MESH"} if collection else {}
            if set(old) != set(current) or any(common.object_digest(current[name]) != row["digest"] for name, row in old.items()):
                raise RuntimeError("Skipped source collection differs from the round baseline: " + cname)

    objects_by_collection = {cname: source_objects(cname) for cname in scope}
    affected = {obj.name: obj for objects in objects_by_collection.values() for obj in objects}
    source_signatures = {name: common.object_digest(obj) for name, obj in affected.items()}
    used_materials = common.source_material_table(list(affected.values()))
    material_before = {mat.name: common.material_state(mat) for mat in bpy.data.materials}
    selected = [obj.name for obj in bpy.context.selected_objects]
    active = bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None
    object_flags = {name: (obj.hide_get(), obj.hide_viewport) for name, obj in affected.items()}
    collection_flags = {collection.name: collection.hide_viewport for cname in scope
                        for collection in [bpy.data.collections[cname], *bpy.data.collections[cname].children_recursive]}
    started = time.perf_counter()
    stage_dir = log / ("shipyard_export_stage_" + time.strftime("%Y%m%d_%H%M%S") + "_" + str(time.time_ns() % 1000000))
    stage_dir.mkdir()
    report = {"status": "running", "source": str(source_path), "pid": expected_pid, "port": expected_port,
              "source_saved": False, "visual_accepted": False, "targets": scope,
              "allowed_changed_names": sorted(allowed), "protection_before": protection,
              "source_material_table": used_materials, "collection_source_hashes": collection_hashes,
              "stage_directory": str(stage_dir), "collections": {}, "stages": [], "exported": []}
    staged = []
    backups = []
    committed = []
    restored = False

    def progress(phase, **details):
        row = {"phase": phase, "elapsed_seconds": time.perf_counter() - started, "time_unix": time.time(), **details}
        report["current_stage"] = row
        if not details.get("heartbeat"):
            report["stages"].append(row)
        _write_json(log / "shipyard_export_progress.json", {key: value for key, value in report.items()
                                                           if key not in {"source_material_table", "collections"}})

    def restore():
        for name, hidden in collection_flags.items():
            bpy.data.collections[name].hide_viewport = hidden
        bpy.ops.object.select_all(action="DESELECT")
        for name in selected:
            bpy.data.objects[name].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects.get(active) if active else None
        for name, (hidden, viewport) in object_flags.items():
            bpy.data.objects[name].hide_viewport = viewport
            bpy.data.objects[name].hide_set(hidden)
        report["source_materials_restored"] = material_before == {mat.name: common.material_state(mat) for mat in bpy.data.materials}
        report["source_meshes_uvs_restored"] = all(common.object_digest(bpy.data.objects[name]) == digest for name, digest in source_signatures.items())
        report["selection_restored"] = set(selected) == {obj.name for obj in bpy.context.selected_objects}
        report["active_object_restored"] = (bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None) == active
        report["visibility_restored"] = all(bpy.data.objects[name].hide_get() == flags[0]
                                             and bpy.data.objects[name].hide_viewport == flags[1]
                                             for name, flags in object_flags.items()) and all(
                                                 bpy.data.collections[name].hide_viewport == flag for name, flag in collection_flags.items())
        report["temporary_collection_removed"] = bpy.data.collections.get(TEMP_NAME) is None
        checks = ("source_materials_restored", "source_meshes_uvs_restored", "selection_restored",
                  "active_object_restored", "visibility_restored", "temporary_collection_removed")
        if not all(report[key] for key in checks):
            raise RuntimeError("Export source/UI state failed to restore: " + repr([key for key in checks if not report[key]]))

    def export_collection(cname, path):
        objects = objects_by_collection[cname]
        for obj in objects:
            obj.hide_viewport = False
            obj.hide_set(False)
        for collection in [bpy.data.collections[cname], *bpy.data.collections[cname].children_recursive]:
            collection.hide_viewport = False
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = [(obj, obj.evaluated_get(depsgraph), obj.matrix_world.copy()) for obj in objects]
        created_meshes = {}
        created_materials = {}
        material_aliases = {}
        snapshots = []
        temporary = None
        try:
            progress("snapshot_evaluated_meshes", collection=cname, total=len(evaluated))
            # Link no new objects until every source evaluated mesh is copied.
            for index, (obj, evaluated_obj, matrix) in enumerate(evaluated):
                data = bpy.data.meshes.new_from_object(evaluated_obj, preserve_all_data_layers=True, depsgraph=depsgraph)
                created_meshes[data.name] = data.as_pointer()
                if cname == "Reference_Terrain":
                    if any(mod.show_viewport for mod in obj.modifiers) or not np.array_equal(np.asarray(matrix), np.eye(4)):
                        raise RuntimeError("C25 terrain must retain raw geometry and identity transform")
                    p = np.empty((len(data.vertices), 3), np.float32)
                    data.vertices.foreach_get("co", p.ravel())
                    loops = np.empty(len(data.loops), np.int32)
                    data.loops.foreach_get("vertex_index", loops)
                    sizes = np.empty(len(data.polygons), np.int32)
                    data.polygons.foreach_get("loop_total", sizes)
                    if not np.all(sizes == 3) or not np.isfinite(p).all():
                        raise RuntimeError("Current terrain must contain finite explicit triangles")
                    q = p[loops]
                    for name, uv in {"UVMap": np.column_stack(((q[:, 0] - 8) / 26, (-q[:, 1] - 10) / 45)),
                                     "RockRegion": np.column_stack(((-q[:, 1] - 10) / 45, (q[:, 2] - .7) / 4.4)),
                                     "GroundRegion": np.column_stack(((q[:, 0] + 4) / 48, (-q[:, 1] + 15) / 97))}.items():
                        if data.uv_layers.get(name) is None:
                            raise RuntimeError("Established terrain UV layer is missing: " + name)
                        data.uv_layers[name].data.foreach_set("uv", uv.astype(np.float32).ravel())
                    original_material = data.materials[0]
                    material = original_material.copy()
                    material.name = "Y26_Export_" + original_material.name
                    created_materials[material.name] = material.as_pointer()
                    material_aliases[material.name] = original_material.name
                    nodes = material.node_tree.nodes
                    principled = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
                    land = nodes.get("G23_LandUse")
                    if land is None or land.image is None:
                        raise RuntimeError("Current G23_LandUse image is missing")
                    material.node_tree.links.new(land.outputs["Color"], principled.inputs["Base Color"])
                    data.materials[0] = material
                    report["terrain"] = {"vertices": len(p), "triangles": len(sizes), "source_uvs_unchanged": True}
                    stage_height_cache(p, loops.reshape(-1, 3))
                category = "ShipyardCOMBINED" if cname == "Reference_Shipyard" else (
                    "Leaf" if any(token in obj.name for token in ("Crown", "Frond", "Tuft", "Coconut")) else "Solid")
                key = (category, tuple(mat.name if mat else "None" for mat in data.materials))
                snapshots.append((obj.name, data, matrix, key))
                if (index + 1) % 150 == 0:
                    progress("snapshot_evaluated_meshes", collection=cname, completed=index + 1, total=len(evaluated), heartbeat=True)
            evaluated.clear()
            depsgraph = None
            temporary = bpy.data.collections.new(TEMP_NAME)
            bpy.context.scene.collection.children.link(temporary)
            groups = {}
            for name, data, matrix, key in snapshots:
                obj = bpy.data.objects.new(name + "_y26_export", data)
                temporary.objects.link(obj)
                obj.matrix_world = matrix
                groups.setdefault(key, []).append(obj)
            bpy.context.view_layer.update()
            joined = []
            for index, ((category, materials), group) in enumerate(groups.items()):
                bpy.ops.object.select_all(action="DESELECT")
                for obj in group:
                    obj.select_set(True)
                bpy.context.view_layer.objects.active = group[0]
                if len(group) > 1:
                    bpy.ops.object.join()
                group[0].name = category + "_" + (materials[0] if materials else "Untextured")
                joined.append(group[0])
                progress("join_material_group", collection=cname, completed=index + 1, total=len(groups), heartbeat=True)
            bpy.ops.object.select_all(action="DESELECT")
            for obj in joined:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = joined[0]
            options = dict(filepath=str(path), export_format="GLB", use_selection=True, export_apply=True,
                           export_yup=True, export_texcoords=True, export_normals=True, export_materials="EXPORT",
                           export_cameras=False, export_lights=False)
            properties = bpy.ops.export_scene.gltf.get_rna_type().properties
            if "export_all_uvs" in properties:
                options["export_all_uvs"] = True
            if "export_vertex_color" in properties:
                options["export_vertex_color"] = "ACTIVE"
            if "export_tangents" in properties:
                options["export_tangents"] = True
            progress("write_staged_glb", collection=cname)
            result = bpy.ops.export_scene.gltf(**options)
            if "FINISHED" not in result:
                raise RuntimeError("glTF export did not finish: " + cname)
            _restore_staged_material_names(path, material_aliases)
            summary = common.glb_summary(path)
            if not summary["triangles"] or summary["animations"]:
                raise RuntimeError("Expected a nonempty static GLB: " + cname)
            return {"source_objects": len(objects), "export_mesh_groups": len(joined), "asset": summary}
        finally:
            progress("cleanup_export_copies", collection=cname)
            temp_objects = list(temporary.objects) if temporary is not None else []
            users = {}
            for obj in temp_objects:
                if obj.type != "MESH" or created_meshes.get(obj.data.name) != obj.data.as_pointer():
                    raise RuntimeError("Unexpected source data in temporary export collection")
                users[obj.data.as_pointer()] = users.get(obj.data.as_pointer(), 0) + 1
            meshes = []
            for name, pointer in created_meshes.items():
                data = bpy.data.meshes.get(name)
                if data is None:
                    continue
                if data.as_pointer() != pointer or data.users != users.get(pointer, 0):
                    raise RuntimeError("Temporary mesh identity/users changed: " + name)
                meshes.append(data)
            ids = [*temp_objects, *meshes] + ([temporary] if temporary is not None else [])
            if ids:
                bpy.data.batch_remove(ids=ids)
            for name, pointer in created_materials.items():
                material = bpy.data.materials.get(name)
                if material is not None:
                    if material.as_pointer() != pointer or material.users:
                        raise RuntimeError("Temporary material has an unexpected identity/user: " + name)
                    bpy.data.materials.remove(material)
            if bpy.data.collections.get(TEMP_NAME) or any(bpy.data.meshes.get(name) for name in created_meshes):
                raise RuntimeError("Temporary export IDs remain")

    def stage_height_cache(positions, triangles):
        bvh = BVHTree.FromPolygons(positions.tolist(), triangles.tolist(), all_triangles=True)
        top = float(positions[:, 2].max() + 50)
        reach = top - float(positions[:, 2].min()) + 50
        values = []
        progress("sample_actual_terrain_height", total_rows=481)
        for row, z in enumerate(np.arange(-30, 90.001, .25)):
            q = float(np.clip((z + 18.7) / (-26 + 18.7), 0, 1))
            shore = 7.8 + 1.45 * math.sin(z * .12) + .48 * math.sin(z * .29) - 21 * q * q * (3 - 2 * q)
            for distance in np.arange(-20, 50.001, .25):
                hit = bvh.ray_cast(Vector((float(shore + distance), float(-z), top)), Vector((0, 0, -1)), reach)[0]
                values.append(round(float(hit.z) if hit is not None else -15., 5))
            if (row + 1) % 60 == 0:
                progress("sample_actual_terrain_height", completed_rows=row + 1, total_rows=481, heartbeat=True)
        if len(values) != 281 * 481 or not np.isfinite(values).all():
            raise RuntimeError("Invalid terrain height-query cache")
        path = stage_dir / HEIGHT_NAME
        path.write_text(json.dumps({"d0": -20, "z0": -30, "step": .25, "columns": 281,
                                    "rows": 481, "heights": values}), encoding="utf8")
        staged.append((path, out / HEIGHT_NAME))
        report["height_values"] = len(values)

    try:
        progress("preflight_complete")
        for cname in scope:
            path = stage_dir / TARGETS[cname]
            report["collections"][cname] = export_collection(cname, path)
            staged.append((path, out / path.name))
        restore()
        restored = True
        report["protection_after"] = check_protected_objects()
        check_runtime()
        rollback_dir = stage_dir / "runtime_before_commit"
        rollback_dir.mkdir()
        for path, destination in staged:
            backup = rollback_dir / destination.name
            existed = destination.exists()
            if existed:
                shutil.copy2(destination, backup)
            backups.append((destination, backup, existed))
        progress("all_assets_staged", files=[destination.name for _, destination in staged])
        for path, destination in staged:
            path.replace(destination)
            committed.append(destination)
            report["exported"].append({"file": destination.name, "sha256": common.sha256(destination), "bytes": destination.stat().st_size})
        written = {destination.name for destination in committed}
        check_runtime(omitted=written)
        report["preserved_runtime_glbs"] = sorted(name for name in expected if name.endswith(".glb") and name not in written)
        report["runtime_asset_hashes"] = {path.name: common.sha256(path) for path in sorted(out.glob("*.glb"))}
        report["runtime_asset_hashes"][HEIGHT_NAME] = common.sha256(out / HEIGHT_NAME)
        progress("save_source")
        result = bpy.ops.wm.save_as_mainfile(filepath=str(source_path))
        if "FINISHED" not in result or bpy.data.is_dirty:
            raise RuntimeError("Source did not save cleanly")
        report.update(source_saved=True, dirty=False)
        report.update(status="completed", source_sha256=common.sha256(source_path))
        progress("completed")
        _write_json(last_path, report)
        return report
    except Exception as exc:
        report.update(status="failed", error=type(exc).__name__ + ": " + str(exc))
        if committed and not report["source_saved"]:
            for destination, backup, existed in reversed(backups):
                if destination not in committed:
                    continue
                if existed:
                    shutil.copy2(backup, destination)
                elif destination.exists():
                    destination.unlink()
            report["runtime_commit_rolled_back"] = True
        raise
    finally:
        if not restored:
            try:
                restore()
            except Exception as exc:
                report["restore_error"] = type(exc).__name__ + ": " + str(exc)
        report["elapsed_seconds"] = time.perf_counter() - started
        _write_json(log / "shipyard_export.json", report)
        _write_json(stage_dir / "shipyard_export.json", report)
        print(json.dumps({key: report.get(key) for key in ("status", "source_sha256", "dirty", "targets", "exported", "error", "restore_error")}, ensure_ascii=False))
