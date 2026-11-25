# Read-only measurement in the verified MCP session.
import bpy, json, numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent; LOG=ROOT/'captures/rock_path_sample_20261123'
terrain=bpy.data.objects['C25_ContourBuiltCoast']; mesh=terrain.data
bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
attr=mesh.color_attributes['LandUse']
rows=[]
for z in [12,15,18,21,24,27,29,32,35,38,40.5,43,46]:
 row=[]
 for x in np.arange(9,33.01,1.0):
  hit,n,fi,dist=bvh.ray_cast(Vector((float(x),-z,60)),Vector((0,0,-1)),150)
  if hit:
   c=np.mean([attr.data[i].color for i in mesh.polygons[fi].loop_indices],axis=0)
   row.append([round(float(x),2),round(hit.z,3),round(n.z,3),[round(float(v),2) for v in c]])
 rows.append({'z':z,'x_height_normal_roles':row})
(LOG/'sections_before.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print(json.dumps(rows))
