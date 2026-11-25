"""Definition-only export of the new lighthouse through the owned GUI MCP.

Requires session_start.json, before_manifest.json, objects_before.json and
materials_before.json. No modeling, snapshot, export or save runs on import.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import time
from pathlib import Path

import numpy as np


def _audit_module(root):
    path = Path(root).parent.parent / "docs/lighthouse_integration_20261126/lighthouse26_audit.py"
    spec = importlib.util.spec_from_file_location("lighthouse26_export_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf8")
    temporary.replace(path)


def export_lighthouse26(expected_pid, expected_port, expected_source, log_path,
                        center_blender=(0, 0, 0), export_space="world", origin_matrix_world=None):
    """Export only lighthouse.glb; preserve new Empty markers and exclude lights.

    Local mode removes center_blender translation. Optional origin_matrix_world
    removes that complete frame instead. World mode bakes existing world poses.
    Blender coordinates are Z-up; glTF/Godot output uses its established Y-up map.
    """
    import bpy
    from mathutils import Matrix, Vector

    root = Path(expected_source).resolve().parent.parent
    audit = _audit_module(root)
    root, source, log = audit.validate_session(expected_pid, expected_port, expected_source, log_path)
    common = audit.common_helpers(root)
    target = root / "assets/reference" / audit.ASSET
    if export_space not in {"local", "world"}:
        raise ValueError("export_space must be local or world")
    center = np.asarray(center_blender, np.float64)
    if center.shape != (3,) or not np.isfinite(center).all():
        raise ValueError("center_blender must be a finite XYZ vector")
    if origin_matrix_world is not None:
        origin = np.asarray(origin_matrix_world, np.float64)
        if export_space != "local" or origin.shape != (4, 4) or not np.isfinite(origin).all() or abs(np.linalg.det(origin)) < 1e-12:
            raise ValueError("A finite invertible origin matrix requires local mode")
        frame = Matrix(origin.tolist()).inverted()
    else:
        frame = Matrix.Translation(-Vector(center.tolist())) if export_space == "local" else Matrix.Identity(4)
    if not callable(getattr(bpy.data, "batch_remove", None)) or bpy.data.collections.get(audit.TEMP):
        raise RuntimeError("Cleanup unavailable or earlier export temporary data remains")
    collection = bpy.data.collections[audit.COLLECTION]
    objects = list(collection.all_objects)
    meshes = [obj for obj in objects if obj.type in {"MESH", "CURVE", "FONT"}]
    empties = [obj for obj in objects if obj.type == "EMPTY"]
    if not meshes:
        raise RuntimeError("Lighthouse collection has no geometry")
    if not audit.REQUIRED_MARKERS <= {obj.name for obj in empties}:
        raise RuntimeError("L26_Assembly and L26_LampEmitter must remain Empty markers")
    protection = audit.protection_checks(root, log, common)
    if not protection["passed"]:
        raise RuntimeError("Pre-export preserved source/runtime check failed: " + repr(protection))
    last_path = log / "lighthouse_export_last_completed.json"
    last = json.loads(last_path.read_text(encoding="utf8")) if last_path.exists() else None
    if target.exists() and (not last or last.get("status") != "completed" or common.sha256(target) != last["glb"]["asset"]["sha256"]):
        raise RuntimeError("Unrecorded or externally changed lighthouse.glb exists")
    if last and not target.exists():
        raise RuntimeError("Previously exported lighthouse.glb is missing")
    source_state = audit.collection_state(collection, common)
    used_materials = common.source_material_table(meshes)
    material_states = {mat.name: audit.export_material_state(mat, common) for obj in meshes for mat in obj.data.materials if mat}
    all_materials_before = {mat.name: audit.export_material_state(mat, common) for mat in bpy.data.materials}
    selected = [obj.name for obj in bpy.context.selected_objects]
    active = bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None
    flags = {obj.name: (obj.hide_get(), obj.hide_viewport, obj.hide_render) for obj in objects}
    collection_flags = {item.name: (item.hide_viewport, item.hide_render) for item in [collection, *collection.children_recursive]}
    marker_matrices = {obj.name: frame @ obj.matrix_world for obj in empties}
    yup = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], np.float64)
    expected_markers = {name: (yup @ np.asarray(matrix) @ yup.T).tolist() for name, matrix in marker_matrices.items()}
    started = time.perf_counter()
    stage_dir = log / ("lighthouse_export_stage_" + time.strftime("%Y%m%d_%H%M%S") + "_" + str(time.time_ns() % 1000000))
    stage_dir.mkdir(parents=True)
    stage = stage_dir / audit.ASSET
    report = {"status": "running", "source": str(source), "pid": expected_pid, "port": expected_port,
              "source_saved": False, "visual_accepted": False, "export_space": export_space,
              "center_blender": center.tolist(), "frame_matrix": [list(row) for row in frame],
              "source_collection_state": source_state, "source_material_states": material_states,
              "source_material_table": used_materials, "expected_markers_gltf": expected_markers,
              "source_geometry_objects": len(meshes), "source_marker_empties": len(empties),
              "excluded_lights": [obj.name for obj in objects if obj.type == "LIGHT"],
              "protection_before": protection, "mesh_checks": [], "stages": []}
    created_meshes, temp_object_pointers = {}, set()
    temporary = None
    snapshots = []
    committed, restored = False, False
    existed = target.exists()
    backup = stage_dir / "lighthouse_before.glb"

    def progress(phase):
        report["stages"].append({"phase": phase, "elapsed_seconds": time.perf_counter() - started})
        _write_json(log / "lighthouse_export_progress.json", {key: report[key] for key in ("status", "source", "stages", "source_saved")})

    def cleanup():
        nonlocal temporary
        current = list(temporary.objects) if temporary is not None else []
        users = {}
        for obj in current:
            if obj.as_pointer() not in temp_object_pointers:
                raise RuntimeError("Unexpected object in temporary export collection")
            if obj.type == "MESH":
                if created_meshes.get(obj.data.name) != obj.data.as_pointer():
                    raise RuntimeError("Source mesh entered temporary export collection")
                users[obj.data.as_pointer()] = users.get(obj.data.as_pointer(), 0) + 1
            elif obj.type != "EMPTY":
                raise RuntimeError("Unexpected temporary object type")
        data_ids = []
        for name, pointer in created_meshes.items():
            data = bpy.data.meshes.get(name)
            if data is not None:
                if data.as_pointer() != pointer or data.users != users.get(pointer, 0):
                    raise RuntimeError("Temporary mesh has unexpected identity/users")
                data_ids.append(data)
        ids = [*current, *data_ids] + ([temporary] if temporary else [])
        if ids:
            bpy.data.batch_remove(ids=ids)
        temporary = None
        if bpy.data.collections.get(audit.TEMP) or any(bpy.data.meshes.get(name) for name in created_meshes):
            raise RuntimeError("Export temporary IDs remain")

    def restore():
        for name, (viewport, render) in collection_flags.items():
            bpy.data.collections[name].hide_viewport = viewport
            bpy.data.collections[name].hide_render = render
        bpy.ops.object.select_all(action="DESELECT")
        for name in selected:
            bpy.data.objects[name].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects.get(active) if active else None
        for name, (hidden, viewport, render) in flags.items():
            obj = bpy.data.objects[name]
            obj.hide_viewport, obj.hide_render = viewport, render
            obj.hide_set(hidden)
        report["source_objects_restored"] = audit.collection_state(collection, common) == source_state
        report["source_materials_restored"] = all_materials_before == {mat.name: audit.export_material_state(mat, common) for mat in bpy.data.materials}
        report["selection_restored"] = set(selected) == {obj.name for obj in bpy.context.selected_objects}
        report["active_restored"] = (bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None) == active
        report["visibility_restored"] = all((bpy.data.objects[name].hide_get(), bpy.data.objects[name].hide_viewport,
                                              bpy.data.objects[name].hide_render) == value for name, value in flags.items()) and all(
            (bpy.data.collections[name].hide_viewport, bpy.data.collections[name].hide_render) == value for name, value in collection_flags.items())
        if not all(report[key] for key in ("source_objects_restored", "source_materials_restored", "selection_restored", "active_restored", "visibility_restored")):
            raise RuntimeError("Source export state did not fully restore")

    try:
        progress("preflight_complete")
        for name in collection_flags:
            bpy.data.collections[name].hide_viewport = False
        for obj in meshes:
            obj.hide_viewport = False
            obj.hide_set(False)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        # Evaluate only new lighthouse objects, snapshot all before scene linking.
        evaluated = [(obj, obj.evaluated_get(depsgraph), frame @ obj.matrix_world) for obj in meshes]
        for obj, evaluated_obj, matrix in evaluated:
            data = bpy.data.meshes.new_from_object(evaluated_obj, preserve_all_data_layers=True, depsgraph=depsgraph)
            created_meshes[data.name] = data.as_pointer()
            check = audit.mesh_check(data, matrix)
            report["mesh_checks"].append({"name": obj.name, **check})
            if not check["passed"]:
                raise RuntimeError("New lighthouse mesh UV/geometry check failed: " + obj.name)
            snapshots.append((obj.name, data, matrix, tuple(mat.name if mat else "None" for mat in data.materials)))
        evaluated.clear()
        depsgraph = None
        progress("new_meshes_snapshotted")
        temporary = bpy.data.collections.new(audit.TEMP)
        bpy.context.scene.collection.children.link(temporary)
        groups = {}
        for name, data, matrix, key in snapshots:
            copy = bpy.data.objects.new(name + "_l26_export", data)
            temporary.objects.link(copy)
            copy.matrix_world = matrix
            temp_object_pointers.add(copy.as_pointer())
            groups.setdefault(key, []).append(copy)
        bpy.context.view_layer.update()
        joined = []
        for key, group in groups.items():
            bpy.ops.object.select_all(action="DESELECT")
            for obj in group:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = group[0]
            if len(group) > 1:
                if "FINISHED" not in bpy.ops.object.join():
                    raise RuntimeError("Temporary lighthouse mesh join did not finish")
            obj = group[0]
            obj.name = "L26_Export_" + (key[0] if key else "Untextured")
            if created_meshes.get(obj.data.name) != obj.data.as_pointer():
                raise RuntimeError("Join replaced the tracked temporary mesh unexpectedly")
            joined_check = audit.mesh_check(obj.data, obj.matrix_world)
            if not joined_check["passed"]:
                raise RuntimeError("Joined lighthouse mesh UV/geometry check failed: " + obj.name)
            joined.append(obj)
        aliases, marker_copies = {}, {}
        for name, matrix in marker_matrices.items():
            copy = bpy.data.objects.new(name + "_l26_marker_export", None)
            temporary.objects.link(copy)
            copy.matrix_world = matrix
            temp_object_pointers.add(copy.as_pointer())
            aliases[copy.name] = name
            marker_copies[name] = copy
            joined.append(copy)
        bpy.context.view_layer.update()
        # Keep the retained Assembly useful as the runtime rigid-transform root.
        # Only temporary copies are parented; every world matrix is preserved.
        assembly_copy = marker_copies["L26_Assembly"]
        for source_marker in empties:
            copy = marker_copies[source_marker.name]
            if copy == assembly_copy:
                continue
            parent = marker_copies.get(source_marker.parent.name) if source_marker.parent else None
            world = copy.matrix_world.copy()
            copy.parent = parent or assembly_copy
            copy.matrix_world = world
        for obj in joined:
            if obj.type == "MESH":
                world = obj.matrix_world.copy()
                obj.parent = assembly_copy
                obj.matrix_world = world
        bpy.context.view_layer.update()
        bpy.ops.object.select_all(action="DESELECT")
        for obj in joined:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = joined[0]
        options = dict(filepath=str(stage), export_format="GLB", use_selection=True, export_apply=True,
                       export_yup=True, export_texcoords=True, export_normals=True, export_materials="EXPORT",
                       export_cameras=False, export_lights=False, export_animations=False)
        properties = bpy.ops.export_scene.gltf.get_rna_type().properties
        for name, value in (("export_all_uvs", True), ("export_vertex_color", "ACTIVE"), ("export_tangents", True)):
            if name in properties:
                options[name] = value
        progress("write_new_asset")
        if "FINISHED" not in bpy.ops.export_scene.gltf(**options):
            raise RuntimeError("Lighthouse GLB export did not finish")
        # Avoid source renames: restore exact marker node names in staged JSON.
        if aliases:
            import struct
            payload, doc, binary_offset = audit.read_glb(stage)
            used = set()
            for node in doc.get("nodes", []):
                name = node.get("name")
                if name in aliases:
                    node["name"] = aliases[name]
                    used.add(name)
            if used != set(aliases):
                raise RuntimeError("An Empty marker was omitted from the GLB")
            encoded = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf8")
            encoded += b" " * ((-len(encoded)) % 4)
            rest = payload[binary_offset:]
            stage.write_bytes(struct.pack("<4sIIII", b"glTF", 2, 20 + len(encoded) + len(rest), len(encoded), 0x4E4F534A) + encoded + rest)
        report["glb"] = audit.glb_checks(stage, common, expected_markers)
        if not report["glb"]["passed"]:
            raise RuntimeError("Staged lighthouse GLB geometry/UV/marker check failed")
        cleanup()
        restore()
        restored = True
        report["protection_after"] = audit.protection_checks(root, log, common)
        if not report["protection_after"]["passed"]:
            raise RuntimeError("Preserved source/runtime changed during export")
        if existed:
            if common.sha256(target) != last["glb"]["asset"]["sha256"]:
                raise RuntimeError("Target changed while staging")
            shutil.copy2(target, backup)
        elif target.exists():
            raise RuntimeError("Target appeared while staging")
        progress("commit_single_asset")
        stage.replace(target)
        committed = True
        progress("save_source")
        if "FINISHED" not in bpy.ops.wm.save_as_mainfile(filepath=str(source)) or bpy.data.is_dirty:
            raise RuntimeError("Source save did not complete cleanly")
        report.update(source_saved=True, dirty=False)
        report.update(status="completed", source_sha256=common.sha256(source))
        progress("completed")
        _write_json(last_path, report)
        return report
    except Exception as exc:
        report.update(status="failed", error=type(exc).__name__ + ": " + str(exc))
        if committed and not report["source_saved"]:
            if existed:
                shutil.copy2(backup, target)
            elif target.exists():
                target.unlink()
            report["target_rolled_back"] = True
        raise
    finally:
        if not restored:
            try:
                cleanup()
            except Exception as exc:
                report["cleanup_error"] = type(exc).__name__ + ": " + str(exc)
            try:
                restore()
            except Exception as exc:
                report["restore_error"] = type(exc).__name__ + ": " + str(exc)
        report["elapsed_seconds"] = time.perf_counter() - started
        _write_json(log / "lighthouse_export.json", report)
        _write_json(stage_dir / "lighthouse_export.json", report)
        print(json.dumps({key: report.get(key) for key in ("status", "source_sha256", "source_saved", "dirty", "error", "cleanup_error", "restore_error")}))
