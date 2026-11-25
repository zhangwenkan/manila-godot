"""New immutable baseline, executed only in the verified GUI Blender MCP."""
import bpy, os, json, hashlib, shutil, numpy as np
from pathlib import Path
from mathutils import Vector
assert os.getpid()==9864 and not bpy.app.background
assert bpy.types.blendermcp_server.port==9881
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/cliff_contacts_20261125'
LOG.mkdir(exist_ok=True)
assert not (LOG/'baseline.npz').exists(), 'Do not overwrite the cliff25 baseline'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(bpy.data.filepath)=='791081d9a9b653e63523396c660b636d53c4c191bc1301a2d093044d801973d2'
paths=[Path(bpy.data.filepath),ROOT/'materials/landform_mass.gdshader',ROOT/'environment/reference_environment.gd',ROOT/'environment/harbor_environment.gd',ROOT/'fleet_harbor.gd',ROOT/'fleet_harbor.tscn']
paths+=list((ROOT/'fleet').glob('*.gd'))
paths+=list((ROOT/'assets/reference').glob('*.glb'))
paths+=list((ROOT/'assets/reference').glob('G23_*'))
paths+=[ROOT/'assets/reference/shore_relief_height.json']
manifest=[]
for p in paths:
    assert p.is_file(), str(p)
    rel=p.relative_to(ROOT); dest=LOG/'before'/rel
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    manifest.append({'path':str(p),'relative':rel.as_posix(),'sha256':sha(p)})
(LOG/'before_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
ob=bpy.data.objects['C25_ContourBuiltCoast'];m=ob.data
p=np.empty((len(m.vertices),3),np.float32);m.vertices.foreach_get('co',p.ravel())
previous=np.load(ROOT/'captures/terrain_structure_20261123/slope_cleanup.npz')
previous_positions=previous['positions']
assert np.max(np.abs(previous_positions-p))<0.00001, 'Live geometry differs from last saved final'
idx=np.empty(len(m.loops),np.int32);m.loops.foreach_get('vertex_index',idx)
colors=np.array([c.color[:] for c in m.color_attributes['LandUse'].data],np.float32)
normals=np.array([v.normal[:] for v in m.vertices],np.float32)
np.savez_compressed(LOG/'baseline.npz',positions=p,triangles=idx.reshape(-1,3),colors=colors,normals=normals)
active={}
def collect(c):
    if c.hide_render or c.name.startswith('Archive_'):return
    for o in c.objects:
        if not o.hide_render:active[o.name]=o
    for child in c.children:collect(child)
for n in ('Reference_Town','Reference_Coast','Reference_Foliage','Reference_Rocks','Reference_GroundCover'):collect(bpy.data.collections[n])
objects=[]
for o in active.values():
    if o.type!='MESH':continue
    bounds=np.array([o.matrix_world@Vector(v) for v in o.bound_box])
    objects.append({'name':o.name,'matrix':np.asarray(o.matrix_world).tolist(),'bounds':[bounds.min(0).tolist(),bounds.max(0).tolist()],'collections':[c.name for c in o.users_collection],'vertices':len(o.data.vertices)})
(LOG/'objects_before.json').write_text(json.dumps(objects,indent=2),encoding='utf8')
for name in ('design.json','foundations.json'):
    src=ROOT/'captures/terrain_structure_20261123'/name
    if src.exists():shutil.copy2(src,LOG/name)
summary={'pid':os.getpid(),'port':9881,'file':bpy.data.filepath,'dirty':bpy.data.is_dirty,'vertices':len(p),'triangles':len(idx)//3,'active_objects':len(objects),'backup_files':len(manifest),'source_sha256':sha(bpy.data.filepath),'blender':bpy.app.version_string}
(LOG/'session_start.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
print(json.dumps(summary))
