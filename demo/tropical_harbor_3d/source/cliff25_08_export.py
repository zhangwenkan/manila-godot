import bpy,os,json,numpy as np
from mathutils import Vector
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/cliff_contacts_20261125'
assert os.getpid()==9864 and bpy.types.blendermcp_server.port==9881 and not bpy.app.background
assert json.loads((LOG/'cliff_structure_audit.json').read_text())['technical_pass']
namespace={}
exec(compile((ROOT/'source/structure23_export.py').read_text(encoding='utf-8-sig'),'structure23_export.py','exec'),namespace)
# The immutable new-round snapshot used Blender float32 matrix multiplication.
# Compare bounds using that identical path, instead of a float64 conversion
# which invents 1-2 micrometre differences at otherwise untouched buildings.
def same_precision_metadata(obj):
    box=np.array([obj.matrix_world@Vector(v) for v in obj.bound_box])
    return {'matrix':np.asarray(obj.matrix_world,float).tolist(),'bounds':[box.min(0).tolist(),box.max(0).tolist()],'vertices':len(obj.data.vertices)}
namespace['_object_metadata']=same_precision_metadata
report=namespace['export_structure23'](9864,changed_collections=['Reference_Foliage','Reference_GroundCover'],only_collections=['Reference_Foliage','Reference_GroundCover'],log_path=LOG,force_terrain=True)
print(json.dumps({'status':report['status'],'source_saved':report['source_saved'],'dirty':report['dirty'],'sha':report.get('source_sha256'),'elapsed_seconds':report.get('elapsed_seconds')}))
