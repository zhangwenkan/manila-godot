"""Third local form/surface iteration, from current-round immutable snapshots."""
import bpy,os,json,time
from pathlib import Path
root=Path(bpy.data.filepath).parent.parent
log=root/'captures/cliff_contacts_20261125'
assert os.getpid()==9864 and bpy.types.blendermcp_server.port==9881 and not bpy.app.background
completed=[]
for name in ['cliff25_01_sculpt.py','cliff25_02_mineral.py','cliff25_03_contacts.py','cliff25_04_ground_detail.py','cliff25_05_root_contacts.py','cliff25_06_source_preview.py','cliff25_07_audit.py','cliff25_09_support_check.py']:
    (log/'form_revision_progress.json').write_text(json.dumps({'current':name,'completed':completed,'time':time.time()}))
    p=root/'source'/name
    exec(compile(p.read_text(encoding='utf-8-sig'),str(p),'exec'),{})
    completed.append(name)
assert json.loads((log/'support_readonly.json').read_text())['technical_pass']
(log/'form_revision_progress.json').write_text(json.dumps({'status':'completed','completed':completed,'time':time.time()}))
