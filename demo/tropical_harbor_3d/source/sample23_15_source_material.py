# Editable Blender preview of the same regional roles, retained after GLB export.
import bpy,json,math
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/rock_path_sample_20261123'
terrain=bpy.data.objects['C25_ContourBuiltCoast'];mat=terrain.data.materials[0];nodes=mat.node_tree.nodes;links=mat.node_tree.links
for n in list(nodes):
 if n.name.startswith('S23Preview '):nodes.remove(n)
def node(kind,label):
 n=nodes.new(kind);n.name='S23Preview '+label;return n
def inp(n,k,value):
 if hasattr(value,'is_output'):links.new(value,n.inputs[k])
 else:n.inputs[k].default_value=value
def mathop(op,a,b=0,label='math'):
 n=node('ShaderNodeMath',label);n.operation=op;inp(n,0,a);inp(n,1,b);return n.outputs[0]
def mix(f,a,b,label):
 n=node('ShaderNodeMixRGB',label);inp(n,0,f);inp(n,1,a);inp(n,2,b);return n.outputs[0]
uv=node('ShaderNodeUVMap','region UV');uv.uv_map='UVMap'
sep=node('ShaderNodeSeparateXYZ','region axes');links.new(uv.outputs[0],sep.inputs[0])
def ramp(sock,lo,hi,label):
 n=node('ShaderNodeMapRange',label);n.clamp=True;n.interpolation_type='SMOOTHSTEP';inp(n,'Value',sock);inp(n,'From Min',lo);inp(n,'From Max',hi);return n.outputs[0]
xf=mathop('MULTIPLY',ramp(sep.outputs['X'],0,2/26,'westfade'),ramp(sep.outputs['X'],1,24/26,'eastfade'))
yf=mathop('MULTIPLY',ramp(sep.outputs['Y'],0,2/45,'southfade'),ramp(sep.outputs['Y'],1,42/45,'northfade'));fade=mathop('MULTIPLY',xf,yf)
attr=node('ShaderNodeVertexColor','legacy roles');attr.layer_name='LandUse';oldsep=node('ShaderNodeSeparateColor','legacy separate');links.new(attr.outputs['Color'],oldsep.inputs[0])
land=nodes['S23 regional land roles'];land.extension='EXTEND';newsep=node('ShaderNodeSeparateColor','regional separate');links.new(land.outputs['Color'],newsep.inputs[0])
weights=[]
for i,(old,new) in enumerate(zip([*oldsep.outputs[:3],attr.outputs['Alpha']],[*newsep.outputs[:3],land.outputs['Alpha']])):
 weight=mathop('ADD',mathop('MULTIPLY',old,mathop('SUBTRACT',1,fade)),mathop('MULTIPLY',new,fade));weights.append(weight)
assigned=mathop('ADD',mathop('ADD',weights[0],weights[1]),mathop('ADD',weights[2],weights[3]));sand=mathop('MAXIMUM',0,mathop('SUBTRACT',1,assigned))
weights=[mathop('MULTIPLY',w,w) for w in weights+[sand]]
total=weights[0]
for w in weights[1:]:total=mathop('ADD',total,w)
total=mathop('MAXIMUM',total,.0001)
weights=[mathop('DIVIDE',w,total) for w in weights]
geom=node('ShaderNodeNewGeometry','world position')
def boximage(image_name,scale,label):
 n=node('ShaderNodeTexImage',label);n.image=bpy.data.images[image_name];n.projection='BOX';n.projection_blend=.2
 v=node('ShaderNodeVectorMath',label+' scale');v.operation='SCALE';links.new(geom.outputs['Position'],v.inputs[0]);v.inputs['Scale'].default_value=1/scale;links.new(v.outputs[0],n.inputs['Vector']);return n.outputs['Color']
grass=boximage('L24_Grass',2.4,'grass');soil=boximage('R27_Earth_Albedo',2.8,'soil');oldrock=boximage('R27_Rock_Albedo',3.2,'old rock');oldpath=boximage('L24_Path',4.8,'old path');path=boximage('S23_Path_Albedo',4.8,'path')
rock=mix(fade,oldrock,nodes['S23 regional rock albedo'].outputs['Color'],'regional rock')
path=mix(fade,oldpath,path,'regional path');beach=(.66,.50,.285,1)
colors=[grass,rock,path,soil,beach];parts=[]
for i,(color,weight) in enumerate(zip(colors,weights)):
 n=node('ShaderNodeMixRGB','weighted '+str(i));n.blend_type='MULTIPLY';inp(n,0,1.);inp(n,1,color);links.new(weight,n.inputs[2]);parts.append(n.outputs[0])
combined=parts[0]
for i,p in enumerate(parts[1:]):
 n=node('ShaderNodeMixRGB','sum '+str(i));n.blend_type='ADD';inp(n,0,1.);inp(n,1,combined);inp(n,2,p);combined=n.outputs[0]
principled=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');links.new(combined,principled.inputs['Base Color']);principled.inputs['Roughness'].default_value=.94
bump=node('ShaderNodeBump','regional rock relief');bump.inputs['Distance'].default_value=.16;links.new(mathop('MULTIPLY',fade,weights[1]),bump.inputs['Strength']);links.new(nodes['S23 regional rock height'].outputs['Color'],bump.inputs['Height']);links.new(bump.outputs['Normal'],principled.inputs['Normal'])
mat['S23_source_preview']='Regional roles with fallback and triplanar textures; engine exact shader remains landform_mass.gdshader'
(LOG/'source_material.json').write_text(json.dumps({'material':mat.name,'source_preview_roles':True,'base_link':principled.inputs['Base Color'].links[0].from_node.name,'uv_layers':[u.name for u in terrain.data.uv_layers],'runtime_shader':'landform_mass.gdshader'},indent=2),encoding='utf8')
print('Restored editable regional grass, soil, sand, rock and path preview in source')
