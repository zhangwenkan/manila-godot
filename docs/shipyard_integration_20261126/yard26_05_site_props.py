"""Archive one complete obsolete pier; relocate/ground complete plant groups."""
import bpy,os,json
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/shipyard_integration_20261126'
assert os.getpid()==29492 and bpy.types.blendermcp_server.port==9881
assert not (LOG/'props_mutation.json').exists()
plan=json.loads((LOG/'site_semantic_candidates_readonly.json').read_text(encoding='utf8'))
raw=np.load(LOG/'terrain_before.npz');old=BVHTree.FromPolygons(raw['positions'].tolist(),raw['triangles'].tolist(),all_triangles=True)
t=bpy.data.objects['C25_ContourBuiltCoast'];new=BVHTree.FromPolygons([v.co[:] for v in t.data.vertices],[list(p.vertices) for p in t.data.polygons],all_triangles=True)
def h(bvh,x,y):
 hit=bvh.ray_cast(Vector((float(x),float(y),60)),Vector((0,0,-1)),200)[0]
 assert hit is not None
 return hit.z
archive=bpy.data.collections.new('Archive_Y26_ReplacedSmallPier');bpy.context.scene.collection.children.link(archive)
archive.hide_render=True;archive.hide_viewport=True
names=plan['old_small_pier']['names'];assert len(names)==121
for name in names:
 ob=bpy.data.objects[name];assert bpy.data.collections['Reference_Coast'] in list(ob.users_collection)
 for c in list(ob.users_collection):c.objects.unlink(ob)
 archive.objects.link(ob)
allowed=list(names);moves=[]
fol=bpy.data.collections['Reference_Foliage']
def suffix(name):
 last=name.rsplit('.',1)[-1];return int(last) if last.isdigit() else 0
def stem(name):
 parts=name.rsplit('.',1);return parts[0] if len(parts)==2 and parts[1].isdigit() else name
def matching(s):return sorted([o for o in fol.objects if stem(o.name)==s],key=lambda o:suffix(o.name))
def support(ob):
 pts=[ob.matrix_world@v.co for v in ob.data.vertices];bottom=min(p.z for p in pts)
 low=[p for p in pts if p.z<bottom+.12]
 return sum(low,Vector())/len(low)
def shift_group(group,root,dx=0,dy=0):
 p=support(root);dz=h(new,p.x+dx,p.y+dy)-h(old,p.x,p.y)
 if abs(dx)+abs(dy)+abs(dz)<.00001:return
 vec=Vector((dx,dy,dz))
 for ob in group:
  mat=ob.matrix_world.copy();mat.translation+=vec;ob.matrix_world=mat;allowed.append(ob.name)
 moves.append({'root':root.name,'count':len(group),'delta_blender':list(vec),'new_root_godot':[p.x+dx,p.z+dz,-p.y-dy]})
trunks=matching('Tree_Trunk');crowns=matching('D19_Tree_Crown');branches=matching('Tree_Branch')
assert len(trunks)==40 and len(crowns)==240 and len(branches)==200
for i,root in enumerate(trunks):
 p=support(root)
 if 4<p.x<25.5 and 0<p.y<18.2:shift_group([root]+crowns[i*6:(i+1)*6]+branches[i*5:(i+1)*5],root)
palms=matching('Palm_Trunk');parts=[(matching(s),n) for s,n in [('D19_Palm_FrondRachis',8),('D19_Palm_FrondLeaflets',8),('Palm_Coconut',3),('D19_Palm_GrowthRing',12)]]
assert len(palms)==18 and all(len(a)==18*n for a,n in parts)
for i,root in enumerate(palms):
 group=[root]+[o for a,n in parts for o in a[i*n:(i+1)*n]];p=support(root)
 if root.name=='Palm_Trunk.014':shift_group(group,root,2.5,5.5)
 elif root.name=='Palm_Trunk.015':shift_group(group,root,27-p.x,10-p.y)
 elif 4<p.x<25.5 and 0<p.y<18.2:shift_group(group,root)
for root in matching('S20_CourtyardShrub'):
 p=support(root)
 if 4<p.x<25.5 and 0<p.y<18.2:shift_group([root],root)
for ob in bpy.data.collections['Reference_Rocks'].objects:
 p=support(ob)
 if ob.name=='Bank_Boulder.036':shift_group([ob],ob,-.2,1.9)
 elif 4<p.x<25.5 and 0<p.y<18.2:shift_group([ob],ob)
bpy.context.view_layer.update()
r={'archived_pier':names,'moved_groups':moves,'allowed_changed_names':sorted(set(allowed)),'saved':False}
(LOG/'props_mutation.json').write_text(json.dumps(r,indent=2),encoding='utf8')
g=json.loads((LOG/'ground_mutation.json').read_text(encoding='utf8'))
mutation={'allowed_changed_names':sorted(set(allowed+g['allowed_changed_names'])),'targets':['Reference_Shipyard','Reference_Terrain','Reference_Coast','Reference_Foliage','Reference_GroundCover','Reference_Rocks']}
(LOG/'mutation.json').write_text(json.dumps(mutation,indent=2),encoding='utf8')
print(json.dumps({'archived_pier_count':len(names),'moves':moves,'allowed_old_names':len(mutation['allowed_changed_names'])}))
