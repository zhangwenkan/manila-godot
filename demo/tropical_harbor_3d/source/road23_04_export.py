"""Export only the road-contact terrain/grass and save the owned Blender source."""
import bpy,json,ast,math,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/road_contacts_20261123';OUT=ROOT/'assets/reference'
terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
assert terrain.get('road23_contacts_grade') and terrain.get('road23_grass_contacts')
coords=np.array([v.co[:] for v in mesh.vertices],np.float32);idx=np.array([l.vertex_index for l in mesh.loops])
mesh.uv_layers['RockRegion'].data.foreach_set('uv',np.column_stack(((-coords[idx,1]-10)/45,(coords[idx,2]-.7)/4.4)).astype(np.float32).ravel())
mat=mesh.materials[0];nodes=mat.node_tree.nodes;links=mat.node_tree.links
pr=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');land=nodes['G23_LandUse']
assert land.image.name=='G23_LandUse'
assert len(pr.inputs['Base Color'].links)==1
preview=pr.inputs['Base Color'].links[0].from_socket
links.new(land.outputs['Color'],pr.inputs['Base Color'])
try:
    bpy.ops.object.select_all(action='DESELECT');terrain.hide_set(False);terrain.select_set(True);bpy.context.view_layer.objects.active=terrain
    opts=dict(filepath=str(OUT/'terrain.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='ACTIVE')
    if 'export_all_uvs' in bpy.ops.export_scene.gltf.get_rna_type().properties:opts['export_all_uvs']=True
    bpy.ops.export_scene.gltf(**opts)
finally:links.new(preview,pr.inputs['Base Color'])
bpy.context.view_layer.update();bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
def ss(a,b,x):
    q=max(0,min(1,(x-a)/(b-a)));return q*q*(3-2*q)
def shore(z):return 7.8+1.45*math.sin(z*.12)+.48*math.sin(z*.29)-21*ss(-18.7,-26,z)
values=[]
for z in np.arange(-30,90.001,.25):
    for d in np.arange(-20,50.001,.25):
        h=bvh.ray_cast(Vector((shore(float(z))+float(d),-float(z),80)),Vector((0,0,-1)),300)[0]
        values.append(round(h.z if h else -15,5))
(OUT/'shore_relief_height.json').write_text(json.dumps({'d0':-20,'z0':-30,'step':.25,'columns':281,'rows':481,'heights':values}),encoding='utf8')
bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.data.collections['Reference_GroundCover'].objects:ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['G23_RootedGrassMargins']
bpy.ops.export_scene.gltf(filepath=str(OUT/'ground_cover.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT',export_vertex_color='ACTIVE')
helper=json.loads((ROOT/'source/reference_detail_01_materials.mcp.json').read_text(encoding='utf8'))['code']
definitions=[n for n in ast.parse(helper).body if isinstance(n,ast.FunctionDef) and n.name=='export_collection']
assert len(definitions)==1 and not bpy.data.collections.get('D19_EXPORT')
exec(compile(ast.Module(body=definitions,type_ignores=[]),'Pure collection export helper','exec'),globals())
source=bpy.data.collections['Reference_Foliage'];hidden=source.hide_viewport
try:export_collection('Reference_Foliage','foliage.glb')
finally:
    tmp=bpy.data.collections.get('D19_EXPORT')
    if tmp:
        for ob in list(tmp.objects):bpy.data.objects.remove(ob,do_unlink=True)
        bpy.data.collections.remove(tmp)
    source.hide_viewport=hidden
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
report={'source_saved':True,'dirty':bpy.data.is_dirty,'source_material_restored':pr.inputs['Base Color'].links[0].from_socket==preview,
 'terrain_vertices':len(mesh.vertices),'terrain_triangles':len(mesh.polygons),'height_values':len(values),
 'assets':{name:{'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest(),'bytes':(OUT/name).stat().st_size} for name in ('terrain.glb','foliage.glb','ground_cover.glb','G23_LandUse.png','shore_relief_height.json')},
 'visual_accepted':False}
(LOG/'export.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
