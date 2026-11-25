import bpy,os,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/lighthouse_integration_20261126'
assert os.getpid()==18904 and bpy.types.blendermcp_server.port==9891
land=bpy.data.objects['C25_ContourBuiltCoast'];inv=land.matrix_world.inverted();rows=[]
for cx,gz in [(5.5,15),(6.1,15),(6.1,18),(5.0,12),(5.5,12)]:
 samples=[]
 for ix in range(11):
  for iz in range(11):
   x=cx+(ix-5)*.5;z=gz+(iz-5)*.5
   ok,p,n,fi=land.ray_cast(inv@Vector((x,-z,30)),inv.to_3x3()@Vector((0,0,-1)))
   samples.append({'x':x,'z':z,'height':float((land.matrix_world@p).z) if ok else None})
 hs=[s['height'] for s in samples if s['height'] is not None]
 rows.append({'center_godot':[cx,0,gz],'samples':samples,'min':min(hs),'max':max(hs),'above_water_count':sum(h>0 for h in hs)})
(LOG/'bay_terrain_probe.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps([{k:v for k,v in row.items() if k!='samples'} for row in rows]))
