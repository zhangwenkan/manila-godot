# Revise this turn's route grading from its own saved pre-road snapshot.
import bpy,json,math,numpy as np
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/rock_path_sample_20261123'
terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
assert terrain.get('sample23_paths') and not terrain.get('sample23_grades_refined')
# Definitions are from this turn's scoped operation; the old mutation block is not replayed.
src=(ROOT/'source/sample23_04_paths.py').read_text(encoding='utf8')
exec(src[src.index('def ss('):src.index('routes=[')],globals())
exec(src[src.index('def nearest('):src.index('for r in routes:')],globals())
pos=np.load(str(LOG/'terrain_after_forms.npz'))['positions'].copy();before=pos.copy()
routes=json.loads((LOG/'routes.json').read_text())
for r in routes:
 if r['name']=='lower_lane':r['points']=r['points'][:9];r['halfwidth']=.62
 if r['name']=='chapel_ramp':r['target_heights']=[1.22,1.22,1.35,1.85,2.42,2.80,3.20,3.65,3.98,4.08]
 if r['name']=='clinic_ramp':
  r['points']=[(14.6,32),(17,33.3),(19.4,33.4),(21.7,33.3),(23.8,32.8),(24.4,32.2),(24.1,31.65),(22.8,31.0),(21.8,30.5),(21.8,29.4),(22.2,28.4)]
  r['target_heights']=[1.40,1.35,1.50,1.98,2.72,3.05,3.40,3.75,4.03,4.29,4.29]
 if not r['grade']:continue
 for i,(x,y,h) in enumerate(pos):
  z=-float(y);x=float(x)
  if not 11<x<26 or not 13<z<35:continue
  d,t,j=nearest(x,z,r['points'])
  if d>r['halfwidth']+1.05:continue
  protection=float(ss(.10,.65,min(poly_dist(x,z,p) for p in floors)))
  weight=(1-float(ss(r['halfwidth']-.10,r['halfwidth']+1.05,d)))*protection
  target=r['target_heights'][j]*(1-t)+r['target_heights'][j+1]*t
  pos[i,2]=h+(target-h)*weight
# Four exact stone threshold supports, spatially limited to the stone's footprint.
steps=[]
for rec in json.loads((LOG/'door_hut_contacts.json').read_text()):
 if rec['object'] not in ['Town_Step.002','Town_Step.004','Town_Step.005','Town_Step.008']:continue
 pts=list(set((p[0],p[2]) for p in rec['corners_godot']));cx,cz=rec['center_godot'][0],rec['center_godot'][2]
 polygon=sorted(pts,key=lambda p:math.atan2(p[1]-cz,p[0]-cx));height=min(p[1] for p in rec['corners_godot'])+.008
 for i,(x,y,h) in enumerate(pos):
  if abs(x-cx)>1.5 or abs(-y-cz)>2:continue
  d=poly_dist(float(x),float(-y),polygon)
  if d>.85:continue
  weight=1-float(ss(.18,.85,d));pos[i,2]=h+(max(float(h),height)-h)*weight
mesh.vertices.foreach_set('co',pos.ravel());mesh.update()
loops=np.array([l.vertex_index for l in mesh.loops])
mesh.uv_layers['RockRegion'].data.foreach_set('uv',np.column_stack(((-pos[loops,1]-10)/37,(pos[loops,2]-.7)/4.4)).astype(np.float32).ravel())
(LOG/'routes.json').write_text(json.dumps(routes,indent=2),encoding='utf8')
(LOG/'grading_refined.json').write_text(json.dumps({'changed_vertices':int(np.sum(abs(pos[:,2]-before[:,2])>.001)),'min_delta':float(np.min(pos[:,2]-before[:,2])),'max_delta':float(np.max(pos[:,2]-before[:,2]))},indent=2),encoding='utf8')
terrain['sample23_grades_refined']=True
print((LOG/'grading_refined.json').read_text())
