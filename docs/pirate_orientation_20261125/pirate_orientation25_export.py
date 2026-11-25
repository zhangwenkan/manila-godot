"""Definition-only export of the existing rigidly moved PirateIsland through owned MCP.

No source is loaded and no operation runs on import. Call export_pirate_orientation25 with
the verified current PID/port/source and this round's log directory. Required
snapshot files: session_start.json, before_manifest.json (relative, sha256),
objects_before.json (name, digest, collection or collections). Object digests
use the same transform/raw-mesh/UV/material-slot convention as terminal25.
Requires island_local_before.json captured BEFORE this round's transform.
Only pirate_island.glb may change; the other 15 GLBs stay hash-locked.
This is a specialized copy of pirate25_export.py; it does not call old snapshot/build scripts.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import struct
import time
from pathlib import Path

import numpy as np


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def object_digest(obj):
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


def material_state(material):
    """Read-only export-entry/exit signature; it is not a historical snapshot."""
    if not material.use_nodes:
        return {"use_nodes": False, "diffuse_color": list(material.diffuse_color)}
    nodes = []
    for node in material.node_tree.nodes:
        row = {"name": node.name, "type": node.type, "inputs": {}}
        for socket in node.inputs:
            if not hasattr(socket, "default_value"):
                continue
            value = socket.default_value
            if isinstance(value, (str, bool, int, float)):
                row["inputs"][socket.identifier] = value
            else:
                try:
                    row["inputs"][socket.identifier] = list(value)
                except TypeError:
                    row["inputs"][socket.identifier] = str(value)
        if node.type == "TEX_IMAGE" and node.image:
            im = node.image
            row["image"] = {"name": im.name, "path": im.filepath, "colorspace": im.colorspace_settings.name,
                            "packed_sha256": hashlib.sha256(bytes(im.packed_file.data)).hexdigest() if im.packed_file else None}
        nodes.append(row)
    links = sorted((l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier)
                   for l in material.node_tree.links)
    return {"use_nodes": True, "nodes": sorted(nodes, key=lambda row: row["name"]), "links": links}


def glb_summary(path):
    data = Path(path).read_bytes()
    magic, version, total = struct.unpack_from("<4sII", data)
    length, kind = struct.unpack_from("<II", data, 12)
    if magic != b"glTF" or version != 2 or total != len(data) or kind != 0x4E4F534A:
        raise RuntimeError("Invalid staged GLB")
    doc = json.loads(data[20:20 + length])
    count = 0
    for mesh in doc.get("meshes", []):
        for primitive in mesh["primitives"]:
            if primitive.get("mode", 4) != 4:
                raise RuntimeError("Expected triangle primitives")
            accessor = primitive["indices"] if "indices" in primitive else primitive["attributes"]["POSITION"]
            number = doc["accessors"][accessor]["count"]
            if number % 3:
                raise RuntimeError("Triangle accessor has incomplete indices")
            count += number // 3
    images = doc.get("images", [])
    if any("bufferView" not in image for image in images):
        raise RuntimeError("Island GLB has external image dependencies")
    binary_offset = 20 + length
    if binary_offset + 8 > len(data):
        raise RuntimeError("Island GLB has no binary chunk")
    binary_length, binary_kind = struct.unpack_from("<II", data, binary_offset)
    if binary_kind != 0x004E4942 or binary_offset + 8 + binary_length > len(data):
        raise RuntimeError("Island GLB has an invalid binary chunk")
    image_table = []
    for index, image in enumerate(images):
        view = doc["bufferViews"][image["bufferView"]]
        start = binary_offset + 8 + view.get("byteOffset", 0)
        payload = data[start:start + view["byteLength"]]
        image_table.append({"index": index, "name": image.get("name"), "mime_type": image.get("mimeType"),
                            "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})

    def texture_image(info):
        if info is None:
            return None
        texture = doc["textures"][info["index"]]
        image_index = texture.get("source")
        return {"texture_index": info["index"], "image_index": image_index,
                "image_name": images[image_index].get("name") if image_index is not None else None,
                "texcoord": info.get("texCoord", 0)}

    material_table = []
    for index, material in enumerate(doc.get("materials", [])):
        pbr = material.get("pbrMetallicRoughness", {})
        material_table.append({"index": index, "name": material.get("name"),
                               "base_color_factor": pbr.get("baseColorFactor", [1, 1, 1, 1]),
                               "base_color": texture_image(pbr.get("baseColorTexture")),
                               "normal": texture_image(material.get("normalTexture")),
                               "metallic_roughness": texture_image(pbr.get("metallicRoughnessTexture")),
                               "roughness_factor": pbr.get("roughnessFactor", 1),
                               "metallic_factor": pbr.get("metallicFactor", 1),
                               "alpha_mode": material.get("alphaMode", "OPAQUE"),
                               "double_sided": material.get("doubleSided", False)})
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "meshes": len(doc.get("meshes", [])),
            "triangles": count, "materials": len(doc.get("materials", [])), "embedded_images": len(images),
            "animations": len(doc.get("animations", [])), "material_table": material_table, "image_table": image_table}


def source_material_table(objects):
    """Inspect packed images without changing paths, pixels, nodes or materials."""
    materials = {mat.name: mat for obj in objects for mat in obj.data.materials if mat}
    rows = []
    for name, mat in sorted(materials.items()):
        images = []
        for node in mat.node_tree.nodes if mat.use_nodes else []:
            if node.type != "TEX_IMAGE" or node.image is None:
                continue
            im = node.image
            packed = bytes(im.packed_file.data) if im.packed_file else None
            images.append({"node": node.name, "name": im.name, "filepath": im.filepath,
                           "size": list(im.size), "colorspace": im.colorspace_settings.name,
                           "packed_bytes": len(packed) if packed else 0,
                           "packed_sha256": hashlib.sha256(packed).hexdigest() if packed else None})
        rows.append({"name": name, "use_nodes": mat.use_nodes, "images": images})
    missing = [(row["name"], im["name"]) for row in rows for im in row["images"] if not im["packed_bytes"]]
    if missing:
        raise RuntimeError("Island material images must stay packed before export: " + repr(missing))
    return rows


def _invariants_module():
    path = Path(__file__).resolve().with_name("pirate_orientation25_invariants.py")
    spec = importlib.util.spec_from_file_location("pirate_orientation25_invariants", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def export_pirate_orientation25(expected_pid, expected_port, expected_source, log_path,
                                expected_assembly_world):
    import bpy

    source_path = Path(expected_source).resolve()
    root = source_path.parent.parent
    log = Path(log_path).resolve()
    out = root / "assets/reference"
    target = out / "pirate_island.glb"
    collection_name = "Reference_PirateIsland"
    temporary_name = "P25_ORIENTATION_EXPORT_TEMP"
    if bpy.app.background or os.getpid() != expected_pid or Path(bpy.data.filepath).resolve() != source_path:
        raise RuntimeError("Wrong independently owned GUI Blender or source")
    if bpy.types.blendermcp_server.port != expected_port or bpy.context.mode != "OBJECT":
        raise RuntimeError("Wrong MCP port or object mode")
    session = json.loads((log / "session_start.json").read_text(encoding="utf8"))
    if session["pid"] != expected_pid or session["port"] != expected_port or Path(session["source"]).resolve() != source_path:
        raise RuntimeError("This round's source/session snapshot does not match")
    if not callable(getattr(bpy.data, "batch_remove", None)) or bpy.data.collections.get(temporary_name):
        raise RuntimeError("Temporary cleanup unavailable or old temporary collection remains")
    collection = bpy.data.collections[collection_name]
    source_objects = [o for o in collection.all_objects if o.type == "MESH"]
    if not source_objects or any(not o.name.startswith("P25_") for o in source_objects):
        raise RuntimeError("Existing island must retain its P25_ mesh objects")
    before = json.loads((log / "objects_before.json").read_text(encoding="utf8"))
    manifest = json.loads((log / "before_manifest.json").read_text(encoding="utf8"))
    preserved_files = {row["relative"]: row["sha256"] for row in manifest
                       if Path(row["relative"]).suffix.lower() == ".glb" and Path(row["relative"]).name != target.name}
    current_files = {path.relative_to(root).as_posix() for path in out.glob("*.glb") if path != target}
    if set(preserved_files) != current_files:
        raise RuntimeError("The original GLB snapshot is incomplete or the runtime file set changed")
    invariants = _invariants_module()
    island_names = invariants.island_snapshot_names(log)
    expected_pose = np.asarray(expected_assembly_world, np.float64)
    if expected_pose.shape != (4, 4) or not np.isfinite(expected_pose).all():
        raise RuntimeError("A concrete finite expected assembly matrix is required")
    last_path = log / "pirate_export_last_completed.json"
    previous = json.loads(last_path.read_text(encoding="utf8")) if last_path.exists() else None
    original_targets = [row for row in manifest if row["relative"] == target.relative_to(root).as_posix()]
    if len(original_targets) != 1 or not target.is_file():
        raise RuntimeError("This transform round requires a recorded existing island GLB")
    allowed_target_sha = previous["asset"]["sha256"] if previous and previous.get("status") == "completed" else original_targets[0]["sha256"]
    if previous and previous.get("status") != "completed":
        raise RuntimeError("Prior export record is not completed")
    if sha256(target) != allowed_target_sha:
        raise RuntimeError("Existing island GLB differs from this round's baseline/last completed export")
    asset_before = glb_summary(target)

    def preserved_checks():
        for relative, digest in preserved_files.items():
            if sha256(root / relative) != digest:
                raise RuntimeError("Preserved runtime GLB changed: " + relative)
        failures = []
        protected_rows = [row for row in before if row["name"] not in island_names]
        for row in protected_rows:
            obj = bpy.data.objects.get(row["name"])
            memberships = set(row.get("collections", [row.get("collection")])) - {None}
            if obj is None or not memberships <= {c.name for c in obj.users_collection} or object_digest(obj) != row["digest"]:
                failures.append(row["name"])
        if failures:
            raise RuntimeError("Existing source objects changed: " + str(failures[:12]))
        local = invariants.check_island_local(log)
        if not local["passed"]:
            raise RuntimeError("Island local geometry/pose/material invariants changed: " + repr(local))
        actual_pose = np.asarray(bpy.data.objects["P25_Assembly"].matrix_world, np.float64)
        pose_error = float(np.max(np.abs(actual_pose - expected_pose)))
        if pose_error > 1e-5:
            raise RuntimeError("Island root differs from the concrete expected pose")
        return {"old_runtime_glbs": len(preserved_files), "old_source_objects": len(protected_rows),
                "island_local_invariants": local, "expected_assembly_world": expected_pose.tolist(),
                "assembly_max_matrix_error": pose_error}

    protection = preserved_checks()
    used_materials = source_material_table(source_objects)
    (log / "pirate_source_material_table.json").write_text(
        json.dumps(used_materials, ensure_ascii=False, indent=2), encoding="utf8")
    selected = [o.name for o in bpy.context.selected_objects]
    active = bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None
    object_flags = {o.name: (o.hide_get(), o.hide_viewport) for o in source_objects}
    collection_flags = {c.name: c.hide_viewport for c in [collection, *collection.children_recursive]}
    materials = {m.name: m for m in bpy.data.materials if m.use_nodes}
    material_before = {name: material_state(mat) for name, mat in materials.items()}
    started = time.perf_counter()
    stage_dir = log / ("export_stage_" + time.strftime("%Y%m%d_%H%M%S") + "_" + str(time.time_ns() % 1000000))
    stage_dir.mkdir(parents=True)
    stage = stage_dir / target.name
    report = {"status": "running", "source": str(source_path), "pid": expected_pid, "port": expected_port,
              "source_saved": False, "stages": [], "protection": protection, "visual_accepted": False,
              "stage_directory": str(stage_dir), "source_objects": len(source_objects)}
    report["source_material_table"] = used_materials
    snapshots = []
    created_mesh_ids = {}
    temp_collection = None
    committed = False
    source_restored = False
    target_existed = target.exists()
    rollback = stage_dir / "pirate_island_before.glb"

    def write_json(path, value):
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf8")
        temp.replace(path)

    def progress(phase, **details):
        row = {"phase": phase, "elapsed_seconds": time.perf_counter() - started, "time_unix": time.time(), **details}
        report["current_stage"] = row
        if not details.get("heartbeat"):
            report["stages"].append(row)
        write_json(log / "pirate_export_progress.json", report)

    def cleanup():
        nonlocal temp_collection
        objects = list(temp_collection.objects) if temp_collection is not None else []
        expected_users = {}
        for obj in objects:
            if obj.type != "MESH" or created_mesh_ids.get(obj.data.name) != obj.data.as_pointer():
                raise RuntimeError("Temporary export object contains unexpected source data")
            expected_users[obj.data.as_pointer()] = expected_users.get(obj.data.as_pointer(), 0) + 1
        meshes = []
        for name, pointer in created_mesh_ids.items():
            data = bpy.data.meshes.get(name)
            if data is None:
                continue
            if data.as_pointer() != pointer or data.users != expected_users.get(pointer, 0):
                raise RuntimeError("Temporary mesh identity/user mismatch: " + name)
            meshes.append(data)
        ids = [*objects, *meshes] + ([temp_collection] if temp_collection is not None else [])
        if ids:
            bpy.data.batch_remove(ids=ids)
        temp_collection = None
        if bpy.data.collections.get(temporary_name) or any(bpy.data.meshes.get(name) for name in created_mesh_ids):
            raise RuntimeError("Temporary export IDs remain")

    def restore():
        for name, flag in collection_flags.items():
            bpy.data.collections[name].hide_viewport = flag
        bpy.ops.object.select_all(action="DESELECT")
        for name in selected:
            if bpy.data.objects.get(name):
                bpy.data.objects[name].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects.get(active) if active else None
        for name, (hidden, viewport) in object_flags.items():
            bpy.data.objects[name].hide_viewport = viewport
            bpy.data.objects[name].hide_set(hidden)
        after = {name: material_state(bpy.data.materials[name]) for name in materials}
        report["source_materials_restored"] = after == material_before
        report["selection_restored"] = set(selected) == {o.name for o in bpy.context.selected_objects}
        report["visibility_restored"] = all(bpy.data.objects[name].hide_get() == flags[0]
                                              and bpy.data.objects[name].hide_viewport == flags[1]
                                              for name, flags in object_flags.items()) and all(
                                                  bpy.data.collections[name].hide_viewport == flag
                                                  for name, flag in collection_flags.items())
        if not all(report[k] for k in ("source_materials_restored", "selection_restored", "visibility_restored")):
            raise RuntimeError("Export changed source material/UI state")

    try:
        progress("preflight_complete")
        for name in collection_flags:
            bpy.data.collections[name].hide_viewport = False
        for obj in source_objects:
            obj.hide_viewport = False
            obj.hide_set(False)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = [(o, o.evaluated_get(depsgraph), o.matrix_world.copy()) for o in source_objects]
        progress("snapshot_all_evaluated_meshes", total=len(evaluated))
        for index, (obj, evaluated_obj, matrix) in enumerate(evaluated):
            data = bpy.data.meshes.new_from_object(evaluated_obj, preserve_all_data_layers=True, depsgraph=depsgraph)
            created_mesh_ids[data.name] = data.as_pointer()
            key = tuple(m.name if m else "None" for m in data.materials)
            snapshots.append((obj.name, data, matrix, key))
            if (index + 1) % 150 == 0:
                progress("snapshot_all_evaluated_meshes", completed=index + 1, total=len(evaluated), heartbeat=True)
        evaluated.clear()
        depsgraph = None
        progress("link_export_copies")
        temp_collection = bpy.data.collections.new(temporary_name)
        bpy.context.scene.collection.children.link(temp_collection)
        groups = {}
        for name, data, matrix, key in snapshots:
            obj = bpy.data.objects.new(name + "_pirate25_export", data)
            temp_collection.objects.link(obj)
            obj.matrix_world = matrix
            groups.setdefault(key, []).append(obj)
        bpy.context.view_layer.update()
        joined = []
        for index, (key, objects) in enumerate(groups.items()):
            progress("join_material_group", completed=index, total=len(groups), heartbeat=True)
            bpy.ops.object.select_all(action="DESELECT")
            for obj in objects:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = objects[0]
            if len(objects) > 1:
                bpy.ops.object.join()
            objects[0].name = "P25_Export_" + (key[0] if key else "Untextured")
            joined.append(objects[0])
        bpy.ops.object.select_all(action="DESELECT")
        for obj in joined:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = joined[0]
        options = dict(filepath=str(stage), export_format="GLB", use_selection=True, export_apply=True,
                       export_yup=True, export_texcoords=True, export_normals=True, export_materials="EXPORT")
        properties = bpy.ops.export_scene.gltf.get_rna_type().properties
        if "export_all_uvs" in properties:
            options["export_all_uvs"] = True
        if "export_vertex_color" in properties:
            options["export_vertex_color"] = "ACTIVE"
        progress("write_staged_glb")
        result = bpy.ops.export_scene.gltf(**options)
        if "FINISHED" not in result:
            raise RuntimeError("glTF export did not finish")
        report["asset"] = glb_summary(stage)
        unchanged_counts = ("meshes", "triangles", "materials", "embedded_images", "animations")
        for key in unchanged_counts:
            if report["asset"][key] != asset_before[key]:
                raise RuntimeError("Rigid-transform export changed GLB count: " + key)
        def image_payloads(summary):
            return sorted((row["name"] or "", row["mime_type"] or "", row["sha256"]) for row in summary["image_table"])
        if image_payloads(report["asset"]) != image_payloads(asset_before):
            raise RuntimeError("Rigid-transform export changed embedded image payloads")
        def semantic_materials(summary):
            rows = []
            for row in summary["material_table"]:
                row = dict(row)
                row.pop("index", None)
                for key in ("base_color", "normal", "metallic_roughness"):
                    if row[key] is not None:
                        row[key] = {k: v for k, v in row[key].items() if k not in ("texture_index", "image_index")}
                rows.append(row)
            return sorted(rows, key=lambda row: row["name"] or "")
        if semantic_materials(report["asset"]) != semantic_materials(asset_before):
            raise RuntimeError("Rigid-transform export changed GLB material semantics")
        report["rigid_export_preserved_counts_and_textures"] = True
        expected_materials = {row["name"] for row in used_materials}
        staged_materials = {row["name"] for row in report["asset"]["material_table"]}
        if staged_materials != expected_materials:
            raise RuntimeError("Staged GLB material names differ from island material slots")
        write_json(log / "pirate_staged_material_table.json", report["asset"])
        progress("cleanup_temporary_ids")
        cleanup()
        report["temporary_ids_removed"] = True
        restore()
        source_restored = True
        report["protection_after"] = preserved_checks()
        if target_existed:
            shutil.copy2(target, rollback)
        progress("commit_single_asset")
        stage.replace(target)
        committed = True
        # Only the new target is replaced here. The full old object/file check
        # immediately above already covers the completed export and cleanup.
        progress("save_source")
        result = bpy.ops.wm.save_as_mainfile(filepath=str(source_path))
        if "FINISHED" not in result or bpy.data.is_dirty:
            raise RuntimeError("Source did not save cleanly")
        report.update(status="completed", source_saved=True, dirty=False, source_sha256=sha256(source_path))
        report["asset"] = glb_summary(target)
        progress("completed")
        write_json(last_path, report)
        return report
    except Exception as exc:
        report.update(status="failed", error=type(exc).__name__ + ": " + str(exc))
        if committed and not report["source_saved"]:
            if target_existed:
                shutil.copy2(rollback, target)
            elif target.exists():
                target.unlink()
            report["runtime_commit_rolled_back"] = True
        raise
    finally:
        if not source_restored:
            try:
                cleanup()
                restore()
            except Exception as exc:
                report["cleanup_restore_error"] = type(exc).__name__ + ": " + str(exc)
        report["elapsed_seconds"] = time.perf_counter() - started
        write_json(log / "pirate_export.json", report)
        write_json(stage_dir / "pirate_export.json", report)
        print(json.dumps({k: report.get(k) for k in ("status", "source", "source_sha256", "dirty", "asset", "protection_after", "error", "cleanup_restore_error")}, ensure_ascii=False))
