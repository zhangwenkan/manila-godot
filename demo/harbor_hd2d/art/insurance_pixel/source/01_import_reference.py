"""Import the supplied GLB as a protected reference, leaving the live scene intact."""
from pathlib import Path
import sys
import json
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pixel_common import *

verify_input()
fresh(SOURCE / "reference_import.json")
with preserve_session():
    original = {
        "filepath": bpy.data.filepath,
        "scene": bpy.context.scene.name,
        "view_layer": bpy.context.view_layer.name,
        "active": bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
        "selected": [o.name for o in bpy.context.selected_objects],
    }
    scene = independent_scene(REFERENCE_SCENE)
    collection = bpy.data.collections.new("INS7_LockedReference")
    scene.collection.children.link(collection)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(INPUT))
    imported = list(set(bpy.data.objects) - before)
    assert imported and all(o.type == "MESH" for o in imported)
    for obj in imported:
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        collection.objects.link(obj)
        obj.hide_select = True
        obj["reference_only"] = True
    collection.hide_select = True
    bpy.context.view_layer.update()
    report = {
        "input": str(INPUT), "sha256": INPUT_SHA,
        "original_session": original,
        "scene": scene.name,
        "objects": [{"name": o.name, "vertices": len(o.data.vertices), "faces": len(o.data.polygons)} for o in imported],
        "blender_z_up_bounds": bounds(imported),
        "scale_and_orientation": "Unmodified import; no projection registration claimed.",
    }
    scene["source_sha256"] = INPUT_SHA
    scene["stage_complete"] = True
    write_json(SOURCE / "reference_import.json", report)
    print(json.dumps(report, ensure_ascii=True))
verify_input()
