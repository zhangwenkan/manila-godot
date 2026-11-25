import bpy,os,json,hashlib,shutil,numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(bpy.data.filepath).parent.parent; LOG=ROOT/'captures/terminal_rebuild_20261125'
assert os.getpid()==13812 and not bpy.app.background and bpy.types.blendermcp_server.port==9881
assert not (LOG/'before_manifest.json').exists(),'Immutable snapshot already exists'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(bpy.data.filepath)=='a8aed95ca21dec5ab8fc36c9111a5a76e65cf90e2b00d1ee15eb60a2f64c6b28'
paths=[Path(bpy.data.filepath),ROOT/'environment/reference_coast.gd',ROOT/'environment/reference_environment.gd',ROOT/'materials/landform_mass.gdshader',ROOT/'fleet_harbor.gd',ROOT/'fleet_harbor.tscn']
paths+=list((ROOT/'fleet').glob('*.gd'))+list((ROOT/'assets/reference').glob('*.glb'))+[ROOT/'assets/reference/shore_relief_height.json']
manifest=[]
for p in paths:
 rel=p.relative_to(ROOT);target=LOG/'before'/rel;target.parent.mkdir(parents=True,exist_ok=True)
 assert not target.exists(),'Backup collision: '+str(rel)
 shutil.copy2(p,target);manifest.append({'relative':rel.as_posix(),'sha256':sha(p),'bytes':p.stat().st_size})
(LOG/'before_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
def digest(o):
 h=hashlib.sha256();h.update(np.asarray(o.matrix_world,dtype=np.float64).tobytes())
 if o.type=='MESH':
  vs=np.empty(len(o.data.vertices)*3,np.float32);o.data.vertices.foreach_get('co',vs);h.update(vs.tobytes())
  ls=np.empty(len(o.data.loops),np.int32);o.data.loops.foreach_get('vertex_index',ls);h.update(ls.tobytes())
  for uv in o.data.uv_layers:
   a=np.empty(len(uv.data)*2,np.float32);uv.data.foreach_get('uv',a);h.update(a.tobytes())
  h.update('|'.join(m.name if m else '' for m in o.data.materials).encode())
 return h.hexdigest()
rows=[]
for c in bpy.data.collections:
 if not c.name.startswith('Reference_') or c.hide_render:continue
 for o in c.objects:
  if o.type!='MESH':continue
  b=[o.matrix_world@Vector(v) for v in o.bound_box]
  rows.append({'name':o.name,'collection':c.name,'digest':digest(o),'matrix':np.asarray(o.matrix_world).tolist(),'bounds':[[min(v[i] for v in b) for i in range(3)],[max(v[i] for v in b) for i in range(3)]],'vertices':len(o.data.vertices)})
(LOG/'objects_before.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
t=bpy.data.objects['C25_ContourBuiltCoast'];p=np.empty((len(t.data.vertices),3),np.float32);t.data.vertices.foreach_get('co',p.ravel())
tri=np.empty(len(t.data.loops),np.int32);t.data.loops.foreach_get('vertex_index',tri)
np.savez_compressed(LOG/'terrain_before.npz',positions=p,triangles=tri.reshape(-1,3))
report={'pid':os.getpid(),'port':9881,'source':bpy.data.filepath,'sha256':sha(bpy.data.filepath),'dirty':bpy.data.is_dirty,'objects':len(rows),'backup_files':len(manifest),'blender':bpy.app.version_string}
(LOG/'session_start.json').write_text(json.dumps(report,indent=2),encoding='utf8')
bpy.app.driver_namespace['terminal25_digest']=digest
print(json.dumps(report))
