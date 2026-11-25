"""Read-only current terrain/shipyard contact check after export."""
import bpy,os,json,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/shipyard_integration_20261126'
assert os.getpid()==29492 and bpy.types.blendermcp_server.port==9881
t=bpy.data.objects['C25_ContourBuiltCoast'];p=np.array([v.co[:] for v in t.data.vertices]);tri=np.array([f.vertices[:] for f in t.data.polygons]);bvh=BVHTree.FromPolygons(p.tolist(),tri.tolist(),all_triangles=True)
before=np.load(LOG/'terrain_before.npz');bp=before['positions'];bt=before['triangles']
old_bvh=BVHTree.FromPolygons(bp.tolist(),bt.tolist(),all_triangles=True)
def areas(a):return np.linalg.norm(np.cross(a[tri[:,1]]-a[tri[:,0]],a[tri[:,2]]-a[tri[:,0]]),axis=1)*.5
a=areas(p);ba=areas(bp);new_bad=np.where((a<1e-10)&(ba>=1e-10))[0]
def height(x,z):
 hit=bvh.ray_cast(Vector((float(x),float(-z),30)),Vector((0,0,-1)),200)[0];assert hit
 return hit.z
floor=[height(x,z) for x in np.linspace(15.2,20.7,12) for z in np.linspace(-12.8,-5.2,15)]
yard=bpy.data.collections['Reference_Shipyard'];wet=[]
for ob in yard.all_objects:
 if ob.type!='MESH' or not ('slip ramp tread' in ob.name or 'submerged slip tread' in ob.name):continue
 pts=np.array([(ob.matrix_world@v.co)[:] for v in ob.data.vertices]);lo=pts.min(0);hi=pts.max(0)
 heights=[height(x,-y) for x in np.linspace(lo[0]+.02,hi[0]-.02,3) for y in np.linspace(lo[1]+.02,hi[1]-.02,7)]
 wet.append({'name':ob.name,'top':float(hi[2]),'bottom':float(lo[2]),'seabed_max':max(heights),'minimum_top_clearance':float(hi[2])-max(heights)})
basin=bpy.data.objects['Combined_front_A basin foundation'];bv=BVHTree.FromPolygons([(basin.matrix_world@v.co)[:] for v in basin.data.vertices],[list(f.vertices) for f in basin.data.polygons]);margin=[]
for x in np.linspace(7.1,15.1,40):
 for z in np.linspace(-10.4,-7.6,15):
  hit=bv.ray_cast(Vector((float(x),float(-z),30)),Vector((0,0,-1)))[0]
  if hit:margin.append(hit.z-height(x,z))
im=bpy.data.images['G23_LandUse'];file=Path(bpy.path.abspath(im.filepath))
r={'pid':os.getpid(),'dirty':bpy.data.is_dirty,'terrain_vertices':len(p),'terrain_triangles':len(tri),'new_degenerate_triangles':len(new_bad),'same_xy':bool(np.array_equal(p[:,:2].astype(np.float32),bp[:,:2])),'same_topology':bool(np.array_equal(tri,bt)),'workshop_floor_top':1.1,'under_workshop_ground_min':min(floor),'under_workshop_ground_max':max(floor),'trough_samples':len(margin),'trough_minimum_ground_clearance':min(margin),'slip_treads':wet,'landuse_packed_matches_disk':hashlib.sha256(bytes(im.packed_file.data)).digest()==hashlib.sha256(file.read_bytes()).digest(),'active_shipyard_meshes':len([o for o in yard.all_objects if o.type=='MESH'])}
support=[]
for cname in ['Reference_Coast','Reference_Town']:
 for ob in bpy.data.collections[cname].all_objects:
  if ob.type!='MESH' or not ob.name.startswith(('Hut_Floor','Town_Floor')):continue
  points=[ob.matrix_world@v.co for v in ob.data.vertices];points.append(sum(points,Vector())/len(points))
  changes=[]
  for q in points:
   if not (4<q.x<26.2 and -2<q.y<18.2):continue
   oldhit=old_bvh.ray_cast(Vector((q.x,q.y,30)),Vector((0,0,-1)),200)[0]
   if oldhit:changes.append(height(q.x,-q.y)-oldhit.z)
  if changes:support.append({'name':ob.name,'samples':len(changes),'max_support_height_change':max(abs(v) for v in changes)})
r['existing_floor_support']=support
(LOG/'contact_audit.json').write_text(json.dumps(r,indent=2),encoding='utf8');print(json.dumps(r))
assert not len(new_bad) and r['same_xy'] and r['same_topology']
assert max(floor)<1.1 and min(margin)>0
assert all(q['minimum_top_clearance']>0 for q in wet)
assert r['landuse_packed_matches_disk']
assert all(q['max_support_height_change']<.04 for q in support)
