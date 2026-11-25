# One-time local form pass, executed inside the owned Blender MCP GUI.
import bpy, json, math, numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/rock_path_sample_20261123'
terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
assert not terrain.get('sample23_forms'), 'Already applied; do not replay'
base=np.load(str(LOG/'terrain_baseline.npz'))
pos=base['positions'].copy();loops=base['loops'];cols=base['colors']
vcol=np.zeros((len(pos),4),np.float32);count=np.zeros(len(pos),np.float32)
np.add.at(vcol,loops,cols);np.add.at(count,loops,1);vcol/=np.maximum(count,1)[:,None]
def ss(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def win(z,a,b,c,d):return ss(a,b,z)*(1-ss(c,d,z))
def polygon_distance(x,z,p):
 inside=False;distance=1e6
 for a,b in zip(p,p[1:]+p[:1]):
  ax,az=a;bx,bz=b
  if ((az>z)!=(bz>z)) and x<(bx-ax)*(z-az)/(bz-az)+ax:inside=not inside
  dx,dz=bx-ax,bz-az;t=max(0,min(1,((x-ax)*dx+(z-az)*dz)/(dx*dx+dz*dz)))
  distance=min(distance,math.hypot(x-ax-t*dx,z-az-t*dz))
 return 0. if inside else distance
footprints=[]
for f in json.loads((LOG/'foundations.json').read_text()):
 footprints.append([(p[0],-p[1]) for p in f['corners'][:4]])
for o in bpy.data.objects:
 if o.type=='MESH' and o.name.startswith('Hut_Floor'):
  pts=[o.matrix_world@v.co for v in o.data.vertices]
  low=min(p.z for p in pts)
  xy=[(p.x,-p.y) for p in pts if abs(p.z-low)<.001]
  if len(xy)>=4:
   cx=sum(p[0] for p in xy)/len(xy);cz=sum(p[1] for p in xy)/len(xy)
   footprints.append(sorted(set(xy),key=lambda p:math.atan2(p[1]-cz,p[0]-cx)))
changed=[]
for i,(x,y,h) in enumerate(pos):
 z=-float(y);x=float(x);h=float(h)
 a=float(win(z,21.8,23.2,29.0,30.4));b=float(win(z,36.2,37.8,43.8,45.2))
 weight=max(a,b)*float(ss(.04,.65,vcol[i,1]))
 if weight<1e-5:continue
 clearance=min(polygon_distance(x,z,p) for p in footprints)
 weight*=float(ss(.25,1.0,clearance))
 if weight<1e-5:continue
 if a>=b:
  low,high=1.22,4.23
  crest=.18+.22*math.exp(-((z-27.2)/1.8)**2)
  # Two broad shoulder levels with unequal spacing; end into adjoining faces.
  q=max(0,min(1,(h-low)/(high-low)))
  q2=float(np.interp(q,[0,.13,.34,.60,.74,.92,1],[0,.09,.42,.53,.83,.97,1]))
 else:
  low=1.65;high=float(np.interp(z,[36,38,40.5,43,45.5],[4,3.94,3.28,3.31,3.5]))
  crest=.22+.17*math.exp(-((z-38.5)/1.6)**2)
  q=max(0,min(1,(h-low)/(high-low)))
  q2=float(np.interp(q,[0,.15,.34,.61,.80,1],[0,.08,.37,.55,.91,1]))
 shoulder=math.sin(math.pi*q)**2
 pos[i,0]=x-crest*shoulder*weight
 pos[i,2]=h+((low+q2*(high-low))-h)*weight*.82
 changed.append(i)
mesh.vertices.foreach_set('co',pos.ravel());mesh.update()
bad=[]
mesh.calc_loop_triangles()
for tri in mesh.loop_triangles:
 a,b,c=[mesh.vertices[i].co for i in tri.vertices]
 if (b-a).cross(c-a).z < -1e-7:bad.append(tri.index)
assert not bad, f'Planar fold detected: {bad[:12]}'
uv0=mesh.uv_layers[0]
uv0.data.foreach_set('uv',np.column_stack(((pos[loops,0]-8)/26,(-pos[loops,1]-10)/37)).astype(np.float32).ravel())
uv1=mesh.uv_layers.get('RockRegion') or mesh.uv_layers.new(name='RockRegion')
uv1.data.foreach_set('uv',np.column_stack(((-pos[loops,1]-10)/37,(pos[loops,2]-.7)/4.4)).astype(np.float32).ravel())
terrain['sample23_forms']=True
terrain['sample23_rock_region']='Godot z10..47, height0.7..5.1; no repeat'
np.savez_compressed(str(LOG/'terrain_after_forms.npz'),positions=pos)
(LOG/'forms.json').write_text(json.dumps({'changed_vertices':len(changed),'max_position_delta':np.max(np.abs(pos-base['positions']),axis=0).tolist(),'planar_folds':len(bad),'new_triangles':0},indent=2),encoding='utf8')
print((LOG/'forms.json').read_text())
