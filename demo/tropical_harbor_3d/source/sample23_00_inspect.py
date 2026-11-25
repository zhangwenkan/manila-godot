# Read-only scene snapshot. Run only through this task's guarded Blender MCP.
import bpy, os, json, numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/rock_path_sample_20261123'
terrain=bpy.data.objects['C25_ContourBuiltCoast']
mesh=terrain.data
positions=np.empty((len(mesh.vertices),3),np.float32)
mesh.vertices.foreach_get('co',positions.ravel())
loops=np.empty(len(mesh.loops),np.int32);mesh.loops.foreach_get('vertex_index',loops)
starts=np.empty(len(mesh.polygons),np.int32);mesh.polygons.foreach_get('loop_start',starts)
sizes=np.empty(len(mesh.polygons),np.int32);mesh.polygons.foreach_get('loop_total',sizes)
colors=np.empty((len(mesh.loops),4),np.float32)
mesh.color_attributes['LandUse'].data.foreach_get('color',colors.ravel())
np.savez_compressed(str(LOG/'terrain_baseline.npz'),positions=positions,loops=loops,starts=starts,sizes=sizes,colors=colors)
found=[]
for o in bpy.data.collections['Reference_Town'].objects:
 if o.name.startswith('Town_Floor'):
  found.append({'name':o.get('town_building'),'object':o.name,'corners':[list(o.matrix_world@v.co) for v in o.data.vertices]})
(LOG/'foundations.json').write_text(json.dumps(found,indent=2),encoding='utf8')
info={'pid':os.getpid(),'source':bpy.data.filepath,'port':bpy.types.blendermcp_server.port,'dirty':bpy.data.is_dirty,'vertices':len(mesh.vertices),'faces':len(mesh.polygons),'uv':[x.name for x in mesh.uv_layers],'materials':[m.name for m in mesh.materials],'terrain_transform':[list(r) for r in terrain.matrix_world],'collections':[c.name for c in bpy.data.collections if c.name.startswith('Reference')],'foundations':len(found)}
(LOG/'session_start.json').write_text(json.dumps(info,indent=2),encoding='utf8')
print(json.dumps(info))
