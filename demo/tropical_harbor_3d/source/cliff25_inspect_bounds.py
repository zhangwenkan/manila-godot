import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/cliff_contacts_20261125'
known={r['name']:r for r in json.loads((LOG/'objects_before.json').read_text())}
rows=[]
for o in bpy.data.collections['Reference_Town'].objects:
    if o.type!='MESH':continue
    old=known.get(o.name)
    if old is None:rows.append({'name':o.name,'kind':'absent_from_baseline'});continue
    matrix=np.array(o.matrix_world,float);box=np.asarray(o.bound_box,float)@matrix[:3,:3].T+matrix[:3,3]
    float_box=np.array([o.matrix_world@Vector(v) for v in o.bound_box])
    delta=np.max(abs(np.array([box.min(0),box.max(0)])-old['bounds']))
    exact_delta=np.max(abs(np.array([float_box.min(0),float_box.max(0)])-old['bounds']))
    md=np.max(abs(matrix-old['matrix']))
    if delta>1e-6 or md>1e-6 or len(o.data.vertices)!=old['vertices']:rows.append({'name':o.name,'double_bounds_error':float(delta),'original_method_bounds_error':float(exact_delta),'matrix_error':float(md),'vertices_same':len(o.data.vertices)==old['vertices']})
(LOG/'bounds_diagnosis.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print(json.dumps({'changes':len(rows),'max_error':max([r.get('double_bounds_error',0) for r in rows],default=0),'max_original_method_error':max([r.get('original_method_bounds_error',0) for r in rows],default=0),'matrix_errors':[r for r in rows if r.get('matrix_error',0)>0],'first':rows[:8]}))
