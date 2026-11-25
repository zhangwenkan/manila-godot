"""One-time rigid assembly move through owned GUI MCP; no mesh edits."""
import bpy, os, math, json, importlib.util
from pathlib import Path
from datetime import datetime
from mathutils import Matrix
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/pirate_orientation_20261125'
assert os.getpid()==38548 and not bpy.app.background and bpy.types.blendermcp_server.port==9881
assert (LOG/'session_start.json').exists() and not (LOG/'transform.json').exists()
HELPER=ROOT.parent.parent/'docs/pirate_orientation_20261125/pirate_orientation25_invariants.py'
spec=importlib.util.spec_from_file_location('pirate_orientation_invariants',HELPER)
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
before=helpers.check_island_local(LOG)
assert before['passed'],before
assembly=bpy.data.objects['P25_Assembly']
assert abs(assembly.location.x+17.5)<1e-5 and abs(assembly.location.y-22)<1e-5 and abs(assembly.rotation_euler.z-math.radians(-20))<1e-5
old_matrix=assembly.matrix_world.copy()
assembly.location=(-17.5,14,0)
assembly.rotation_euler=(0,0,math.radians(90))
bpy.context.view_layer.update()
after=helpers.check_island_local(LOG)
assert after['passed'],after
report={'created_local':datetime.now().astimezone().isoformat(),'pid':os.getpid(),'port':9881,'old_assembly_world':[list(v) for v in old_matrix],'expected_assembly_world':[list(v) for v in assembly.matrix_world],'godot_center':[-17.5,0,-14],'godot_front':[1,0,0],'absolute_yaw_degrees':90,'rotation_change_degrees':110,'local_invariants':after,'source_saved':False,'mesh_geometry_changed':False}
(LOG/'transform.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='local_invariants'}))
