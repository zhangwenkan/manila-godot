"""Normalize the inspected asset-only library into a normal editable startup file."""
import bpy
from pathlib import Path
from mathutils import Vector
p=Path(bpy.data.filepath)
assert p.name=='insurance.blend' and p.exists()
assert len(bpy.data.scenes)==1 and bpy.data.scenes[0].name=='InsuranceAssetSource'
s=bpy.data.scenes[0]
assert all(o.type in ['MESH','EMPTY'] for o in s.objects)
for window in bpy.context.window_manager.windows:
    window.scene=s
for obj in s.objects: obj.select_set(obj.name=='InsuranceAsset')
s.view_layers[0].objects.active=bpy.data.objects['InsuranceAsset']
# A framed material viewport makes the saved source immediately inspectable.
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type!='VIEW_3D': continue
        space=area.spaces.active
        space.shading.type='MATERIAL'
        space.overlay.show_overlays=False
        region=space.region_3d
        region.view_perspective='ORTHO'
        region.view_location=Vector((-2.25,0,3.0))
        region.view_distance=24
        region.view_rotation=Vector((15,-24,19)).to_track_quat('Z','Y')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(p))
print('INSURANCE_EDITABLE_STARTUP_SAVED')
