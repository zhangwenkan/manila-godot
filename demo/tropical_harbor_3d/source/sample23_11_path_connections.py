# Scoped door connections and a beachward lane exit. One-time live MCP operation.
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/rock_path_sample_20261123'
terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
assert not terrain.get('sample23_connections')
def ss(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def nearest(x,z,points):
 best=(1e8,0.,0)
 for i,(a,b) in enumerate(zip(points,points[1:])):
  dx,dz=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz)))
  dist=math.hypot(x-a[0]-t*dx,z-a[1]-t*dz)
  if dist<best[0]:best=(dist,t,i)
 return best
routes=json.loads((LOG/'routes.json').read_text())
for r in routes:
 if r['name']=='lower_lane':
  r['points'] += [[9.85,38.1],[9.35,38.5],[8.85,38.85],[8.1,39.1]]
 if r['name']=='clinic_entry':r['halfwidth']=.43
 if r['name']=='clinic_side_hut_entry':
  r['points']=[[21.7,33.3],[21.6,34.2],[21.55,35.2],[21.6,36.1],[22.45,36.49]];r['halfwidth']=.44;r['rounded']=False
add=[
 {'name':'chapel_side_hut_entry','halfwidth':.43,'grade':False,'points':[[24,17.8],[24,18.8],[24.45,19.35],[24.96,19.49]]},
 {'name':'rosie_entry','halfwidth':.53,'grade':False,'points':[[12.05,49.34],[13.0,49.36],[13.8,49.33]]},
 {'name':'tavern_entry','halfwidth':.48,'grade':False,'points':[[10.4,37.7],[10.9,38.7],[11.0,40.4],[11.6,40.78]]},
 {'name':'travel_entry','halfwidth':.49,'grade':False,'points':[[21.0,46.55],[22.0,46.52],[22.55,46.49]]}]
routes+=add
pos=np.array([v.co[:] for v in mesh.vertices],np.float32);before=pos.copy()
# The low entry of the two stilt huts is approached by an earthen grade, leaving their floors and stilts intact.
grade=[
 ([(21.7,33.3),(21.6,34.2),(21.55,35.2),(21.6,36.1),(22.45,36.49)],[1.98,2.46,3.00,3.54,3.95],.44),
 ([(24,17.8),(24,18.8),(24.45,19.35),(24.96,19.49)],[3.20,3.60,3.89,4.04],.43)]
for points,heights,half in grade:
 xmin=min(p[0] for p in points)-1.;xmax=max(p[0] for p in points)+1.;zmin=min(p[1] for p in points)-1.;zmax=max(p[1] for p in points)+1.
 for i,(x,y,h) in enumerate(pos):
  z=-float(y);x=float(x)
  if not xmin<x<xmax or not zmin<z<zmax:continue
  d,t,j=nearest(x,z,points)
  if d>half+.65:continue
  weight=1-float(ss(half+.05,half+.65,d));target=heights[j]*(1-t)+heights[j+1]*t
  # Only fill the entrance approach; do not cut existing support ground below huts.
  pos[i,2]=h+(max(h,target)-h)*weight
# Complete Rosie and travel office thresholds already in the sample.
stepnames=['Town_Step.001','Town_Step.003']
for o in bpy.data.collections['Reference_Coast'].all_objects:
 if o.type!='MESH' or not o.name.startswith('Hut_EntrySteps'):continue
 pts=[o.matrix_world@Vector(v) for v in o.bound_box];c=sum(pts,Vector())/8
 if any(abs(c.x-x)<.05 and abs(-c.y-z)<.05 and abs(c.z-h)<.04 for x,z,h in [(22.44397,36.49067,4.00032),(24.95671,19.49066,4.09074)]):stepnames.append(o.name)
assert len(stepnames)==4,stepnames
for name in stepnames:
 obj=bpy.data.objects[name];corners=[obj.matrix_world@Vector(v) for v in obj.bound_box]
 center=sum(corners,Vector())/8;h=min(p.z for p in corners)+.008
 inv=obj.matrix_world.inverted();localmin=np.min(np.array(obj.bound_box),axis=0);localmax=np.max(np.array(obj.bound_box),axis=0)
 for i,p in enumerate(pos):
  if abs(p[0]-center.x)>1.3 or abs(p[1]-center.y)>1.8:continue
  q=inv@Vector(p);dx=max(localmin[0]-q.x,0,q.x-localmax[0]);dy=max(localmin[1]-q.y,0,q.y-localmax[1]);d=math.hypot(dx,dy)
  if d>.65:continue
  weight=1-float(ss(.22,.65,d));pos[i,2]=p[2]+(max(float(p[2]),h)-p[2])*weight
mesh.vertices.foreach_set('co',pos.ravel());mesh.update()
(LOG/'routes.json').write_text(json.dumps(routes,indent=2),encoding='utf8')
(LOG/'connection_grading.json').write_text(json.dumps({'changed_vertices':int(np.sum(abs(pos[:,2]-before[:,2])>.001)),'min_delta':float(np.min(pos[:,2]-before[:,2])),'max_delta':float(np.max(pos[:,2]-before[:,2])),'hut_grades':grade},indent=2),encoding='utf8')
terrain['sample23_connections']=True
print((LOG/'connection_grading.json').read_text())
