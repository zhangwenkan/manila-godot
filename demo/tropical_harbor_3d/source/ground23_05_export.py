"""Install editable source preview, export continuous terrain and save via MCP."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent;OUT=ROOT/'assets/reference';LOG=ROOT/'captures/ground_integration_20261123'
terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
assert terrain.get('ground23_forms')
coords=np.array([v.co[:] for v in mesh.vertices],np.float32);indices=np.array([l.vertex_index for l in mesh.loops])
uv=mesh.uv_layers.get('GroundRegion') or mesh.uv_layers.new(name='GroundRegion')
uv.data.foreach_set('uv',np.column_stack(((coords[indices,0]+4)/48,(-coords[indices,1]+15)/97)).astype(np.float32).ravel())
# Retain old UVs accurately for archival interpretation; runtime G23 is world mapped.
mesh.uv_layers['UVMap'].data.foreach_set('uv',np.column_stack(((coords[indices,0]-8)/26,(-coords[indices,1]-10)/45)).astype(np.float32).ravel())
mesh.uv_layers['RockRegion'].data.foreach_set('uv',np.column_stack(((-coords[indices,1]-10)/45,(coords[indices,2]-.7)/4.4)).astype(np.float32).ravel())
mat=mesh.materials[0];nodes=mat.node_tree.nodes;links=mat.node_tree.links
for nd in list(nodes):
    if nd.name.startswith('G23Preview '):nodes.remove(nd)
def node(kind,label):
    nd=nodes.new(kind);nd.name='G23Preview '+label;return nd
def inp(nd,k,v):
    if hasattr(v,'is_output'):links.new(v,nd.inputs[k])
    else:nd.inputs[k].default_value=v
def mathop(op,a,b=0):
    nd=node('ShaderNodeMath',op);nd.operation=op;inp(nd,0,a);inp(nd,1,b);return nd.outputs[0]
uvn=node('ShaderNodeUVMap','land UV');uvn.uv_map='GroundRegion'
land=nodes['G23_LandUse'];land.extension='EXTEND';links.new(uvn.outputs[0],land.inputs['Vector'])
sep=node('ShaderNodeSeparateColor','roles');links.new(land.outputs['Color'],sep.inputs[0])
weights=[*sep.outputs[:3],land.outputs['Alpha']]
total=mathop('ADD',mathop('ADD',weights[0],weights[1]),mathop('ADD',weights[2],weights[3]))
weights.append(mathop('MAXIMUM',0,mathop('SUBTRACT',1,total)))
weights=[mathop('MULTIPLY',w,w) for w in weights]
total=weights[0]
for w in weights[1:]:total=mathop('ADD',total,w)
weights=[mathop('DIVIDE',w,mathop('MAXIMUM',total,.0001)) for w in weights]
geo=node('ShaderNodeNewGeometry','world');parts=[];heights=[]
for name,size,w,amp in zip(['Grass','Rock','Path','Soil','Sand'],[5,8,4,4,6],weights,[.040,.24,.012,.050,.012]):
    tex=node('ShaderNodeTexImage',name);tex.image=bpy.data.images['G23_'+name];tex.projection='BOX';tex.projection_blend=.2
    scale=node('ShaderNodeVectorMath',name+' scale');scale.operation='SCALE';links.new(geo.outputs['Position'],scale.inputs[0]);scale.inputs['Scale'].default_value=1/size;links.new(scale.outputs[0],tex.inputs['Vector'])
    mul=node('ShaderNodeMixRGB',name+' weight');mul.blend_type='MULTIPLY';inp(mul,0,1);inp(mul,1,tex.outputs['Color']);inp(mul,2,w);parts.append(mul.outputs[0])
    heights.append(mathop('MULTIPLY',mathop('MULTIPLY',tex.outputs['Alpha'],amp),w))
combined=parts[0]
for p in parts[1:]:
    nd=node('ShaderNodeMixRGB','sum');nd.blend_type='ADD';inp(nd,0,1);inp(nd,1,combined);inp(nd,2,p);combined=nd.outputs[0]
pr=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');links.new(combined,pr.inputs['Base Color']);pr.inputs['Roughness'].default_value=.94
# Source preview uses the same height channels, but engine differentiates them
# independently to exclude role boundaries from relief. Record that distinction.
bump=node('ShaderNodeBump','preview microrelief');bump.inputs['Distance'].default_value=1
hh=heights[0]
for h in heights[1:]:hh=mathop('ADD',hh,h)
links.new(hh,bump.inputs['Height']);links.new(bump.outputs['Normal'],pr.inputs['Normal'])
mat['G23_source_preview']='Five authored RGB/height materials with GroundRegion role map. Runtime differentiates material heights independently.'
bpy.context.view_layer.update();bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
def ss(a,b,t):
    t=max(0,min(1,(t-a)/(b-a)));return t*t*(3-2*t)
def shore(z):return 7.8+1.45*math.sin(z*.12)+.48*math.sin(z*.29)-21*ss(-18.7,-26,z)
def height(x,z):
    hit=bvh.ray_cast(Vector((x,-z,80)),Vector((0,0,-1)),300)[0];return hit.z if hit else -15
values=[round(height(shore(float(z))+float(d),float(z)),5) for z in np.arange(-30,90.001,.25) for d in np.arange(-20,50.001,.25)]
(OUT/'shore_relief_height.json').write_text(json.dumps({'d0':-20,'z0':-30,'step':.25,'columns':281,'rows':481,'heights':values}),encoding='utf8')
# Preserve source preview after temporary export linkage used to retain UV sets.
links.new(land.outputs['Color'],pr.inputs['Base Color'])
bpy.ops.object.select_all(action='DESELECT');terrain.hide_set(False);terrain.select_set(True);bpy.context.view_layer.objects.active=terrain
try:
    options=dict(filepath=str(OUT/'terrain.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='ACTIVE')
    if 'export_all_uvs' in bpy.ops.export_scene.gltf.get_rna_type().properties:
        options['export_all_uvs']=True
    bpy.ops.export_scene.gltf(**options)
finally:links.new(combined,pr.inputs['Base Color'])
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
(LOG/'export.json').write_text(json.dumps({'source_saved':True,'dirty':bpy.data.is_dirty,'terrain_vertices':len(mesh.vertices),'terrain_triangles':len(mesh.polygons),'height_values':len(values),'material_name':mat.name,'uv_layers':[u.name for u in mesh.uv_layers],'source_preview':True},indent=2),encoding='utf8')
print('Exported terrain, refreshed actual height cache, restored preview and saved source')
