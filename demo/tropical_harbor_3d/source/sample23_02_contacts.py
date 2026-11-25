import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/rock_path_sample_20261123'
records=[]
for o in bpy.data.objects:
 if o.type!='MESH' or not (o.name.startswith('Hut_Floor') or o.name.startswith('Town_Step') or ('Grass' not in o.name and 'Porch' in o.name)):continue
 points=[o.matrix_world@Vector(v) for v in o.bound_box]
 c=sum(points,Vector())/8
 if not 10<-c.y<47:continue
 records.append({'object':o.name,'building':o.get('town_building'),'center_godot':[c.x,c.z,-c.y],'corners_godot':[[p.x,p.z,-p.y] for p in points]})
(LOG/'door_hut_contacts.json').write_text(json.dumps(records,indent=2),encoding='utf8')
print(json.dumps(records))
