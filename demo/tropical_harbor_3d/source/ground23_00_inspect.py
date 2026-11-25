import bpy, json, os, numpy as np
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/ground_integration_20261123'
o=bpy.data.objects['C25_ContourBuiltCoast'];m=o.data
p=np.array([v.co[:] for v in m.vertices],np.float32)
l=np.array([l.vertex_index for l in m.loops],np.int32)
c=np.array([c.color[:] for c in m.color_attributes['LandUse'].data],np.float32)
norm=np.array([v.normal[:] for v in m.vertices],np.float32)
np.savez_compressed(str(LOG/'baseline.npz'),positions=p,loops=l,colors=c,normals=norm,starts=np.array([f.loop_start for f in m.polygons]),sizes=np.array([f.loop_total for f in m.polygons]))
summary={'pid':os.getpid(),'file':bpy.data.filepath,'port':bpy.types.blendermcp_server.port,'dirty':bpy.data.is_dirty,'vertices':len(p),'faces':len(m.polygons),'bounds':[p.min(axis=0).tolist(),p.max(axis=0).tolist()],'collections':[(c.name,len(c.objects)) for c in bpy.data.collections if c.name.startswith('Reference')], 'grass':[(ob.name,len(ob.data.polygons)) for ob in bpy.data.objects if ob.type=='MESH' and 'Grass' in ob.name and not ob.hide_render]}
(LOG/'session_start.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
print(json.dumps(summary))
