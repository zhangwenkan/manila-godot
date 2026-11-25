import bpy
from pathlib import Path
root=Path(bpy.data.filepath).parent.parent
script=root.parents[1]/'docs/reference_review_20261125/cliff25_support_readonly.py'
ns={}
exec(compile(script.read_text(encoding='utf-8-sig'),str(script),'exec'),ns)
ns['audit_cliff25_support'](9864)
