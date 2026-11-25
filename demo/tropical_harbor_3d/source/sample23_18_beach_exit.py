# Fade the end of the low street into the beach, not a closed circular road cap.
import bpy,json,math,numpy as np,zlib,struct
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/rock_path_sample_20261123';OUT=ROOT/'assets/reference';terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
assert not terrain.get('sample23_beach_exit')
src=(ROOT/'source/sample23_05_surfaces.py').read_text(encoding='utf8');exec(src[src.index('def ss('):src.index('# Long nonrepeating')],globals())
def beach_exit(x,z):
 a=(10.9,37.9);b=(6.3,39.5);dx=b[0]-a[0];dz=b[1]-a[1]
 t=np.clip(((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz),0,1);d=np.hypot(x-a[0]-t*dx,z-a[1]-t*dz)
 radius=.70+.60*t
 return (1-ss(radius-.05,radius+.28,d))*ss(10.8,8.6,x)
data=np.load(str(LOG/'regional_surface_data.npz'));land=data['land'].copy();heightfield=data['height'].copy();nz=data['normal_z'].copy();n=len(land);v,u=np.mgrid[0:n,0:n].astype(np.float32);X=8+26*(u+.5)/n;Z=10+45*(v+.5)/n
mask=beach_exit(X,Z);land*=1-mask[:,:,None]
image=png('S23_LandUse',land,True);mesh.materials[0].node_tree.nodes['S23 regional land roles'].image=image
np.savez_compressed(str(LOG/'regional_surface_data.npz'),land=land,height=heightfield,normal_z=nz)
coords=np.array([v.co[:] for v in mesh.vertices]);indices=np.array([l.vertex_index for l in mesh.loops]);weight=beach_exit(coords[indices,0],-coords[indices,1])
colors=np.array([c.color[:] for c in mesh.color_attributes['LandUse'].data],np.float32);colors*=1-weight[:,None]
mesh.color_attributes['LandUse'].data.foreach_set('color',colors.ravel());mesh.update();terrain['sample23_beach_exit']=True
(LOG/'beach_exit.json').write_text(json.dumps({'corridor_godot_xz':[[10.9,37.9],[6.3,39.5]],'fade_to_beach_x':[10.8,8.6],'changed_color_corners':int(np.sum(weight>.001)),'height_and_topology_changed':False},indent=2),encoding='utf8')
print('Opened sandy street exit through former circular endpoint; no height changes')
