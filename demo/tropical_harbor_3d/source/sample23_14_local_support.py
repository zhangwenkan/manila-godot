# Correct explicitly identified ground assemblies, never generic building parts.
import bpy,json,numpy as np,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/rock_path_sample_20261123';terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
assert not terrain.get('sample23_local_support')
triage=json.loads((ROOT.parent.parent/'docs/reference_review_20261123/ground_contact_triage.json').read_text(encoding='utf8'))
groups={g['anchor']:g for g in triage['groups']};bpy.context.view_layer.update();bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
def ground(x,y):
 p=bvh.ray_cast(Vector((float(x),float(y),80)),Vector((0,0,-1)),300)[0];assert p is not None;return p.z
def ss(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
moves=[]
for anchor,embed in [('Palm_Trunk.010',.10),('Tree_Trunk.035',.10)]+[('S20_CourtyardShrub.'+str(i).zfill(3),.10) for i in range(20,24)]+[('S20_grill_Prop_Barrel.007',-.005)]:
 o=bpy.data.objects[anchor];verts=np.array([o.matrix_world@v.co for v in o.data.vertices]);low=verts[verts[:,2]<verts[:,2].min()+.04];center=low.mean(axis=0)
 delta=ground(center[0],center[1])-embed-float(center[2])
 members=groups[anchor]['group_members']
 for name in members:
  item=bpy.data.objects[name];assert item.parent is None and not item.constraints
  m=item.matrix_world.copy();m.translation.z+=delta;item.matrix_world=m
 moves.append({'anchor':anchor,'objects':members,'vertical_delta':delta,'root_before':center.tolist()})
# Planters remain with their own architectural arrangement. Give their bases a bounded level landing.
pos=np.array([v.co[:] for v in mesh.vertices],np.float32);before=pos.copy();pads=[]
for name in ['Town_Planter.007','Town_Planter.008','Town_Planter.011','Town_Planter.012']:
 o=bpy.data.objects[name];corners=np.array([o.matrix_world@Vector(v) for v in o.bound_box]);center=corners.mean(axis=0);target=float(corners[:,2].min())+.005
 localmin=np.min(np.array(o.bound_box),axis=0);localmax=np.max(np.array(o.bound_box),axis=0);inverse=o.matrix_world.inverted()
 for i,p in enumerate(pos):
  if abs(p[0]-center[0])>1.1 or abs(p[1]-center[1])>1.1:continue
  q=inverse@Vector(p);dx=max(localmin[0]-q.x,0,q.x-localmax[0]);dy=max(localmin[1]-q.y,0,q.y-localmax[1]);d=math.hypot(dx,dy)
  if d>.6:continue
  weight=1-ss(.18,.6,d);pos[i,2]=p[2]+(max(p[2],target)-p[2])*weight
 pads.append({'object':name,'base_target':target})
mesh.vertices.foreach_set('co',pos.ravel());mesh.update();bpy.context.view_layer.update()
terrain['sample23_local_support']=True
(LOG/'local_support.json').write_text(json.dumps({'moves':moves,'planter_supports':pads,'ground_vertices_changed':int(np.sum(abs(pos[:,2]-before[:,2])>.001))},indent=2),encoding='utf8')
print(json.dumps({'explicit_groups_moved':len(moves),'components':sum(len(m['objects']) for m in moves),'bounded_planter_supports':len(pads),'ground_vertices_changed':int(np.sum(abs(pos[:,2]-before[:,2])>.001))}))
