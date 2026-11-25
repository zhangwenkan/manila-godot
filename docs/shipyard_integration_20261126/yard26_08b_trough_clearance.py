"""Give the coarse ground triangles clearance below the finer stone trough."""
import bpy,os,json,shutil
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/shipyard_integration_20261126'
assert os.getpid()==29492 and bpy.types.blendermcp_server.port==9881
assert not (LOG/'trough_clearance_revision.json').exists()
shutil.copy2(LOG/'contact_audit.json',LOG/'contact_audit_before_trough_fix.json')
ob=bpy.data.objects['Combined_front_A basin foundation'];bv=BVHTree.FromPolygons([(ob.matrix_world@v.co)[:] for v in ob.data.vertices],[list(f.vertices) for f in ob.data.polygons])
t=bpy.data.objects['C25_ContourBuiltCoast'];changed=[]
for v in t.data.vertices:
 x,z=v.co.x,-v.co.y
 if not (6.7<x<15.6 and -10.88<z<-7.12):continue
 sx=max(7.06,min(15.19,x));hit=bv.ray_cast(Vector((sx,9,30)),Vector((0,0,-1)))[0]
 assert hit is not None
 desired=hit.z-.18
 if v.co.z>desired:
  changed.append([v.index,v.co.z,desired]);v.co.z=desired
t.data.update();bpy.context.view_layer.update()
r={'changed_vertices':len(changed),'maximum_lowering':max(q[1]-q[2] for q in changed),'vertices':changed,'saved':False}
(LOG/'trough_clearance_revision.json').write_text(json.dumps(r,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in r.items() if k!='vertices'}))
exec(compile((ROOT.parent.parent/'docs/shipyard_integration_20261126/yard26_07_contact_audit.py').read_text(encoding='utf8'),'current_contact_audit','exec'),globals())
