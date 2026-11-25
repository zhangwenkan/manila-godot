"""Close only this round's verified, saved GUI Blender through its MCP."""
import bpy,os,json,hashlib
from pathlib import Path
from datetime import datetime
LOG=Path(bpy.data.filepath).parent.parent/'captures/pirate_orientation_20261125'
assert os.getpid()==38548 and bpy.types.blendermcp_server.port==9881 and not bpy.data.is_dirty
source_sha=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
assert source_sha=='c7875c007daf21c3e4d3cec38df6ad6ed9bb2f59460f64625ba240f1a05519c1'
audits=list(LOG.glob('pirate_audit_*.json'))
assert audits and json.loads(max(audits,key=lambda p:p.stat().st_mtime).read_text(encoding='utf8'))['passed']
assert not bpy.data.collections.get('P25_EXPORT_TEMP')
r={'pid':os.getpid(),'port':9881,'source':bpy.data.filepath,'source_sha256':source_sha,'dirty':bpy.data.is_dirty,'requested_at':datetime.now().astimezone().isoformat(),'normal_close_requested':True,'process_exited':False}
(LOG/'session_close.json').write_text(json.dumps(r,indent=2),encoding='utf8')
def close_owned():
    bpy.ops.wm.quit_blender()
    return None
bpy.app.timers.register(close_owned,first_interval=2.0)
print(json.dumps(r))
