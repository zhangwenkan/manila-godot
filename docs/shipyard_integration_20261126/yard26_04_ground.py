"""One-shot local earthwork, through owned GUI MCP. No historic scripts replayed."""
import bpy,bmesh,os,json,math,shutil,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/shipyard_integration_20261126'
assert os.getpid()==29492 and bpy.types.blendermcp_server.port==9881 and not bpy.app.background
assert not (LOG/'ground_mutation.json').exists()
terrain=bpy.data.objects['C25_ContourBuiltCoast'];assert not terrain.get('yard26_earthwork')
mesh=terrain.data
coords=np.array([v.co[:] for v in mesh.vertices],dtype=np.float32)
tri=np.array([p.vertices[:] for p in mesh.polygons],dtype=np.int32)
np.savez_compressed(LOG/'terrain_before.npz',positions=coords,triangles=tri)
old=BVHTree.FromPolygons(coords.tolist(),tri.tolist(),all_triangles=True)
def smooth(a,b,v):
 t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)
def influence(x,z):
 return smooth(4.0,7.5,x)*(1-smooth(21.8,25.5,x))*smooth(-18.2,-14.2,z)*(1-smooth(-3.1,0.1,z))
def height_profile(x):
 return np.interp(x,[3.8,4.6,5.4,6.2,7.2,9.2,22],[-.45,-.33,-.23,-.13,.02,.86,.86])
x=coords[:,0];z=-coords[:,1];w=influence(x,z)
newcoords=coords.copy();newcoords[:,2]=coords[:,2]*(1-w)+height_profile(x)*w
# Keep the sloping central stone trough exposed below its cross sleepers.
basin=bpy.data.objects['Combined_front_A basin foundation']
basin_bvh=BVHTree.FromPolygons([(basin.matrix_world@v.co)[:] for v in basin.data.vertices],[list(p.vertices) for p in basin.data.polygons])
for i in np.where((x>7.0)&(x<15.25)&(z>-10.53)&(z<-7.47))[0]:
 hit=basin_bvh.ray_cast(Vector((float(x[i]),float(-z[i]),20)),Vector((0,0,-1)))[0]
 if hit:newcoords[i,2]=min(newcoords[i,2],hit.z-.065)
changed=np.where(np.abs(newcoords[:,2]-coords[:,2])>1e-6)[0]
mesh.vertices.foreach_set('co',newcoords.ravel());mesh.update()
terrain['yard26_earthwork']=True
new=BVHTree.FromPolygons(newcoords.tolist(),tri.tolist(),all_triangles=True)
def ray(bvh,x,z):
 return bvh.ray_cast(Vector((float(x),float(-z),50)),Vector((0,0,-1)),200)[0]
# Existing nonrepeating land use owns the actual material boundaries. Change
# this same local workyard field, instead of placing a second ground sheet.
im=bpy.data.images['G23_LandUse'];p=Path(bpy.path.abspath(im.filepath));backup=LOG/'before/assets/reference/G23_LandUse.png'
assert not backup.exists();backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,backup)
pix=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(pix);pix=pix.reshape(im.size[1],im.size[0],4)
np.savez_compressed(LOG/'landuse_before.npz',pixels=pix)
# Blender rows begin at image bottom; this existing map's row 0 is world Z=-15.
xx=-4+(np.arange(im.size[0])+.5)/im.size[0]*48
zz=-15+(np.arange(im.size[1])+.5)/im.size[1]*97
X,Z=np.meshgrid(xx,zz)
def yard_material(x,z):
 yard=smooth(7.1,9.3,x)*(1-smooth(21.2,22.0,x))*smooth(-15.0,-13.7,z)*(1-smooth(-2.8,-.8,z))
 # The side approach shares the public street and leads to the stone side treads.
 approach=smooth(9.2,10.2,x)*(1-smooth(15.7,17.1,x))*smooth(-5.2,-3.7,z)*(1-smooth(-1.0,.2,z))
 return np.maximum(yard,approach)
