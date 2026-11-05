"""Run through execute_blender_code on the live Blender MCP connection.
Exports the two existing collections; never starts a background Blender process.
"""
import bpy, json
from pathlib import Path
if Path(bpy.data.filepath).name != 'harbor_art_mcp.blend':
    raise RuntimeError('Open harbor_art_mcp.blend through Blender MCP first.')
root=Path(bpy.data.filepath).parent.parent
bpy.context.scene.blendermcp_port=9877
rows=[]
for coll, filename in [("Boat_Workshop","fleet_boat_mcp.glb"),("Pier_Working","pier_working_mcp.glb")]:
    for c in bpy.data.collections:
        c.hide_viewport = c.name not in [coll, "References"]
    bpy.ops.object.select_all(action='DESELECT')
    objects=[o for o in bpy.data.collections[coll].objects if o.type=='MESH']
    for o in objects:
        o.hide_set(False)
        o.hide_viewport=False
        o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    path=root/'assets'/filename
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
        export_texcoords=True,export_normals=True,export_tangents=True,
        export_vertex_color='NONE',export_materials='EXPORT',export_image_format='AUTO',
        export_apply=True,export_yup=True,export_animations=False)
    rows.append({'file':filename,'bytes':path.stat().st_size,'meshes':len(objects)})
for name in ['Boat_Workshop','Pier_Working','Pier_Broken']:
    bpy.data.collections[name].hide_viewport=False
    bpy.data.collections[name].hide_render=False
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(json.dumps(rows))
