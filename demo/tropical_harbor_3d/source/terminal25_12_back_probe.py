"""Read-only same-camera hit probe for the final rear-footing review."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector
root = Path(bpy.data.filepath).parent.parent
log = root / 'captures/terminal_rebuild_20261125'
eye=Vector((7.070596,42.28264,11.88596))
target=Vector((-2.943,24.0761,4.967475))
forward=(target-eye).normalized()
right=forward.cross(Vector((0,0,1))).normalized()
up=right.cross(forward).normalized()
deps=bpy.context.evaluated_depsgraph_get()
rows=[]
for x,y in [(590,648),(600,650),(610,654),(620,657),(630,662),(640,665),(650,666),(660,670),(670,672),(680,677),(690,680),(700,680),(710,687),(720,687),(730,685),(650,630),(650,645),(650,675),(650,685)]:
    ray=(forward + right*((2*x/1600-1)*math.tan(math.radians(24))*1600/900) + up*((1-2*y/900)*math.tan(math.radians(24)))).normalized()
    hit,loc,norm,index,obj,mat=bpy.context.scene.ray_cast(deps,eye,ray,distance=200)
    rows.append({'pixel':[x,y],'hit':bool(hit),'object':obj.name if hit else None,'position':list(loc) if hit else None,'face':index,'normal':list(norm),'dot_ray_normal':ray.dot(norm)})
(log/'back_probe.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print(json.dumps(rows))
