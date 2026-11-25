import bpy, os, json
from pathlib import Path
from mathutils import Vector
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/terminal_rebuild_20261125'
LOG.mkdir(exist_ok=True)
(LOG/'.gdignore').write_text('# Task evidence and backups only.\n',encoding='utf8')
assert os.getpid()==13812 and not bpy.app.background and bpy.types.blendermcp_server.port==9881
rows=[]
for colname in ['Reference_Coast','Reference_Foliage','Reference_Rocks']:
 for o in bpy.data.collections[colname].all_objects:
  if o.type!='MESH':continue
  b=[o.matrix_world@Vector(c) for c in o.bound_box]
  lo=[min(v[i] for v in b) for i in range(3)];hi=[max(v[i] for v in b) for i in range(3)]
  if hi[1]>21 and lo[1]<31 and hi[0]>-11 and lo[0]<8:
   rows.append({'name':o.name,'collection':colname,'bounds':[lo,hi],'props':{k:str(o[k]) for k in o.keys()},'materials':[m.name if m else '' for m in o.data.materials]})
report={'pid':os.getpid(),'port':bpy.types.blendermcp_server.port,'source':bpy.data.filepath,'dirty':bpy.data.is_dirty,'blender':bpy.app.version_string,'objects':rows,'collections':[c.name for c in bpy.data.collections if c.name.startswith('Reference_')],'materials':[m.name for m in bpy.data.materials if m.name.startswith(('Ref_TR20','Ref_D19','Ref_Town','Ref_Glass','Ref_Rope'))]}
(LOG/'inspect.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'pid':report['pid'],'port':report['port'],'source':report['source'],'dirty':report['dirty'],'local_objects':len(rows),'floors':[r for r in rows if 'Floor' in r['name']],'materials':report['materials']},ensure_ascii=False))