pw=yard_material(X,Z);roles=np.zeros_like(pix);roles[:,:,2]=.84;roles[:,:,3]=.16
# Between sea and work slab keep sand. Rounded terrace shoulders retain grass.
beach=smooth(4.0,5.0,X)*(1-smooth(7.8,9.3,X))*smooth(-15.0,-13.4,Z)*(1-smooth(-4.0,-2.2,Z))
result=pix*(1-pw[:,:,None])+roles*pw[:,:,None]
result*=1-beach[:,:,None]*.95
modified=int(np.count_nonzero(np.max(abs(result-pix),axis=2)>1e-6))
im.pixels.foreach_set(result.ravel());im.update();im.filepath_raw=str(p);im.file_format='PNG';im.save()
if im.packed_file:im.unpack(method='REMOVE')
im.pack()
# Vertex fallback follows the same site, including the tiny northern section
# outside the texture's world extent.
attr=mesh.color_attributes['LandUse']
for loop in mesh.loops:
 v=newcoords[loop.vertex_index];q=float(yard_material(v[0],-v[1]));be=float(smooth(4,5,v[0])*(1-smooth(7.8,9.3,v[0]))*smooth(-15,-13.4,-v[1])*(1-smooth(-4,-2.2,-v[1])))
 if q>.00001 or be>.00001:
  a=attr.data[loop.index];a.color=tuple((np.array(a.color)*(1-q)+np.array([0,0,.84,.16])*q)*(1-be*.95))
# Reconcile disconnected ground plants with the actual resulting surface.
grass=[];allowed=[terrain.name]
for name in ['L24_GrassTuftClusters','G23_RootedGrassMargins','G23_EmbeddedSlopeFragments']:
 ob=bpy.data.objects.get(name)
 if not ob:continue
 bm=bmesh.new();bm.from_mesh(ob.data);todo=set(bm.verts);remove=[];moved=0;removed=0
 while todo:
  start=next(iter(todo));group={start};queue=[start]
  while queue:
   v=queue.pop()
   for e in v.link_edges:
    vv=e.other_vert(v)
    if vv not in group:group.add(vv);queue.append(vv)
  todo-=group
  pts=[ob.matrix_world@v.co for v in group];center=sum(pts,Vector())/len(pts);gx,gz=center.x,-center.y
  if float(influence(gx,gz))<.00001:continue
  if float(yard_material(gx,gz))>.12 or (gx<9.4 and -14.5<gz<-3.3):
   remove.extend(group);removed+=1;continue
  a=ray(old,gx,gz);b=ray(new,gx,gz)
  if a and b and abs(b.z-a.z)>1e-5:
   shift=ob.matrix_world.to_3x3().inverted()@Vector((0,0,b.z-a.z))
   for v in group:v.co+=shift
   moved+=1
 if remove:bmesh.ops.delete(bm,geom=remove,context='VERTS')
 if removed or moved:
  ob.data=ob.data.copy();ob.data.name=name+'_Y26';bm.to_mesh(ob.data);ob.data.update();allowed.append(name)
 bm.free();grass.append({'name':name,'removed_components':removed,'regrounded_components':moved})
# Simple topological and protected-coordinate check; only Z has changed.
edges={}
for t in tri:
 for a,b in zip(t,np.roll(t,-1)):
  k=tuple(sorted((int(a),int(b))));edges[k]=edges.get(k,0)+1
boundary={i for e,n in edges.items() if n==1 for i in e}
boundary_changed=[i for i in boundary if abs(float(newcoords[i,2]-coords[i,2]))>1e-6]
assert not boundary_changed,boundary_changed
assert np.isfinite(newcoords).all() and np.array_equal(newcoords[:,:2],coords[:,:2])
r={'allowed_changed_names':allowed,'terrain_vertices':len(coords),'terrain_triangles':len(tri),'changed_vertices':len(changed),'height_delta_range':[float((newcoords-coords)[:,2].min()),float((newcoords-coords)[:,2].max())],'boundary_edges':sum(n==1 for n in edges.values()),'new_boundary_edges':0,'nonmanifold_edges':sum(n>2 for n in edges.values()),'changed_boundary_vertices':boundary_changed,'landuse_changed_pixels':modified,'landuse_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'grass':grass,'saved':False}
(LOG/'ground_mutation.json').write_text(json.dumps(r,indent=2),encoding='utf8');print(json.dumps(r))
