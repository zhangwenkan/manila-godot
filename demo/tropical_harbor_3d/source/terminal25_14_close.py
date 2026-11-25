"""Close only this verified, saved GUI source after the final independent audit."""
import bpy,os,json,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
assert os.getpid()==13812 and not bpy.app.background and bpy.types.blendermcp_server.port==9881
source=Path(bpy.data.filepath)
assert source.name=='harbor_shore_control_mcp.blend'
log=source.parent.parent/'captures/terminal_rebuild_20261125'
final=json.loads((log/'final_source_check.json').read_text(encoding='utf8'))
export=json.loads((log/'export.json').read_text(encoding='utf8'))
assert final['passed'] and not bpy.data.is_dirty and export['status']=='completed'
sha=hashlib.sha256(source.read_bytes()).hexdigest()
assert sha==export['source_sha256']==final['source_sha256']
report={'pid':os.getpid(),'port':9881,'source':str(source),'source_sha256':sha,
        'dirty':bool(bpy.data.is_dirty),'normal_quit_requested':True,'process_exited':False,
        'requested_at':datetime.now(timezone(timedelta(hours=8))).isoformat()}
(log/'session_close.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def close_owned():
    bpy.ops.wm.quit_blender()
    return None
bpy.app.timers.register(close_owned,first_interval=2.0)
print(json.dumps(report,ensure_ascii=False))
