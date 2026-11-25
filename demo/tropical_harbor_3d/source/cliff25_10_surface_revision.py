"""Explicit second surface iteration; GUI MCP only, current-round baselines."""
import bpy,os,json,time
from pathlib import Path
root=Path(bpy.data.filepath).parent.parent
log=root/'captures/cliff_contacts_20261125'
assert os.getpid()==9864 and bpy.types.blendermcp_server.port==9881 and not bpy.app.background
completed=[]
for name in ['cliff25_03_contacts.py','cliff25_04_ground_detail.py','cliff25_05_root_contacts.py','cliff25_06_source_preview.py']:
    (log/'surface_revision_progress.json').write_text(json.dumps({'current':name,'completed':completed,'time':time.time()}))
    path=root/'source'/name
    exec(compile(path.read_text(encoding='utf-8-sig'),str(path),'exec'),{})
    completed.append(name)
(log/'surface_revision_progress.json').write_text(json.dumps({'status':'completed','completed':completed,'time':time.time()}))
