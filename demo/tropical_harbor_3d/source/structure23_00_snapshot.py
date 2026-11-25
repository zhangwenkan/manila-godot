"""Inspect and snapshot the owned GUI session before the structural rebuild."""
import bpy, os, json, hashlib, shutil, numpy as np
from pathlib import Path
assert not bpy.app.background
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/terrain_structure_20261123'
LOG.mkdir(exist_ok=True)
assert not (LOG/'baseline.npz').exists(), 'Do not overwrite the structural baseline'
BEFORE=LOG/'before';BEFORE.mkdir(exist_ok=True)
paths=[Path(bpy.data.filepath),ROOT/'reference_environment.gd',ROOT/'materials/landform_mass.gdshader']
paths+=list((ROOT/'assets/reference').glob('*.glb'))
paths+=list((ROOT/'assets/reference').glob('G23_*'))
paths+=[ROOT/'assets/reference/shore_relief_height.json']
manifest=[]
for p in paths:
    if not p.is_file():continue
    rel=p.relative_to(ROOT);dest=BEFORE/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    manifest.append({'path':str(p),'relative':str(rel),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(LOG/'before_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
ob=bpy.data.objects['C25_ContourBuiltCoast'];m=ob.data
p=np.array([v.co[:] for v in m.vertices],np.float32);idx=np.array([l.vertex_index for l in m.loops],np.int32)
np.savez_compressed(LOG/'baseline.npz',positions=p,triangles=idx.reshape(-1,3),colors=np.array([c.color[:] for c in m.color_attributes['LandUse'].data],np.float32),normals=np.array([v.normal[:] for v in m.vertices],np.float32))
active={}
def collect(col):
    if col.hide_render or col.name.startswith('Archive_'):return
    for o in col.objects:
        if not o.hide_render:active[o.name]=o
    for c in col.children:collect(c)
for n in ('Reference_Town','Reference_Coast','Reference_Foliage','Reference_Rocks','Reference_GroundCover'):collect(bpy.data.collections[n])
objects=[]
for o in active.values():
    if o.type!='MESH':continue
    from mathutils import Vector
    bounds=np.array([o.matrix_world@Vector(v) for v in o.bound_box])
    objects.append({'name':o.name,'matrix':np.array(o.matrix_world).tolist(),'bounds':[bounds.min(0).tolist(),bounds.max(0).tolist()],'collections':[c.name for c in o.users_collection],'vertices':len(o.data.vertices)})
(LOG/'objects_before.json').write_text(json.dumps(objects,indent=2),encoding='utf8')
summary={'pid':os.getpid(),'port':bpy.types.blendermcp_server.port,'file':bpy.data.filepath,'dirty':bpy.data.is_dirty,'vertices':len(p),'triangles':len(idx)//3,'active_objects':len(objects),'backup_files':len(manifest),'blender':bpy.app.version_string}
(LOG/'session_start.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(json.dumps(summary))
