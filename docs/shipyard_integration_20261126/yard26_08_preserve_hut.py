"""Keep the existing uphill hut, stairs and supply crate fully supported."""
import bpy,bmesh,os,json,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/shipyard_integration_20261126'
assert os.getpid()==29492 and bpy.types.blendermcp_server.port==9881
assert not (LOG/'hut_support_revision.json').exists()
assert json.loads((LOG/'shipyard_export.json').read_text(encoding='utf8'))['status']=='completed'
t=bpy.data.objects['C25_ContourBuiltCoast'];mesh=t.data;p=np.array([v.co[:] for v in mesh.vertices],np.float32);tri=np.array([f.vertices[:] for f in mesh.polygons]);original=np.load(LOG/'terrain_before.npz')['positions']
np.savez_compressed(LOG/'terrain_before_hut_revision.npz',positions=p,triangles=tri)
def smooth(a,b,v):
 q=np.clip((v-a)/(b-a),0,1);return q*q*(3-2*q)
def protect(x,z):return smooth(18.8,19.9,x)*(1-smooth(25,26.2,x))*smooth(-5.1,-3.7,z)*(1-smooth(.8,1.8,z))
w=protect(p[:,0],-p[:,1]);after=p.copy();after[:,2]=p[:,2]*(1-w)+original[:,2]*w
mesh.vertices.foreach_set('co',after.ravel());mesh.update()
old=BVHTree.FromPolygons(p.tolist(),tri.tolist(),all_triangles=True);new=BVHTree.FromPolygons(after.tolist(),tri.tolist(),all_triangles=True);baseline=BVHTree.FromPolygons(original.tolist(),tri.tolist(),all_triangles=True)
def h(b,x,y):
 hit=b.ray_cast(Vector((float(x),float(y),60)),Vector((0,0,-1)),200)[0];assert hit;return hit.z
allowed=[];reground=[]
# Restore complete tree groups to the revised shoulder, deriving membership
# from the established counts, not nearest crown proximity.
fol=bpy.data.collections['Reference_Foliage']
def suffix(n):return int(n.rsplit('.',1)[-1]) if n.rsplit('.',1)[-1].isdigit() else 0
def stem(n):return n.rsplit('.',1)[0] if n.rsplit('.',1)[-1].isdigit() else n
def matching(s):return sorted([o for o in fol.objects if stem(o.name)==s],key=lambda o:suffix(o.name))
trunks=matching('Tree_Trunk');crowns=matching('D19_Tree_Crown');branches=matching('Tree_Branch')
assert len(trunks)==40 and len(crowns)==240 and len(branches)==200
for i,root in enumerate(trunks):
 pts=[root.matrix_world@v.co for v in root.data.vertices];low=min(q.z for q in pts);base=[q for q in pts if q.z<low+.12];q=sum(base,Vector())/len(base)
 if not (18.8<q.x<26.2 and -1.8<q.y<5.1):continue
 dz=h(new,q.x,q.y)-h(old,q.x,q.y)
 if abs(dz)<1e-5:continue
 group=[root]+crowns[i*6:(i+1)*6]+branches[i*5:(i+1)*5]
 for ob in group:
  mat=ob.matrix_world.copy();mat.translation.z+=dz;ob.matrix_world=mat;allowed.append(ob.name)
 reground.append({'root':root.name,'delta_height':dz,'count':len(group)})
for name in ['L24_GrassTuftClusters','G23_RootedGrassMargins','G23_EmbeddedSlopeFragments']:
 ob=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(ob.data);todo=set(bm.verts);count=0
 while todo:
  root=next(iter(todo));group={root};queue=[root]
  while queue:
   v=queue.pop()
   for e in v.link_edges:
    vv=e.other_vert(v)
    if vv not in group:group.add(vv);queue.append(vv)
  todo-=group;pts=[ob.matrix_world@v.co for v in group];q=sum(pts,Vector())/len(pts)
  if not (18.8<q.x<26.2 and -1.8<q.y<5.1):continue
  dz=h(new,q.x,q.y)-h(old,q.x,q.y)
  if abs(dz)<1e-5:continue
  shift=ob.matrix_world.to_3x3().inverted()@Vector((0,0,dz))
  for v in group:v.co+=shift
  count+=1
 if count:bm.to_mesh(ob.data);ob.data.update();allowed.append(name)
 bm.free();reground.append({'object':name,'components':count})
im=bpy.data.images['G23_LandUse'];pix=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(pix);pix=pix.reshape(im.size[1],im.size[0],4)
basepix=np.load(LOG/'landuse_before.npz')['pixels'];X,Z=np.meshgrid(-4+(np.arange(im.size[0])+.5)/im.size[0]*48,-15+(np.arange(im.size[1])+.5)/im.size[1]*97);pw=protect(X,Z)
result=(pix*(1-pw[:,:,None])+basepix*pw[:,:,None]).astype(np.float32);im.pixels.foreach_set(result.ravel());im.update();im.save()
if im.packed_file:im.unpack(method='REMOVE')
im.pack()
bpy.context.view_layer.update()
checks=[]
for name in ['Hut_Stilt.052','Hut_Stilt.053','Hut_Stilt.054','Hut_Stilt.055','Hut_EntrySteps.052','Hut_EntrySteps.053','Hut_EntrySteps.054','Hut_EntrySteps.055','Hut_StairStringer.026','Hut_StairStringer.027','Prop_Crate.019']:
 ob=bpy.data.objects[name]
 pts=[ob.matrix_world@v.co for v in ob.data.vertices];xy=sum(pts,Vector())/len(pts);prior=h(baseline,xy.x,xy.y);actual=h(new,xy.x,xy.y)
 checks.append({'name':name,'prior_terrain_height':prior,'new_terrain_height':actual,'height_error':actual-prior})
r={'changed_vertices':int(np.count_nonzero(abs(after[:,2]-p[:,2])>1e-6)),'height_increase_max':float((after-p)[:,2].max()),'regrounded':reground,'original_hut_support':checks,'maximum_support_height_error':max(abs(q['height_error']) for q in checks),'landuse_packed_matches_disk':hashlib.sha256(bytes(im.packed_file.data)).digest()==hashlib.sha256(Path(bpy.path.abspath(im.filepath)).read_bytes()).digest(),'saved':False}
(LOG/'hut_support_revision.json').write_text(json.dumps(r,indent=2),encoding='utf8')
m=json.loads((LOG/'mutation.json').read_text(encoding='utf8'));m['allowed_changed_names']=sorted(set(m['allowed_changed_names']+allowed));(LOG/'mutation.json').write_text(json.dumps(m,indent=2),encoding='utf8')
print(json.dumps(r));assert r['maximum_support_height_error']<.04
