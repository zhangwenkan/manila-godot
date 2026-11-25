"""Resume after float64 image upload failed; do not repeat the earthwork."""
import bpy,bmesh,os,json,math,shutil,hashlib,ast
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/shipyard_integration_20261126'
assert os.getpid()==29492 and bpy.types.blendermcp_server.port==9881
assert not (LOG/'ground_mutation.json').exists()
terrain=bpy.data.objects['C25_ContourBuiltCoast'];assert terrain.get('yard26_earthwork')
mesh=terrain.data;raw=np.load(LOG/'terrain_before.npz');coords=raw['positions'];tri=raw['triangles']
newcoords=np.array([v.co[:] for v in mesh.vertices],dtype=np.float32)
assert np.array_equal(newcoords[:,:2],coords[:,:2])
changed=np.where(np.abs(newcoords[:,2]-coords[:,2])>1e-6)[0];assert len(changed)>0
old=BVHTree.FromPolygons(coords.tolist(),tri.tolist(),all_triangles=True)
new=BVHTree.FromPolygons(newcoords.tolist(),tri.tolist(),all_triangles=True)
source=(ROOT.parent.parent/'docs/shipyard_integration_20261126/yard26_04_ground.py').read_text(encoding='utf8')
parsed=ast.parse(source)
defs=ast.Module(body=[n for n in parsed.body if isinstance(n,ast.FunctionDef)],type_ignores=[])
exec(compile(defs,'yard26_math_definitions','exec'),globals())
im=bpy.data.images['G23_LandUse'];p=Path(bpy.path.abspath(im.filepath));backup=LOG/'before/assets/reference/G23_LandUse.png'
assert hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(backup.read_bytes()).digest(),'Unexpected disk write after failed image upload'
pix=np.load(LOG/'landuse_before.npz')['pixels']
X,Z=np.meshgrid(-4+(np.arange(im.size[0])+.5)/im.size[0]*48,-15+(np.arange(im.size[1])+.5)/im.size[1]*97)
pw=yard_material(X,Z);roles=np.zeros_like(pix);roles[:,:,2]=.84;roles[:,:,3]=.16
beach=smooth(4,5,X)*(1-smooth(7.8,9.3,X))*smooth(-15,-13.4,Z)*(1-smooth(-4,-2.2,Z))
result=((pix*(1-pw[:,:,None])+roles*pw[:,:,None])*(1-beach[:,:,None]*.95)).astype(np.float32)
modified=int(np.count_nonzero(np.max(abs(result-pix),axis=2)>1e-6))
im.pixels.foreach_set(result.ravel());im.update();im.filepath_raw=str(p);im.file_format='PNG';im.save()
if im.packed_file:im.unpack(method='REMOVE')
im.pack()
attr=mesh.color_attributes['LandUse'];colors=np.empty(len(attr.data)*4,np.float32);attr.data.foreach_get('color',colors);colors=colors.reshape(-1,4)
ids=np.array([l.vertex_index for l in mesh.loops]);v=newcoords[ids];q=yard_material(v[:,0],-v[:,1])
be=smooth(4,5,v[:,0])*(1-smooth(7.8,9.3,v[:,0]))*smooth(-15,-13.4,-v[:,1])*(1-smooth(-4,-2.2,-v[:,1]))
cols=((colors*(1-q[:,None])+np.array([0,0,.84,.16])*q[:,None])*(1-be[:,None]*.95)).astype(np.float32)
attr.data.foreach_set('color',cols.ravel())
# Only the remaining grass reconciliation and audit section executes.
tail=source[source.index('grass=[];allowed=[terrain.name]'):]
exec(compile(tail,'yard26_finish_ground_tail','exec'),globals())
