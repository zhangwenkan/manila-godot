"""Run only in a NEW --background --factory-startup Blender process."""
from pathlib import Path
import bpy
from mathutils import Vector

source = Path(__file__).resolve().parent
output = source / "insurance_pixel_sample.blend"
assert not output.exists(), "Refusing to overwrite an existing source"
assert not bpy.data.filepath, "Must not run in the user's open file"
assert bpy.app.background, "Use a separate background Blender process"
with bpy.data.libraries.load(str(source / "sample_source_library.blend"), link=False) as (available, loaded):
    assert available.scenes == ["INS7_StyleSample"]
    loaded.scenes = available.scenes
scene = loaded.scenes[0]
for window in bpy.context.window_manager.windows:
    window.scene = scene
for other in list(bpy.data.scenes):
    if other != scene:
        bpy.data.scenes.remove(other)
for obj in list(bpy.data.objects):
    if obj.name not in scene.objects:
        bpy.data.objects.remove(obj, do_unlink=True)
assert all(o.type in {"MESH", "EMPTY"} for o in scene.objects)
assert len([o for o in scene.objects if o.type == "MESH"]) == 39
root = scene.objects["INS7_StyleSampleRoot"]
for obj in scene.objects:
    obj.select_set(obj == root)
scene.view_layers[0].objects.active = root
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            space = area.spaces.active
            space.shading.type = "MATERIAL"
            space.overlay.show_overlays = False
            space.region_3d.view_perspective = "ORTHO"
            space.region_3d.view_location = Vector((.55,.55,3.25))
            space.region_3d.view_distance = 20
            space.region_3d.view_rotation = Vector((6,-18,11)).to_track_quat('Z','Y')
assert all(i.packed_file for i in bpy.data.images if i.name.startswith("sample_"))
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
print("INS7_SAMPLE_SOURCE_SAVED", str(output), "39 editable mesh parts; 2 packed textures; no reference/default scene")
