"""Read-only snapshot for the road contact correction, via owned GUI MCP."""
import bpy,json,os,numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/road_contacts_20261123'
o=bpy.data.objects['C25_ContourBuiltCoast'];m=o.data
assert o.get('ground23_integrated_shoulders')
assert len(m.vertices)==66230 and len(m.polygons)==114226
p=np.array([v.co[:] for v in m.vertices],np.float32)
np.savez_compressed(str(LOG/'baseline.npz'),positions=p,loops=np.array([l.vertex_index for l in m.loops],np.int32),
    starts=np.array([f.loop_start for f in m.polygons]),sizes=np.array([f.loop_total for f in m.polygons]),
    colors=np.array([c.color[:] for c in m.color_attributes['LandUse'].data],np.float32),
    normals=np.array([v.normal[:] for v in m.vertices],np.float32))
rows=[];seen=set()
for cn in ('Reference_Town','Reference_Coast','Reference_Foliage','Reference_Rocks'):
    for ob in bpy.data.collections[cn].all_objects:
        if ob.name in seen or ob.type!='MESH' or ob.hide_render or any(c.name.startswith('Archive') for c in ob.users_collection):continue
        seen.add(ob.name)
        corners=[ob.matrix_world@Vector(v) for v in ob.bound_box]
        lo=[min(v[a] for v in corners) for a in range(3)];hi=[max(v[a] for v in corners) for a in range(3)]
        if any(s.lower() in ob.name.lower() for s in ('floor','step','deck','platform','foundation','trunk','rock','bush','bench','supply','barrel','crate','net')):
            rows.append({'name':ob.name,'collection':cn,'bounds_blender':[lo,hi], 'origin_blender':list(ob.matrix_world.translation)})
(LOG/'active_footprints.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
report={'pid':os.getpid(),'file':bpy.data.filepath,'port':bpy.types.blendermcp_server.port,'dirty':bpy.data.is_dirty,'vertices':len(p),'triangles':len(m.polygons),'footprints':len(rows)}
(LOG/'session_start.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
