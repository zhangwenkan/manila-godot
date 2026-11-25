# Ground grass blades after the scoped grades. Live MCP once only.
import bpy,bmesh,json,numpy as np,ast
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/rock_path_sample_20261123';OUT=ROOT/'assets/reference'
terrain=bpy.data.objects['C25_ContourBuiltCoast'];assert not terrain.get('sample23_grass')
raw=np.load(str(LOG/'terrain_baseline.npz'));loops=raw['loops'];faces=[loops[s:s+n].tolist() for s,n in zip(raw['starts'],raw['sizes'])]
oldbvh=BVHTree.FromPolygons(raw['positions'].tolist(),faces);bpy.context.view_layer.update();bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
roles=np.load(str(LOG/'regional_surface_data.npz'))['land'];n=len(roles)
o=bpy.data.objects['L24_GrassTuftClusters'];bm=bmesh.new();bm.from_mesh(o.data);bm.faces.ensure_lookup_table();inverse=o.matrix_world.inverted();remove=[];moved=0
for face in bm.faces:
 assert len(face.verts)==3 and all(len(v.link_faces)==1 for v in face.verts),'Shared blade vertices need distinct treatment'
 root=o.matrix_world@((face.verts[0].co+face.verts[1].co)*.5);x,y=root.x,root.y;z=-y
 if not (10<x<32 and 12<z<52):continue
 role=roles[min(n-1,int((z-10)/45*n)),min(n-1,int((x-8)/26*n))]
 hit,normal,_,_=bvh.ray_cast(Vector((x,y,80)),Vector((0,0,-1)),300)
 old=oldbvh.ray_cast(Vector((x,y,80)),Vector((0,0,-1)),300)[0]
 if hit is None or old is None:continue
 if role[2]>.35 or role[1]>.55 or normal.z<.56:
  remove.append(face);continue
 if abs(hit.z-old.z)>.025:
  delta=hit.z-.015-root.z
  for v in face.verts:
   p=o.matrix_world@v.co;p.z+=delta;v.co=inverse@p
  moved+=1
bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(o.data);bm.free();o.data.update()
terrain['sample23_grass']=True
(LOG/'grass_grounding.json').write_text(json.dumps({'removed_blades':len(remove),'replanted_blades':moved,'remaining_blades':len(o.data.polygons),'scope':'x10..32,z12..52; no terrain-independent prop matching'},indent=2),encoding='utf8')
print((LOG/'grass_grounding.json').read_text())
