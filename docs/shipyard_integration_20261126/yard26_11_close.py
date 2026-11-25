"""Close only the verified, saved Y26 GUI Blender session via its MCP."""
import bpy
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path('F:/马尼拉godot/manila-godot/demo/tropical_harbor_3d')
LOG = ROOT / 'captures/shipyard_integration_20261126'
source = ROOT / 'source/harbor_shore_control_mcp.blend'
assert os.getpid() == 29492
assert bpy.types.blendermcp_server.port == 9881
assert Path(bpy.data.filepath).resolve() == source.resolve()
audit = json.loads((LOG / 'final_source_audit.json').read_text(encoding='utf-8'))
export = json.loads((LOG / 'shipyard_export_last_completed.json').read_text(encoding='utf-8'))
assert audit['passed'] and all(audit['checks'].values())
assert export['status'] == 'completed' and export['source_saved']
assert not bpy.data.is_dirty and not export['dirty']
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == export['source_sha256']
record = {
    'pid': os.getpid(),
    'port': 9881,
    'source': str(source),
    'source_sha256': source_hash,
    'dirty_observed': bool(bpy.data.is_dirty),
    'source_audit': str(LOG / 'final_source_audit.json'),
    'targeted_capture': str(ROOT / 'captures/art_20261126_013606_203304'),
    'normal_quit_requested': True,
    'requested_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
    'process_exit_confirmed': False,
}
(LOG / 'session_close.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
def quit_owned_session():
    bpy.ops.wm.quit_blender()
    return None
bpy.app.timers.register(quit_owned_session, first_interval=1.5)
print(json.dumps(record, ensure_ascii=False))
