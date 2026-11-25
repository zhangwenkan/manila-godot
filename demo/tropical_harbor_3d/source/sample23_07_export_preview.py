# Export current sample through the verified Blender MCP session.
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/rock_path_sample_20261123';OUT=ROOT/'assets/reference'
terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
assert terrain.get('sample23_surfaces') and terrain.get('sample23_grades_refined')
coords=np.array([v.co[:] for v in mesh.vertices],np.float32);indices=np.array([l.vertex_index for l in mesh.loops])
mesh.uv_layers['RockRegion'].data.foreach_set('uv',np.column_stack(((-coords[indices,1]-10)/45,(coords[indices,2]-.7)/4.4)).astype(np.float32).ravel())
mat=mesh.materials[0];nodes=mat.node_tree.nodes;links=mat.node_tree.links
principled=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
regional=nodes.get('S23 regional rock albedo')
previous_base=[(l.from_socket,l.to_socket) for l in list(links) if l.to_node==principled and l.to_socket==principled.inputs['Base Color']]
links.new(regional.outputs['Color'],principled.inputs['Base Color'])
bpy.context.view_layer.update();bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def shore(z):return 7.8+1.45*np.sin(z*.12)+.48*np.sin(z*.29)-21*smooth(-18.7,-26,z)
def ground(x,z):
 hit=bvh.ray_cast(Vector((x,-z,80)),Vector((0,0,-1)),300)[0];return hit.z if hit else -15
values=[round(ground(float(shore(z)+d),float(z)),5) for z in np.arange(-30,90.001,.25) for d in np.arange(-20,50.001,.25)]
(OUT/'shore_relief_height.json').write_text(json.dumps({'d0':-20,'z0':-30,'step':.25,'columns':281,'rows':481,'heights':values}),encoding='utf8')
bpy.ops.object.select_all(action='DESELECT');terrain.hide_set(False);terrain.select_set(True);bpy.context.view_layer.objects.active=terrain
props=bpy.ops.export_scene.gltf.get_rna_type().properties
kwargs=dict(filepath=str(OUT/'terrain.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='ACTIVE')
if 'export_all_uvs' in props:kwargs['export_all_uvs']=True
try:
 bpy.ops.export_scene.gltf(**kwargs)
finally:
 for l in list(links):
  if l.to_node==principled and l.to_socket==principled.inputs['Base Color']:links.remove(l)
 for a,b in previous_base:links.new(a,b)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print(json.dumps({'exported':True,'source_saved':True,'dirty':bpy.data.is_dirty,'uvs':[u.name for u in mesh.uv_layers],'export_all_uvs':'export_all_uvs' in props}))
