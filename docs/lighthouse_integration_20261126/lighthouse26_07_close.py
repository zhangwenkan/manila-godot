"""Close only this owned, clean, audited GUI Blender session."""
import bpy, os, json, hashlib
from pathlib import Path
ROOT = Path(bpy.data.filepath).parent.parent
LOG = ROOT / 'captures/lighthouse_integration_20261126'
assert os.getpid() == 18904 and bpy.types.blendermcp_server.port == 9891
assert not bpy.app.background and not bpy.data.is_dirty
audit = json.loads((LOG / 'lighthouse_final_audit.json').read_text(encoding='utf-8'))
assert audit['passed'] and audit['disk_source_matches_completed_export']
assert hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest() == audit['source_sha256']
(LOG / 'close_requested.json').write_text(json.dumps({'pid': os.getpid(), 'port': 9891,
    'dirty': False, 'source_sha256': audit['source_sha256'], 'normal_quit_scheduled': True}, indent=2), encoding='utf-8')
def close_owned_session():
    bpy.ops.wm.quit_blender()
    return None
bpy.app.timers.register(close_owned_session, first_interval=1.0)
print('Owned clean audited Blender normal exit scheduled')
