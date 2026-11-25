"""Record a verified new GUI session without changing any scene data."""
import bpy, os, json, hashlib
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/terrain_structure_20261123'
assert os.getpid()==28032 and bpy.types.blendermcp_server.port==9881
assert not bpy.app.background and not bpy.data.is_dirty
digest=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
assert digest=='a1bc01b19da7b12c9993f8afaecc70889f15d10f7190a482b6f6fa35e5e7cdaf'
record={'pid':os.getpid(),'port':9881,'file':bpy.data.filepath,'source_sha256':digest,
 'dirty':bpy.data.is_dirty,'blender':bpy.app.version_string,'resumed_on':'2026-11-25',
 'previous_pid':12164,'previous_session_normal_quit_verified':False,
 'saved_state':'third completed export; fourth failed trial was not saved',
 'immutable_baseline':'baseline.npz and objects_before.json remain unchanged'}
(LOG/'session_resume_20261125.json').write_text(json.dumps(record,indent=2),encoding='utf8')
print(json.dumps(record))
