"""Normally close only this turn's verified clean Blender after final review."""
import bpy,json,os,hashlib
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/terrain_structure_20261123'
assert os.getpid()==28032 and bpy.types.blendermcp_server.port==9881
assert not bpy.app.background and not bpy.data.is_dirty
audit=json.loads((LOG/'final_readonly.json').read_text(encoding='utf8'))
export=json.loads((LOG/'export.json').read_text(encoding='utf8'))
assert audit['integrity_pass'] and audit['technical_pass'] and audit['dirty_after'] is False
assert export['source_saved'] and export['dirty'] is False
digest=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
assert digest==export['source_sha256']
report={'pid':os.getpid(),'port':9881,'source':bpy.data.filepath,'source_sha256':digest,
        'source_saved':True,'dirty':False,'integrity_pass':True,'technical_pass':True,
        'visual_accepted':False,'normal_quit_requested':True,'process_exited':False}
(LOG/'session_close.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
def close_structure_session():
    bpy.ops.wm.quit_blender()
    return None
bpy.app.timers.register(close_structure_session,first_interval=1.5)
