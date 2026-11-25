import bpy,os,json,hashlib
from pathlib import Path
from datetime import datetime
LOG=Path(bpy.data.filepath).parent.parent/'captures/pirate_island_20261125'
assert os.getpid()==1028 and bpy.types.blendermcp_server.port==9881 and not bpy.data.is_dirty
source_sha=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
assert source_sha=='09330e1d03d41f946ebda7121c44c38d6089e839e5030f35cb36457b5f89457b'
assert not bpy.data.collections.get('P25_EXPORT_TEMP')
r={'pid':os.getpid(),'port':9881,'source':bpy.data.filepath,'source_sha256':source_sha,'dirty':bpy.data.is_dirty,'requested_at':datetime.now().astimezone().isoformat(),'normal_close_requested':True,'process_exited':False}
(LOG/'session_close.json').write_text(json.dumps(r,indent=2),encoding='utf8')
def close_owned():bpy.ops.wm.quit_blender();return None
bpy.app.timers.register(close_owned,first_interval=2.0)
print(json.dumps(r))
