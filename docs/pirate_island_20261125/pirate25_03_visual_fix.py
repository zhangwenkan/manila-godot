import bpy,math,json,numpy as np
from pathlib import Path
from mathutils import Vector
ns=bpy.app.driver_namespace['pirate25'];LOG=ns['LOG'];C=ns['C'];root=ns['root']
assert not (LOG/'visual_fix.json').exists()
base=bpy.data.objects['P25_IslandSandBody'];o=bpy.data.objects['P25_BeachTalus.005']
x,y=3.35,-2.45;ok,hit,n,ix=base.ray_cast(Vector((x,y,10)),Vector((0,0,-1)));assert ok
o.location=(x,y,hit.z+.52*.25)
report=json.loads((LOG/'build.json').read_text(encoding='utf8'))
for a in report['supports']:
 if a['object']==o.name:a['bottom_local']=[x,y,hit.z-.13]
# Bring the rock floor above the sand without changing the underlying closed sand body.
floor=bpy.data.objects['P25_CaveFloor'];floor.location.z=.59;floor.data.materials.clear();floor.data.materials.append(ns['P']['void'])
floor.scale.y=1.24
# Deep broad end and upper side surfaces read as a real dark recess from the game camera.
ns['box']('CaveDeepBacking',(.65,2.70,1.68),(2.65,.24,2.55),'void',.02)
ns['box']('CaveLeftInnerWall',(-.64,1.30,1.15),(.16,2.65,1.36),'rockdark',.02)
ns['box']('CaveRightInnerWall',(1.94,1.30,1.15),(.16,2.65,1.36),'rockdark',.02)
# The fan moss layer originally intersected the slightly nonplanar rock caps.
caps=[]
for o in C.objects:
 if o.name.startswith('P25_RockCrownMoss'):
  o.location.z+=.10
  for p in o.data.polygons:p.use_smooth=False
  caps.append(o.name)
ns['mat']('moss_cap',(117,142,66),'Ref_D19_Foliage1')
for name in caps:
 o=bpy.data.objects[name];o.data.materials.clear();o.data.materials.append(ns['P']['moss_cap'])
# Shorter, wider evergreen layers replace the tall needle silhouette.
pines=0
for o in C.objects:
 if not o.name.startswith('P25_NeedleCanopy'):continue
 v=o.data.vertices;assert len(v)==33
 lower=sum(v[j].co.z for j in range(11))/11
 upper=sum(v[j].co.z for j in range(22,33))/11
 h=(upper-lower-.10)/.50
 cx=sum(v[j].co.x for j in range(11))/11;cy=sum(v[j].co.y for j in range(11))/11
 for j,p in enumerate(v):
  p.co.x=cx+(p.co.x-cx)*1.22;p.co.y=cy+(p.co.y-cy)*1.22
  if j>=22:p.co.z-=.24*h
 pines+=1
# Town foliage uses rounded normals; retain the shaped silhouette, soften the faceted tree blocks.
for o in C.objects:
 if o.name.startswith(('P25_BroadCanopy','P25_BroadTop')):
  for p in o.data.polygons:p.use_smooth=True
# Break the silhouette of the tallest monolithic peak with two embedded shoulders.
ns['blob']('HighRidgeShoulder',(.42,2.88,4.85),(1.75,1.90,3.5),'rocklight',720)
ns['blob']('HighRidgeCrown',(1.15,3.33,6.95),(1.7,1.6,.90),'rocklight',721)
bpy.context.view_layer.update()
report['objects']=len([o for o in C.objects if o.type=='MESH'])
(LOG/'build.json').write_text(json.dumps(report,indent=2),encoding='utf8')
result={'stone':list(bpy.data.objects['P25_BeachTalus.005'].location),'stone_support_hit':list(hit),'moss_caps':caps,'pine_layers':pines,'objects':report['objects'],'source_saved':False}
(LOG/'visual_fix.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
for c in bpy.data.collections:
 if c.name.startswith('Reference_') and ('Ocean' in c.name or 'Water' in c.name):
  print(c.name,[(o.name,list(o.dimensions),list(o.location),[m.name for m in o.data.materials] if o.type=='MESH' else []) for o in c.objects])
