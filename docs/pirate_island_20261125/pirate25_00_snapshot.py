import bpy,os,json,hashlib,shutil,numpy as np
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/pirate_island_20261125'
assert os.getpid()==1028 and not bpy.app.background and bpy.types.blendermcp_server.port==9881
assert not (LOG/'before_manifest.json').exists()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(bpy.data.filepath)=='b2e3a5fdabf16d0c2092884b2ee84334e7f32c7226670a34b51181822f6eca12'
paths=[Path(bpy.data.filepath),ROOT/'environment/reference_coast.gd',ROOT/'environment/reference_environment.gd',ROOT/'materials/landform_mass.gdshader',ROOT/'fleet_harbor.gd',ROOT/'fleet_harbor.tscn']
paths+=list((ROOT/'fleet').glob('*.gd'))+list((ROOT/'assets/reference').glob('*.glb'))+[ROOT/'assets/reference/shore_relief_height.json']
manifest=[]
for p in paths:
 rel=p.relative_to(ROOT);target=LOG/'before'/rel;target.parent.mkdir(parents=True,exist_ok=True)
 assert not target.exists(),str(target)
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
rows=[{'name':o.name,'collection':c.name,'digest':digest(o)} for c in bpy.data.collections if c.name.startswith('Reference_') and not c.hide_render for o in c.objects if o.type=='MESH']
(LOG/'objects_before.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
report={'pid':os.getpid(),'port':9881,'source':bpy.data.filepath,'sha256':sha(bpy.data.filepath),'dirty':bpy.data.is_dirty,'objects':len(rows),'backup_files':len(manifest),'blender':bpy.app.version_string}
(LOG/'session_start.json').write_text(json.dumps(report,indent=2),encoding='utf8')
materials=[]
for m in bpy.data.materials:
 if m.name.startswith(('Ref_','C25')):
  p=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) if m.use_nodes else None
  materials.append({'name':m.name,'images':[n.image.name for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] if m.use_nodes else [],'color':list(p.inputs['Base Color'].default_value) if p else None})
(LOG/'materials_before.json').write_text(json.dumps(materials,indent=2),encoding='utf8')
bpy.app.driver_namespace['pirate25_digest']=digest
print(json.dumps(report));print(json.dumps(materials))
