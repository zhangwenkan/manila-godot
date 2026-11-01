from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
from model_lib import *
root=activate()
# Dedicated inspection setup; excluded from the export whitelist.
s=scene()
preview=bpy.data.collections.new('INS_Preview')
s.collection.children.link(preview)
cam_data=bpy.data.cameras.new('INS_ReviewCamera')
cam=bpy.data.objects.new('INS_ReviewCamera',cam_data)
preview.objects.link(cam)
cam.location=(15,-24,19)
target=Vector((-2.7,0,2.2))
cam.rotation_euler=(target-Vector(cam.location)).to_track_quat('-Z','Y').to_euler()
cam_data.type='ORTHO'
cam_data.ortho_scale=23
s.camera=cam
s.render.engine='CYCLES'
s.cycles.samples=24
s.render.resolution_x=1600
s.render.resolution_y=1100
s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('INS_PreviewWorld')
s.world.use_nodes=True
s.world.node_tree.nodes['Background'].inputs[0].default_value=(.42,.49,.53,1)
s.world.node_tree.nodes['Background'].inputs[1].default_value=.7
light_data=bpy.data.lights.new('INS_Key','AREA')
light_data.energy=1800
light_data.shape='DISK'
light_data.size=10
light=bpy.data.objects.new('INS_Key',light_data)
preview.objects.link(light)
light.location=(-5,-9,17)
light.rotation_euler=(Vector((-1,1,0))-light.location).to_track_quat('-Z','Y').to_euler()
s.view_settings.view_transform='Standard'
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        space=area.spaces.active
        space.overlay.show_overlays=False
        space.shading.type='MATERIAL'
        space.region_3d.view_perspective='CAMERA'
        space.region_3d.view_camera_zoom=0
print('INS_PREVIEW_SETUP_READY')
