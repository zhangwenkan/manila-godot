import bpy,json
from pathlib import Path
ns=bpy.app.driver_namespace['pirate25'];LOG=ns['LOG'];assert not (LOG/'shore_stone_fix.json').exists()
o=bpy.data.objects['P25_BeachTalus.005'];before=list(o.location)
x,y=3.75,-3.0;z=ns['ground_z'](x,y);o.location=(x,y,z+.52*.25)
report=json.loads((LOG/'build.json').read_text(encoding='utf8'))
for a in report['supports']:
 if a['object']==o.name:a['bottom_local']=[x,y,z-.18]
(LOG/'build.json').write_text(json.dumps(report,indent=2),encoding='utf8')
(LOG/'shore_stone_fix.json').write_text(json.dumps({'object':o.name,'before':before,'after':list(o.location)},indent=2),encoding='utf8')
bpy.context.view_layer.update();print('shore stone moved back onto actual island shelf')
