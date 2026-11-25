import bpy,os
from pathlib import Path
root=Path(bpy.data.filepath).parent.parent
namespace={}
exec(compile((root.parents[1]/'docs/reference_review_20261125/cliff25_live_audit.py').read_text(encoding='utf-8-sig'),'cliff25_live_audit.py','exec'),namespace)
report=namespace['audit_cliff25'](9864,check_export=False)
assert report['technical_pass'],report
