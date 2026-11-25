"""Read-only final source/packed-image/export verification; owned MCP only."""
import bpy
import hashlib
import json
import os
import struct
from datetime import datetime
from pathlib import Path


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


ROOT = Path(bpy.data.filepath).parent.parent
LOG = ROOT / "captures/terminal_rebuild_20261125"
expected_source = ROOT / "source/harbor_shore_control_mcp.blend"
assert os.getpid() == 13812 and not bpy.app.background
assert bpy.types.blendermcp_server.port == 9881
assert Path(bpy.data.filepath).resolve() == expected_source.resolve()
export = json.loads((LOG / "export.json").read_text(encoding="utf8"))
audit_candidates = sorted(LOG.glob("independent_audit_*.json"))
assert audit_candidates, "No independent source audit available"
audit_name = audit_candidates[-1].name
audit = json.loads((LOG / audit_name).read_text(encoding="utf8"))
checks = []


def check(name, passed, **details):
    checks.append({"name": name, "pass": bool(passed), **details})


dirty_before = bool(bpy.data.is_dirty)
source_sha = sha(expected_source)
check("source_path_pid_port_verified", True, source=str(expected_source), pid=os.getpid(), port=9881)
check("source_clean_and_matches_completed_export", not dirty_before and export.get("status") == "completed"
      and export.get("source_saved") and not export.get("dirty") and source_sha == export.get("source_sha256"),
      dirty=dirty_before, source_sha256=source_sha, export_sha256=export.get("source_sha256"))
check("independent_geometry_audit_passed_clean", audit.get("passed") and not audit.get("failed_checks")
      and not audit.get("source_dirty") and not audit.get("scene_dirty_after")
      and audit.get("pid") == os.getpid() and Path(audit["source"]).resolve() == expected_source.resolve()
      and datetime.fromisoformat(audit["created_local"]).timestamp() >= export["current_stage"]["time_unix"],
      report=audit_name, checks=audit.get("check_count"), warnings=len(audit.get("warnings", [])))

runtime_mismatch = []
for name, expected_hash in export["runtime_asset_hashes"].items():
    actual = sha(ROOT / "assets/reference" / name)
    if actual != expected_hash:
        runtime_mismatch.append({"file": name, "actual": actual, "expected": expected_hash})
check("runtime_assets_match_latest_export", not runtime_mismatch,
      checked=len(export["runtime_asset_hashes"]), failures=runtime_mismatch)

temporary_collections = [c.name for c in bpy.data.collections if c.name.startswith("TN25_EXPORT_TEMP")]
temporary_objects = [o.name for o in bpy.data.objects if "_tn25_export" in o.name or o.name.startswith("TN25_EXPORT_TEMP")]
temporary_meshes = [m.name for m in bpy.data.meshes if "_tn25_export" in m.name or m.name.startswith("TN25_EXPORT_TEMP")]
check("export_temporary_ids_absent", not temporary_collections and not temporary_objects and not temporary_meshes
      and export.get("temporary_collection_removed") is True,
      collections=temporary_collections, objects=temporary_objects, tagged_meshes=temporary_meshes,
      completed_export_verified_allocated_mesh_cleanup=True)

image_reports = []


def inspect_image(image):
    stored_disk = Path(bpy.path.abspath(image.filepath))
    disk = stored_disk
    moved_disk = ROOT / "assets/reference" / stored_disk.name
    if not disk.is_file() and moved_disk.is_file():
        disk = moved_disk
    packed = bytes(image.packed_file.data) if image.packed_file else None
    packed_sha = hashlib.sha256(packed).hexdigest() if packed is not None else None
    disk_sha = sha(disk) if disk.is_file() else None
    row = {"image": image.name, "stored_disk_path": str(stored_disk), "stored_path_exists": stored_disk.is_file(),
           "disk_path": str(disk), "current_project_same_filename_used": disk != stored_disk,
           "packed_bytes": len(packed) if packed is not None else 0,
           "packed_sha256": packed_sha, "disk_sha256": disk_sha,
           "packed_matches_disk": packed is not None and packed_sha == disk_sha,
           "image_dirty": bool(image.is_dirty), "size": list(image.size)}
    image_reports.append(row)
    return row


roof = bpy.data.materials["Ref_TN25_NavyRoof"]
original_blue = bpy.data.materials["Ref_TR20_blue"]
roof_images = {node.image.name: node.image for node in roof.node_tree.nodes if node.type == "TEX_IMAGE" and node.image}
for image in roof_images.values():
    inspect_image(image)
check("roof_packed_images_equal_disk", len(roof_images) == 3 and all(row["packed_matches_disk"] and not row["image_dirty"] for row in image_reports),
      images=image_reports)
