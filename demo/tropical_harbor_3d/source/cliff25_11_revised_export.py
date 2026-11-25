import bpy,os
from pathlib import Path
root=Path(bpy.data.filepath).parent.parent
assert os.getpid()==9864 and bpy.types.blendermcp_server.port==9881 and not bpy.app.background
for name in ['cliff25_07_audit.py','cliff25_09_support_check.py']:
    p=root/'source'/name
    exec(compile(p.read_text(encoding='utf-8-sig'),str(p),'exec'),{})
import json
assert json.loads((root/'captures/cliff_contacts_20261125/support_readonly.json').read_text())['technical_pass']
p=root/'source/cliff25_08_export.py'
exec(compile(p.read_text(encoding='utf-8-sig'),str(p),'exec'),{})
