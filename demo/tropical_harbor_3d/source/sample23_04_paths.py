# Authored routes and local grading. Execute once through guarded Blender MCP.
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/rock_path_sample_20261123'
terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
assert terrain.get('sample23_forms') and not terrain.get('sample23_paths')
pos=np.array([v.co[:] for v in mesh.vertices],np.float32);before=pos.copy()
bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
def ground(x,z):
 hit=bvh.ray_cast(Vector((x,-z,80)),Vector((0,0,-1)),200)[0]
 return float(hit.z)
def ss(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
routes=[
 {'name':'lower_lane','halfwidth':.68,'grade':False,'points':[(12.9,20),(12.8,22),(12.9,24),(13.4,26.5),(14,29),(14.6,32),(14.1,34.5),(12.6,36.5),(10.4,37.7),(10.15,40.2),(10.5,43.7),(12.0,46.5)]},
 {'name':'chapel_ramp','halfwidth':.60,'grade':True,'points':[(12.9,20),(16.8,19.8),(19,20.2),(21.2,20),(23,19.6),(24,19),(24,17.8),(22.8,16.8),(22.3,15.4),(22.3,14.7)],'end_height':4.08},
 {'name':'clinic_ramp','halfwidth':.64,'grade':True,'points':[(14.6,32),(17,33.3),(19.4,33.4),(21.7,33.3),(23.8,32.8),(24.4,32.2),(22.9,31.6),(22.1,30.6),(22.1,29.6),(22.2,28.4)],'end_height':4.36},
 {'name':'chapel_entry','halfwidth':.53,'grade':False,'points':[(22.3,14.7),(23.46,14.8)]},
 {'name':'clinic_entry','halfwidth':.55,'grade':False,'points':[(22.2,28.4),(23.12,28.48)]},
 {'name':'restaurant_entry','halfwidth':.60,'grade':False,'points':[(12.9,24),(14.65,23.86)]},
 {'name':'chapel_north_connection','halfwidth':.55,'grade':False,'points':[(22.3,14.7),(22.0,12.2),(23.2,10)]},
 {'name':'clinic_side_hut_entry','halfwidth':.45,'grade':False,'points':[(21.7,33.3),(22.1,34.3),(22.55,36.3)]}
]
def nearest(x,z,points):
 best=(1e8,0.,0)
 for i,(a,b) in enumerate(zip(points,points[1:])):
  dx,dz=b[0]-a[0],b[1]-a[1];q=np.clip(((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz),0,1)
  dist=np.hypot(x-a[0]-q*dx,z-a[1]-q*dz)
  if dist<best[0]:best=(float(dist),float(q),i)
 return best
def poly_dist(x,z,p):
 inside=False;d=1e5
 for a,b in zip(p,p[1:]+p[:1]):
  if ((a[1]>z)!=(b[1]>z)) and x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]:inside=not inside
  dx,dz=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz)))
  d=min(d,math.hypot(x-a[0]-t*dx,z-a[1]-t*dz))
 return 0 if inside else d
floors=[]
for f in json.loads((LOG/'foundations.json').read_text()):floors.append([(p[0],-p[1]) for p in f['corners'][:4]])
for rec in json.loads((LOG/'door_hut_contacts.json').read_text()):
 if rec['object'].startswith('Hut_Floor'):
  pts=list(set((p[0],p[2]) for p in rec['corners_godot']));cx,cz=rec['center_godot'][0],rec['center_godot'][2]
  floors.append(sorted(pts,key=lambda p:math.atan2(p[1]-cz,p[0]-cx)))
for r in routes:
 heights=[ground(*p) for p in r['points']]
 lens=np.array([0]+[math.dist(a,b) for a,b in zip(r['points'],r['points'][1:])]).cumsum()
 if r['grade']:
  # The slope spans the whole approach, not the last 1 m of a former ledge.
  h0=heights[0];h1=r['end_height'];t=lens/lens[-1]
  target=h0+(h1-h0)*(t*.75+ss(0,1,t)*.25)
  target[-1]=h1
 else:target=heights
 r['heights_before']=heights;r['target_heights']=[float(v) for v in target]
 if not r['grade']:continue
 for i,(x,y,h) in enumerate(pos):
  z=-float(y);x=float(x)
  if not 11<x<26 or not 13<z<35:continue
  d,t,j=nearest(x,z,r['points'])
  if d>r['halfwidth']+1.05:continue
  protection=float(ss(.10,.65,min(poly_dist(x,z,p) for p in floors)))
  w=(1-float(ss(r['halfwidth']-.10,r['halfwidth']+1.05,d)))*protection
  wanted=target[j]*(1-t)+target[j+1]*t
  pos[i,2]=h+(wanted-h)*w
# Fill only immediately below four existing threshold stones, never move buildings.
steps=[]
for rec in json.loads((LOG/'door_hut_contacts.json').read_text()):
 if rec['object'] not in ['Town_Step.002','Town_Step.004','Town_Step.005','Town_Step.008']:continue
 pts=list(set((p[0],p[2]) for p in rec['corners_godot']));cx,cz=rec['center_godot'][0],rec['center_godot'][2]
 polygon=sorted(pts,key=lambda p:math.atan2(p[1]-cz,p[0]-cx));height=min(p[1] for p in rec['corners_godot'])+.008
 moved=0
 for i,(x,y,h) in enumerate(pos):
  if abs(x-cx)>1.5 or abs(-y-cz)>2:continue
  d=poly_dist(float(x),float(-y),polygon)
  if d>.85:continue
  w=1-float(ss(.18,.85,d));target=max(float(h),height)
  pos[i,2]=h+(target-h)*w;moved+=abs(pos[i,2]-h)>.001
 steps.append({'object':rec['object'],'target':height,'vertices':int(moved)})
mesh.vertices.foreach_set('co',pos.ravel());mesh.update()
loops=np.array([l.vertex_index for l in mesh.loops])
mesh.uv_layers['RockRegion'].data.foreach_set('uv',np.column_stack(((-pos[loops,1]-10)/37,(pos[loops,2]-.7)/4.4)).astype(np.float32).ravel())
terrain['sample23_paths']=True
(LOG/'routes.json').write_text(json.dumps(routes,indent=2),encoding='utf8')
(LOG/'grading.json').write_text(json.dumps({'changed_vertices':int(np.sum(abs(pos[:,2]-before[:,2])>.001)),'min_delta':float(np.min(pos[:,2]-before[:,2])),'max_delta':float(np.max(pos[:,2]-before[:,2])),'step_supports':steps},indent=2),encoding='utf8')
print((LOG/'grading.json').read_text())
