"""Run in an owned background Blender process, never in the user's live session."""
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Vector

source=Path(__file__).resolve().parent
patched='--r2-1' in sys.argv
output=source/('insurance_rebuild_r2_1.blend' if patched else 'insurance_rebuild_r2.blend')
library=source/('insurance_r2_1_library.blend' if patched else 'insurance_r2_library.blend')
assert bpy.app.background and not bpy.data.filepath
assert not output.exists()
with bpy.data.libraries.load(str(library),link=False) as (available,loaded):
    assert available.scenes==['Insurance_Rebuild_R2']
    loaded.scenes=available.scenes
scene=loaded.scenes[0]
for window in bpy.context.window_manager.windows: window.scene=scene
for other in list(bpy.data.scenes):
    if other!=scene: bpy.data.scenes.remove(other)
for obj in list(bpy.data.objects):
    if obj.name not in scene.objects: bpy.data.objects.remove(obj,do_unlink=True)
# Remove unrelated factory materials locally; do not modify installed assets or preferences.
used={m for obj in scene.objects if obj.type=='MESH' for m in obj.data.materials}
for mat in list(bpy.data.materials):
    if mat not in used: bpy.data.materials.remove(mat)
bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=False,do_recursive=True)
assert len(bpy.data.scenes)==1
assert all(obj.type in {'EMPTY','MESH'} for obj in scene.objects)
root=scene.objects['INR2_CompleteHarbor']
for obj in scene.objects: obj.select_set(obj==root)
scene.view_layers[0].objects.active=root
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active; space.shading.type='MATERIAL'
            space.overlay.show_overlays=False
            space.region_3d.view_perspective='ORTHO'
            space.region_3d.view_location=Vector((0,-1.05,3.35))
            space.region_3d.view_distance=24
            space.region_3d.view_rotation=Vector((0,-1,.90)).to_track_quat('Z','Y')
images={node.image for mat in used for node in mat.node_tree.nodes if node.type=='TEX_IMAGE'}
assert len(images)==2 and all(image.packed_file for image in images)
for obj in scene.objects:
    if obj.type!='MESH': continue
    bm=bmesh.new(); bm.from_mesh(obj.data)
    assert all(e.is_manifold for e in bm.edges),obj.name
    assert all(f.calc_area()>1e-9 for f in bm.faces),obj.name
    bm.free()
bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
print('R2_EDITABLE_SAVED',len([o for o in scene.objects if o.type=='MESH']),'closed parts, 2 packed textures, no reference/default objects')
