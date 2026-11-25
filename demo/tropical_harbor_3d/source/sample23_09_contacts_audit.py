# Read only audit of this turn's changed ground. Run through owned MCP.
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/rock_path_sample_20261123'
terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
raw=np.load(str(LOG/'terrain_baseline.npz'));old=raw['positions'];oldloops=raw['loops'];faces=[oldloops[s:s+n].tolist() for s,n in zip(raw['starts'],raw['sizes'])]
baseline=BVHTree.FromPolygons(old.tolist(),faces)
bpy.context.view_layer.update();current=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
def ground(bvh,x,y):
 p=bvh.ray_cast(Vector((float(x),float(y),80)),Vector((0,0,-1)),300)[0]
 return p.z if p is not None else -100
contacts=[];floors=[]
for cname in ['Reference_Town','Reference_Coast','Reference_Foliage','Reference_Rocks']:
 coll=bpy.data.collections.get(cname)
 if not coll:continue
 for o in coll.all_objects:
  if o.type!='MESH' or o==terrain or o.name.startswith('L24_Grass'):continue
  pts=np.array([o.matrix_world@Vector(v) for v in o.bound_box]);center=pts.mean(axis=0)
  if not (8<center[0]<34 and 10<-center[1]<55):continue
  bottom=pts[pts[:,2]<pts[:,2].min()+.001]
  if not len(bottom):continue
  delta=[ground(current,p[0],p[1])-ground(baseline,p[0],p[1]) for p in bottom]
  item={'name':o.name,'collection':cname,'building':o.get('town_building'),'center':[float(center[0]),float(-center[1]),float(center[2])],'bottom':float(pts[:,2].min()),'delta':[float(min(delta)),float(max(delta))],'gaps':[float(p[2]-ground(current,p[0],p[1])) for p in bottom],'oldgaps':[float(p[2]-ground(baseline,p[0],p[1])) for p in bottom]}
  if o.name.startswith(('Town_Floor','Town_Step','Hut_Floor','Hut_FrontStep')):floors.append(item)
  if max(abs(d) for d in delta)>.045:contacts.append(item)
grass=bpy.data.objects.get('L24_GrassTuftClusters');grassrows=[]
region=np.load(str(LOG/'regional_surface_data.npz'))['land'];n=len(region)
if grass:
 for p in grass.data.polygons:
  verts=[grass.matrix_world@grass.data.vertices[i].co for i in p.vertices]
  root=(verts[0]+verts[1])*.5;x,y=root.x,root.y;z=-y
  if not (8<x<34 and 10<z<55):continue
  a=ground(baseline,x,y);b=ground(current,x,y);role=region[min(n-1,int((z-10)/45*n)),min(n-1,int((x-8)/26*n))]
  if abs(a-b)>.03 or role[2]>.35 or role[1]>.6:
   grassrows.append({'face':p.index,'root':[x,z,root.z],'ground':b,'oldground':a,'delta':b-a,'roles':[float(v) for v in role]})
nodes=[];mat=mesh.materials[0]
for node in mat.node_tree.nodes:
 nodes.append({'name':node.name,'type':node.type,'image':getattr(getattr(node,'image',None),'name',None)})
links=[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in mat.node_tree.links]
report={'contacts_on_changed_ground':contacts,'floors_and_steps':floors,'grass_candidates':grassrows,'source_material_nodes':nodes,'source_material_links':links}
(LOG/'contacts_current.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({'changed_ground_objects':len(contacts),'floors_and_steps':len(floors),'grass_candidates':len(grassrows),'source_material_links':links}))
