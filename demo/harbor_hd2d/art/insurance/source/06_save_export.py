from pathlib import Path
import sys, json, ast
sys.path.insert(0,str(Path(__file__).parent))
from model_lib import *
root=activate()
assert root.get('dock_complete')
source_path=SOURCE/'insurance.blend'
glb_path=SOURCE.parent/'insurance.glb'
assert not source_path.exists() and not glb_path.exists(), 'Inspect existing deliveries before exporting again'
# Save only the model collection and its dependencies, without the user's scene or preview rig.
saved_scene=bpy.data.scenes.new('InsuranceAssetSource')
saved_scene.collection.children.link(collection())
saved_scene.unit_settings.system='METRIC'
saved_scene['modeling_notes']='Local Blender-MCP scripted mesh construction from one reference view. Hidden sides are interpreted. Visual comparison remains pending.'
for image in bpy.data.images:
    if image.name in ['wall_blue.png','roof_tin.png','crane_red.png','dock_wood.png']:
        image.pack()
bpy.data.libraries.write(str(source_path),{saved_scene},path_remap='RELATIVE',fake_user=True,compress=True)
# The editable source keeps all parts. The runtime export consolidates evaluated
# geometry by semantic group, retaining UVs and multiple material surfaces.
export_scene=bpy.data.scenes.new('INS_RuntimeExport')
export_col=bpy.data.collections.new('INS_RuntimeGeometry')
export_scene.collection.children.link(export_col)
export_root=bpy.data.objects.new('InsuranceRuntime',None)
export_col.objects.link(export_root)
source_deps=bpy.context.evaluated_depsgraph_get()
prepared=[]
for section in root.children:
    copies=[]
    for obj in section.children_recursive:
        if obj.type!='MESH': continue
        data=bpy.data.meshes.new_from_object(obj.evaluated_get(source_deps),preserve_all_data_layers=True,depsgraph=source_deps)
        copy=bpy.data.objects.new('INS_EvaluatedPart',data)
        export_col.objects.link(copy)
        copy.matrix_world=obj.matrix_world.copy()
        copies.append(copy)
    prepared.append((section.name,copies))
bpy.context.window.scene=export_scene
for name,copies in prepared:
    for obj in bpy.context.view_layer.objects: obj.select_set(False)
    for obj in copies: obj.select_set(True)
    bpy.context.view_layer.objects.active=copies[0]
    bpy.ops.object.join()
    joined=bpy.context.view_layer.objects.active
    joined.name='INS_'+name+'Geometry'
    joined.parent=export_root
    # Bake translation/rotation/scale into the combined mesh for a clean game origin.
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
for obj in bpy.context.view_layer.objects: obj.select_set(True)
bpy.context.view_layer.objects.active=export_root
bpy.ops.export_scene.gltf(filepath=str(glb_path),export_format='GLB',use_selection=True,use_active_scene=True,export_yup=True,export_apply=True,export_cameras=False,export_lights=False,export_animations=False,export_materials='EXPORT',export_image_format='AUTO')
print('DELIVERY_SAVED',str(source_path),str(glb_path))
print('RUNTIME_GROUPS',[(o.name,len(o.data.polygons),len(o.data.materials)) for o in export_scene.objects if o.type=='MESH'])
# Restore the user's original active scene and selection. The new model scenes remain available.
original=ast.literal_eval(scene()['original_scene_state'])
bpy.context.window.scene=bpy.data.scenes[original['scene']]
for obj in bpy.context.view_layer.objects: obj.select_set(obj.name in original['selected'])
if original['active']: bpy.context.view_layer.objects.active=bpy.data.objects[original['active']]
print('ORIGINAL_SCENE_RESTORED',bpy.context.scene.name,[o.name for o in bpy.context.scene.objects])
