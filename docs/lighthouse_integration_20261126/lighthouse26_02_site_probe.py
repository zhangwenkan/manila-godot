"""Read-only current terrain probe and new-asset bounds; via owned MCP."""
import bpy, os, json, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/lighthouse_integration_20261126'
assert os.getpid()==18904 and bpy.types.blendermcp_server.port==9891
land=bpy.data.objects['C25_ContourBuiltCoast']; inverse=land.matrix_world.inverted()
bpy.context.view_layer.update()
rows=[]
for gz in [21,27,33,39]:
 samples=[]
 for ix in range(11):
  for iz in range(11):
   gx=7.5+(ix-5)*.5;zz=gz+(iz-5)*.5
   origin=inverse@Vector((gx,-zz,30));direction=inverse.to_3x3()@Vector((0,0,-1))
   ok,point,normal,face=land.ray_cast(origin,direction)
   samples.append({'x':gx,'z':zz,'height':float((land.matrix_world@point).z) if ok else None})
 hs=[v['height'] for v in samples if v['height'] is not None]
 rows.append({'center_godot':[7.5,0,gz],'samples':samples,'min':min(hs) if hs else None,'max':max(hs) if hs else None,
              'above_water_count':sum(v>0 for v in hs),'missing':121-len(hs)})
collection=bpy.data.collections['Reference_Lighthouse']
points=[o.matrix_world@Vector(p) for o in collection.objects if o.type=='MESH' for p in o.bound_box]
bounds={'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
report={'read_only':True,'candidate_terrain':rows,'new_lighthouse_blender_bounds':bounds,'source_saved':False}
(LOG/'site_terrain_probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'candidate_summary':[{k:v for k,v in r.items() if k!='samples'} for r in rows],'new_bounds':bounds}))
