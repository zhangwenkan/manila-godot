import bpy, os, json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
assert os.getpid()==29492 and bpy.types.blendermcp_server.port==9881
ROOT=Path(bpy.data.filepath).parent.parent; LOG=ROOT/'captures/shipyard_integration_20261126'
terrain=bpy.data.objects['C25_ContourBuiltCoast']
bvh=BVHTree.FromPolygons([terrain.matrix_world@v.co for v in terrain.data.vertices],[list(p.vertices) for p in terrain.data.polygons])
def height(x,z):
 hit=bvh.ray_cast(Vector((x,-z,30)),Vector((0,0,-1)))
 return round(hit[0].z,4) if hit[0] else None
def bounds(o):
 pts=[o.matrix_world@Vector(p) for p in o.bound_box]
 return [[round(min(p[i] for p in pts),4) for i in range(3)],[round(max(p[i] for p in pts),4) for i in range(3)]]
near=[]
for c in ['Reference_Town','Reference_Foliage','Reference_Rocks']:
 for o in bpy.data.collections[c].all_objects:
  if o.type!='MESH':continue
  b=bounds(o)
  if b[1][0]>8 and b[0][0]<26 and b[1][1]>0 and b[0][1]<20:
   if c!='Reference_Foliage' or 'Trunk' in o.name or 'stem' in o.name.lower():near.append({'name':o.name,'collection':c,'bounds':b,'props':{k:str(o[k]) for k in o.keys()}})
r={'grid':{str(z):{str(x):height(x,z) for x in [3,5,7,9,11,13,15,17,19,21,23,25]} for z in [-20,-18,-16,-14,-12,-10,-8,-6,-4,-2,0,2]},'near':near,'colors':[(a.name,a.domain,a.data_type) for a in terrain.data.color_attributes],'land_images':[{'name':i.name,'path':i.filepath,'size':list(i.size),'packed':bool(i.packed_file),'colorspace':i.colorspace_settings.name} for i in bpy.data.images if 'LandUse' in i.name or 'land_use' in i.filepath],'workshop_support':[{'name':o.name,'bounds':bounds(o)} for o in bpy.data.collections['Reference_Shipyard'].all_objects if o.type=='MESH' and any(s in o.name.lower() for s in ['foundation','shore tread','transition flag','slipway','submerged','outer steps'])]}
(LOG/'site_inspect.json').write_text(json.dumps(r,indent=2),encoding='utf8')
print(json.dumps({'grid':r['grid'],'near':r['near'],'colors':r['colors'],'land_images':r['land_images']}))