roof_bsdf = next(n for n in roof.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
roof_color_links = roof_bsdf.inputs["Base Color"].links
roof_color = roof_color_links[0].from_node.image.name if len(roof_color_links) == 1 and roof_color_links[0].from_node.type == "TEX_IMAGE" else None
check("roof_uses_independent_navy_color", roof != original_blue and roof.node_tree != original_blue.node_tree
      and roof_color == "TN25_NavyRoof_Color", color_image=roof_color)

shared_rows = []
for role in ("plaster", "ivory", "peach", "mint", "stone", "wood", "deck", "beam", "blue", "sage", "red", "teal", "tile", "tile2"):
    name = "Ref_TR20_" + role
    material = bpy.data.materials.get(name)
    if material is None or not material.use_nodes:
        shared_rows.append({"material": name, "pass": False, "reason": "missing material or nodes"})
        continue
    principled = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    color_links = principled.inputs["Base Color"].links
    rough_links = principled.inputs["Roughness"].links
    normal_links = principled.inputs["Normal"].links
    color = color_links[0].from_node.image.name if len(color_links) == 1 and color_links[0].from_node.type == "TEX_IMAGE" else None
    rough = rough_links[0].from_node.image.name if len(rough_links) == 1 and rough_links[0].from_node.type == "TEX_IMAGE" else None
    normal = None
    strength = None
    if len(normal_links) == 1 and normal_links[0].from_node.type == "NORMAL_MAP":
        normal_node = normal_links[0].from_node
        strength = float(normal_node.inputs["Strength"].default_value)
        links = normal_node.inputs["Color"].links
        if len(links) == 1 and links[0].from_node.type == "TEX_IMAGE":
            normal = links[0].from_node.image.name
    expected_strength = .48 if role in ("plaster", "ivory", "peach", "mint", "stone", "wood", "deck", "beam") else .26
    valid = (color == name + "_Albedo" and rough == name + "_Roughness" and normal == name + "_Normal"
             and strength is not None and abs(strength - expected_strength) < 1e-6)
    shared_rows.append({"material": name, "pass": valid, "base_color_image": color,
                        "roughness_image": rough, "normal_image": normal, "normal_strength": strength})
check("shared_current_town_material_links_not_replaced", all(row["pass"] for row in shared_rows), materials=shared_rows,
      scope="Checks current original map links and authored normal strengths; no historical node-content checksum was recorded.")
town_navy_users = [o.name for o in bpy.data.collections["Reference_Town"].objects if o.type == "MESH" and roof in o.data.materials[:]]
check("new_navy_material_not_assigned_to_old_town", not town_navy_users, town_objects=town_navy_users)

terrain_material = bpy.data.objects["C25_ContourBuiltCoast"].data.materials[0]
terrain_bsdf = next(n for n in terrain_material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
terrain_color_links = terrain_bsdf.inputs["Base Color"].links
terrain_sources = [{"node": link.from_node.name, "type": link.from_node.type, "socket": link.from_socket.name} for link in terrain_color_links]
check("terrain_export_preview_link_restored", export.get("source_material_restored") is True
      and len(terrain_color_links) == 1 and terrain_color_links[0].from_node.name != "G23_LandUse", links=terrain_sources)

glb_path = ROOT / "assets/reference/terminal.glb"
data = glb_path.read_bytes()
magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
chunk_length, chunk_type = struct.unpack_from("<II", data, 12)
assert magic == b"glTF" and version == 2 and declared_length == len(data) and chunk_type == 0x4E4F534A
gltf = json.loads(data[20:20+chunk_length])
triangle_count = 0
modes = []
for mesh in gltf.get("meshes", []):
    for primitive in mesh["primitives"]:
        mode = primitive.get("mode", 4)
        modes.append(mode)
        count = gltf["accessors"][primitive["indices"]]["count"] if "indices" in primitive else gltf["accessors"][primitive["attributes"]["POSITION"]]["count"]
        if mode == 4:
            assert count % 3 == 0
            triangle_count += count // 3
glb = {"file": str(glb_path), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
       "meshes": len(gltf.get("meshes", [])), "triangles": triangle_count,
       "materials": len(gltf.get("materials", [])), "images": len(gltf.get("images", [])),
       "embedded_images": sum("bufferView" in im for im in gltf.get("images", [])),
       "nodes": len(gltf.get("nodes", [])), "animations": len(gltf.get("animations", []))}
check("terminal_glb_matches_export_geometry", set(modes) == {4}
      and glb["meshes"] == export["collections"]["Reference_Terminal"]["export_mesh_groups"]
      and triangle_count == export["collections"]["Reference_Terminal"]["evaluated_triangles"], **glb)
check("terminal_glb_images_all_embedded", glb["images"] > 0 and glb["embedded_images"] == glb["images"])
check("read_only_check_kept_source_clean", not bpy.data.is_dirty and sha(expected_source) == source_sha,
      source_dirty_after=bool(bpy.data.is_dirty))
report = {"created_local": datetime.now().astimezone().isoformat(), "read_only": True,
          "source": str(expected_source), "source_sha256": source_sha, "dirty": bool(bpy.data.is_dirty),
          "pid": os.getpid(), "port": 9881, "checks": checks,
          "passed": all(row["pass"] for row in checks), "terminal_glb": glb,
          "failed_checks": [row["name"] for row in checks if not row["pass"]]}
path = LOG / "final_source_check.json"
path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
print(json.dumps({"report": str(path), "passed": report["passed"], "failed_checks": report["failed_checks"],
                  "checks": len(checks), "source_sha256": source_sha, "dirty": report["dirty"], "terminal_glb": glb}, ensure_ascii=False))
